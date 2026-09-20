import hashlib
import json
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from app.core.config import settings
from app.models.assessment import Assessment, AssessmentConclusionEnum, AssessmentStatusEnum
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.framework import Framework, FrameworkFunction, FrameworkCategory, FrameworkSubcategory
from app.models.policy import (
    AttestationRecordStatusEnum,
    CampaignStatusEnum,
    CampaignTargetTypeEnum,
    Policy,
    PolicyAttestationCampaign,
    PolicyControlMapping,
    PolicyReviewStageEnum,
    PolicyReviewStatusEnum,
    PolicyReviewWorkflow,
    PolicyStatusEnum,
    PolicyTypeEnum,
    PolicyVersion,
    PolicyVersionStatusEnum,
    UserAttestationRecord,
)
from app.models.user import User
from app.schemas.policy import (
    PolicyAttestationCampaignCreate,
    PolicyAttestationCampaignUpdate,
    PolicyCreate,
    PolicyReviewWorkflowAction,
    PolicyReviewWorkflowCreate,
    PolicyUpdate,
    PolicyVersionCreate,
    PolicyVersionUpdate,
    UserAttestationSubmit,
)
from app.services.audit_service import AuditService


class PolicyService:
    @staticmethod
    def compute_canonical_hash(content: str) -> str:
        """Deterministic policy content hashing.

        - UTF-8 representation
        - CRLF and CR normalized to LF
        - Line-level trailing whitespace stripped
        - SHA-256 digest
        """
        lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        normalized = "\n".join(line.rstrip() for line in lines)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    # ── Root Policy Operations ──────────────────────────────────────────────

    @staticmethod
    def list_policies(
        db: Session,
        organization_id: int,
        status: Optional[PolicyStatusEnum] = None,
        policy_type: Optional[PolicyTypeEnum] = None,
        owner_id: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(Policy)
            .filter(Policy.organization_id == organization_id)
            .options(joinedload(Policy.owner), joinedload(Policy.versions))
        )

        if status:
            query = query.filter(Policy.status == status)
        if policy_type:
            query = query.filter(Policy.policy_type == policy_type)
        if owner_id:
            query = query.filter(Policy.owner_id == owner_id)
        if search:
            query = query.filter(
                (Policy.title.ilike(f"%{search}%"))
                | (Policy.description.ilike(f"%{search}%"))
            )

        policies = query.order_by(Policy.updated_at.desc()).offset(skip).limit(limit).all()

        results = []
        for pol in policies:
            latest_version = pol.versions[0] if pol.versions else None
            mapped_subcats = (
                db.query(FrameworkSubcategory)
                .join(PolicyControlMapping, PolicyControlMapping.subcategory_id == FrameworkSubcategory.id)
                .filter(
                    PolicyControlMapping.organization_id == organization_id,
                    PolicyControlMapping.policy_id == pol.id,
                )
                .all()
            )
            results.append({
                "id": pol.id,
                "organization_id": pol.organization_id,
                "title": pol.title,
                "description": pol.description,
                "policy_type": pol.policy_type,
                "status": pol.status,
                "owner_id": pol.owner_id,
                "effective_date": pol.effective_date,
                "review_date": pol.review_date,
                "created_at": pol.created_at,
                "updated_at": pol.updated_at,
                "owner": pol.owner,
                "current_version": latest_version,
                "total_versions": len(pol.versions),
                "mapped_subcategories": mapped_subcats,
            })

        return results

    @staticmethod
    def get_policy_by_id(
        db: Session, policy_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        pol = (
            db.query(Policy)
            .filter(
                Policy.id == policy_id,
                Policy.organization_id == organization_id,
            )
            .options(
                joinedload(Policy.owner),
                joinedload(Policy.versions).joinedload(PolicyVersion.created_by),
            )
            .first()
        )
        if not pol:
            return None

        mapped_subcats = (
            db.query(FrameworkSubcategory)
            .join(PolicyControlMapping, PolicyControlMapping.subcategory_id == FrameworkSubcategory.id)
            .filter(
                PolicyControlMapping.organization_id == organization_id,
                PolicyControlMapping.policy_id == pol.id,
            )
            .all()
        )

        latest_version = pol.versions[0] if pol.versions else None

        return {
            "id": pol.id,
            "organization_id": pol.organization_id,
            "title": pol.title,
            "description": pol.description,
            "policy_type": pol.policy_type,
            "status": pol.status,
            "owner_id": pol.owner_id,
            "effective_date": pol.effective_date,
            "review_date": pol.review_date,
            "created_at": pol.created_at,
            "updated_at": pol.updated_at,
            "owner": pol.owner,
            "current_version": latest_version,
            "total_versions": len(pol.versions),
            "versions": pol.versions,
            "mapped_subcategories": mapped_subcats,
        }

    @staticmethod
    def create_policy(
        db: Session, obj_in: PolicyCreate, organization_id: int, created_by_id: Optional[int]
    ) -> Policy:
        pol = Policy(
            organization_id=organization_id,
            title=obj_in.title,
            description=obj_in.description,
            policy_type=obj_in.policy_type,
            status=PolicyStatusEnum.DRAFT,
            owner_id=obj_in.owner_id or created_by_id,
            effective_date=obj_in.effective_date,
            review_date=obj_in.review_date,
        )
        db.add(pol)
        db.commit()
        db.refresh(pol)

        # Create initial Version 1 with canonical hash
        v1_hash = PolicyService.compute_canonical_hash(obj_in.initial_content)
        v1 = PolicyVersion(
            organization_id=organization_id,
            policy_id=pol.id,
            version_number=1,
            content=obj_in.initial_content,
            content_hash_sha256=v1_hash,
            change_summary="Initial drafted version",
            status=PolicyVersionStatusEnum.DRAFT,
            effective_date=obj_in.effective_date,
            created_by_id=created_by_id,
        )
        db.add(v1)

        # Map initial subcategories (deduplicated)
        unique_subcat_ids = list(dict.fromkeys(obj_in.mapped_subcategory_ids))
        for subcat_id in unique_subcat_ids:
            sub = db.query(FrameworkSubcategory).filter(FrameworkSubcategory.id == subcat_id).first()
            if sub:
                mapping = PolicyControlMapping(
                    organization_id=organization_id,
                    policy_id=pol.id,
                    subcategory_id=sub.id,
                )
                db.add(mapping)

        db.commit()
        db.refresh(pol)
        return pol

    @staticmethod
    def update_policy(
        db: Session, policy_id: int, organization_id: int, obj_in: PolicyUpdate
    ) -> Optional[Policy]:
        pol = (
            db.query(Policy)
            .filter(
                Policy.id == policy_id,
                Policy.organization_id == organization_id,
            )
            .first()
        )
        if not pol:
            return None

        if pol.status == PolicyStatusEnum.ARCHIVED:
            raise ValueError("Cannot modify an archived policy. Restore policy to DRAFT status first.")

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(pol, field, value)

        db.add(pol)
        db.commit()
        db.refresh(pol)
        return pol

    @staticmethod
    def update_policy_status(
        db: Session, policy_id: int, organization_id: int, new_status: PolicyStatusEnum
    ) -> Optional[Policy]:
        pol = (
            db.query(Policy)
            .filter(
                Policy.id == policy_id,
                Policy.organization_id == organization_id,
            )
            .first()
        )
        if not pol:
            return None

        valid_transitions = {
            PolicyStatusEnum.DRAFT: [PolicyStatusEnum.UNDER_REVIEW, PolicyStatusEnum.ARCHIVED],
            PolicyStatusEnum.UNDER_REVIEW: [PolicyStatusEnum.APPROVED, PolicyStatusEnum.DRAFT, PolicyStatusEnum.ARCHIVED],
            PolicyStatusEnum.APPROVED: [PolicyStatusEnum.PUBLISHED, PolicyStatusEnum.UNDER_REVIEW, PolicyStatusEnum.ARCHIVED],
            PolicyStatusEnum.PUBLISHED: [PolicyStatusEnum.UNDER_REVIEW, PolicyStatusEnum.ARCHIVED],
            PolicyStatusEnum.ARCHIVED: [PolicyStatusEnum.DRAFT],
        }

        allowed = valid_transitions.get(pol.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid policy state transition from {pol.status.value} to {new_status.value}. Allowed next states: {[s.value for s in allowed]}"
            )

        pol.status = new_status
        db.add(pol)
        db.commit()
        db.refresh(pol)
        return pol

    # ── Policy Version Lifecycle ────────────────────────────────────────────

    @staticmethod
    def list_policy_versions(
        db: Session, policy_id: int, organization_id: int
    ) -> List[PolicyVersion]:
        pol = (
            db.query(Policy)
            .filter(Policy.id == policy_id, Policy.organization_id == organization_id)
            .first()
        )
        if not pol:
            raise ValueError("Policy not found in your organization")

        return (
            db.query(PolicyVersion)
            .filter(PolicyVersion.policy_id == policy_id)
            .options(joinedload(PolicyVersion.created_by), joinedload(PolicyVersion.approved_by))
            .order_by(PolicyVersion.version_number.desc())
            .all()
        )

    @staticmethod
    def get_policy_version(
        db: Session, policy_id: int, version_id: int, organization_id: int
    ) -> Optional[PolicyVersion]:
        pol = (
            db.query(Policy)
            .filter(Policy.id == policy_id, Policy.organization_id == organization_id)
            .first()
        )
        if not pol:
            return None

        return (
            db.query(PolicyVersion)
            .filter(PolicyVersion.id == version_id, PolicyVersion.policy_id == policy_id)
            .options(joinedload(PolicyVersion.created_by), joinedload(PolicyVersion.approved_by))
            .first()
        )

    @staticmethod
    def create_policy_version(
        db: Session,
        policy_id: int,
        organization_id: int,
        obj_in: PolicyVersionCreate,
        created_by_id: Optional[int],
    ) -> PolicyVersion:
        pol = (
            db.query(Policy)
            .filter(Policy.id == policy_id, Policy.organization_id == organization_id)
            .first()
        )
        if not pol:
            raise ValueError("Policy not found in your organization")

        if pol.status == PolicyStatusEnum.ARCHIVED:
            raise ValueError("Cannot add new versions to an archived policy. Restore policy to DRAFT status first.")

        latest_ver = (
            db.query(PolicyVersion)
            .filter(PolicyVersion.policy_id == policy_id)
            .order_by(PolicyVersion.version_number.desc())
            .first()
        )
        next_ver_num = (latest_ver.version_number + 1) if latest_ver else 1

        content_hash = PolicyService.compute_canonical_hash(obj_in.content)

        new_version = PolicyVersion(
            organization_id=organization_id,
            policy_id=pol.id,
            version_number=next_ver_num,
            content=obj_in.content,
            content_hash_sha256=content_hash,
            change_summary=obj_in.change_summary,
            status=PolicyVersionStatusEnum.DRAFT,
            effective_date=obj_in.effective_date or pol.effective_date,
            created_by_id=created_by_id,
        )
        db.add(new_version)
        db.commit()
        db.refresh(new_version)
        return new_version

    @staticmethod
    def update_policy_version(
        db: Session,
        policy_id: int,
        version_id: int,
        organization_id: int,
        obj_in: PolicyVersionUpdate,
    ) -> PolicyVersion:
        version = PolicyService.get_policy_version(db, policy_id, version_id, organization_id)
        if not version:
            raise ValueError("Policy version not found in your organization")

        # STRICT IMMUTABILITY CHECK
        if version.status != PolicyVersionStatusEnum.DRAFT:
            raise ValueError(
                f"Cannot mutate policy version in '{version.status.value}' status. "
                "Only DRAFT versions are mutable; submitted, approved, and published versions are immutable."
            )

        if obj_in.content is not None:
            version.content = obj_in.content
            version.content_hash_sha256 = PolicyService.compute_canonical_hash(obj_in.content)
        if obj_in.change_summary is not None:
            version.change_summary = obj_in.change_summary
        if obj_in.effective_date is not None:
            version.effective_date = obj_in.effective_date

        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def submit_version_for_review(
        db: Session,
        policy_id: int,
        version_id: int,
        organization_id: int,
        review_in: PolicyReviewWorkflowCreate,
        current_user_id: int,
    ) -> Tuple[PolicyVersion, PolicyReviewWorkflow]:
        version = PolicyService.get_policy_version(db, policy_id, version_id, organization_id)
        if not version:
            raise ValueError("Policy version not found in your organization")

        if version.status not in [PolicyVersionStatusEnum.DRAFT]:
            raise ValueError(f"Cannot submit version in status '{version.status.value}' for review. Must be DRAFT.")

        version.status = PolicyVersionStatusEnum.UNDER_REVIEW

        pol = db.query(Policy).filter(Policy.id == policy_id, Policy.organization_id == organization_id).first()
        if pol and pol.status == PolicyStatusEnum.DRAFT:
            pol.status = PolicyStatusEnum.UNDER_REVIEW

        workflow_code = f"WF-REV-{version.id}-{int(datetime.now(timezone.utc).timestamp())}"
        workflow = PolicyReviewWorkflow(
            organization_id=organization_id,
            policy_id=policy_id,
            version_id=version.id,
            workflow_code=workflow_code,
            review_stage=review_in.review_stage,
            status=PolicyReviewStatusEnum.PENDING,
            assigned_reviewer_id=review_in.assigned_reviewer_id,
            review_notes=review_in.review_notes,
            created_by_id=current_user_id,
        )
        db.add(workflow)
        db.commit()
        db.refresh(version)
        db.refresh(workflow)
        return version, workflow

    @staticmethod
    def review_policy_version_workflow(
        db: Session,
        policy_id: int,
        version_id: int,
        workflow_id: int,
        organization_id: int,
        action_in: PolicyReviewWorkflowAction,
        current_user_id: int,
    ) -> Tuple[PolicyVersion, PolicyReviewWorkflow]:
        version = PolicyService.get_policy_version(db, policy_id, version_id, organization_id)
        if not version:
            raise ValueError("Policy version not found in your organization")

        workflow = (
            db.query(PolicyReviewWorkflow)
            .filter(
                PolicyReviewWorkflow.id == workflow_id,
                PolicyReviewWorkflow.version_id == version_id,
                PolicyReviewWorkflow.organization_id == organization_id,
            )
            .first()
        )
        if not workflow:
            raise ValueError("Policy review workflow not found")

        decision = action_in.decision.upper()
        now = datetime.now(timezone.utc)

        if decision == "APPROVE":
            # STRICT FOUR-EYES CHECK: Author cannot approve their own version
            if version.created_by_id == current_user_id:
                raise ValueError("Four-Eyes Violation: The author/creator of a policy version cannot approve it.")

            workflow.status = PolicyReviewStatusEnum.APPROVED
            workflow.approved_by_id = current_user_id
            workflow.approved_at = now
            workflow.reviewed_by_id = current_user_id
            workflow.reviewed_at = now
            if action_in.review_notes:
                workflow.review_notes = (
                    f"{workflow.review_notes or ''}\nApproval Notes: {action_in.review_notes}".strip()
                )

            version.status = PolicyVersionStatusEnum.APPROVED
            version.approved_by_id = current_user_id
            version.approved_at = now

            pol = db.query(Policy).filter(Policy.id == policy_id, Policy.organization_id == organization_id).first()
            if pol:
                pol.status = PolicyStatusEnum.APPROVED

        elif decision == "REJECT":
            workflow.status = PolicyReviewStatusEnum.REJECTED
            workflow.reviewed_by_id = current_user_id
            workflow.reviewed_at = now
            if action_in.review_notes:
                workflow.review_notes = (
                    f"{workflow.review_notes or ''}\nRejection Notes: {action_in.review_notes}".strip()
                )
            version.status = PolicyVersionStatusEnum.ARCHIVED

        elif decision == "CHANGES_REQUESTED":
            workflow.status = PolicyReviewStatusEnum.CHANGES_REQUESTED
            workflow.reviewed_by_id = current_user_id
            workflow.reviewed_at = now
            if action_in.review_notes:
                workflow.review_notes = (
                    f"{workflow.review_notes or ''}\nChanges Requested: {action_in.review_notes}".strip()
                )
            version.status = PolicyVersionStatusEnum.DRAFT

        else:
            raise ValueError(f"Invalid decision '{action_in.decision}'. Allowed: APPROVE, REJECT, CHANGES_REQUESTED.")

        db.commit()
        db.refresh(version)
        db.refresh(workflow)
        return version, workflow

    @staticmethod
    def publish_policy_version(
        db: Session,
        policy_id: int,
        version_id: int,
        organization_id: int,
        current_user_id: int,
    ) -> PolicyVersion:
        version = PolicyService.get_policy_version(db, policy_id, version_id, organization_id)
        if not version:
            raise ValueError("Policy version not found in your organization")

        # Must be formally approved before publishing
        if version.status != PolicyVersionStatusEnum.APPROVED:
            raise ValueError(
                f"Cannot publish policy version in status '{version.status.value}'. Version must be formally APPROVED."
            )

        # Supersede previously published versions
        old_published = (
            db.query(PolicyVersion)
            .filter(
                PolicyVersion.policy_id == policy_id,
                PolicyVersion.organization_id == organization_id,
                PolicyVersion.status == PolicyVersionStatusEnum.PUBLISHED,
            )
            .all()
        )
        for op in old_published:
            op.status = PolicyVersionStatusEnum.SUPERSEDED

        version.status = PolicyVersionStatusEnum.PUBLISHED

        pol = db.query(Policy).filter(Policy.id == policy_id, Policy.organization_id == organization_id).first()
        if pol:
            pol.status = PolicyStatusEnum.PUBLISHED
            pol.effective_date = version.effective_date or date.today()

        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def delete_policy_version(
        db: Session, policy_id: int, version_id: int, organization_id: int
    ) -> bool:
        version = PolicyService.get_policy_version(db, policy_id, version_id, organization_id)
        if not version:
            return False

        # Cannot delete if bound to an active campaign
        active_campaign = (
            db.query(PolicyAttestationCampaign)
            .filter(
                PolicyAttestationCampaign.version_id == version.id,
                PolicyAttestationCampaign.organization_id == organization_id,
                PolicyAttestationCampaign.status == CampaignStatusEnum.ACTIVE,
            )
            .first()
        )
        if active_campaign:
            raise ValueError(
                f"Cannot delete policy version: it is bound to active attestation campaign '{active_campaign.campaign_code}'."
            )

        db.delete(version)
        db.commit()
        return True

    # ── Attestation Campaign Management ─────────────────────────────────────

    @staticmethod
    def list_campaigns(
        db: Session,
        organization_id: int,
        policy_id: Optional[int] = None,
        status: Optional[CampaignStatusEnum] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[PolicyAttestationCampaign]:
        query = db.query(PolicyAttestationCampaign).filter(
            PolicyAttestationCampaign.organization_id == organization_id
        )
        if policy_id:
            query = query.filter(PolicyAttestationCampaign.policy_id == policy_id)
        if status:
            query = query.filter(PolicyAttestationCampaign.status == status)

        return (
            query.options(
                joinedload(PolicyAttestationCampaign.policy),
                joinedload(PolicyAttestationCampaign.version),
            )
            .order_by(PolicyAttestationCampaign.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_campaign(
        db: Session, campaign_id: int, organization_id: int
    ) -> Optional[PolicyAttestationCampaign]:
        return (
            db.query(PolicyAttestationCampaign)
            .filter(
                PolicyAttestationCampaign.id == campaign_id,
                PolicyAttestationCampaign.organization_id == organization_id,
            )
            .options(
                joinedload(PolicyAttestationCampaign.policy),
                joinedload(PolicyAttestationCampaign.version),
            )
            .first()
        )

    @staticmethod
    def create_campaign(
        db: Session,
        campaign_in: PolicyAttestationCampaignCreate,
        organization_id: int,
        current_user_id: int,
    ) -> PolicyAttestationCampaign:
        pol = db.query(Policy).filter(
            Policy.id == campaign_in.policy_id,
            Policy.organization_id == organization_id,
        ).first()
        if not pol:
            raise ValueError("Target policy not found in your organization")

        version = db.query(PolicyVersion).filter(
            PolicyVersion.id == campaign_in.version_id,
            PolicyVersion.policy_id == pol.id,
        ).first()
        if not version:
            raise ValueError("Target policy version not found for this policy")

        # Check unique campaign code
        existing = db.query(PolicyAttestationCampaign).filter(
            PolicyAttestationCampaign.organization_id == organization_id,
            PolicyAttestationCampaign.campaign_code == campaign_in.campaign_code,
        ).first()
        if existing:
            raise ValueError(f"Campaign code '{campaign_in.campaign_code}' already exists.")

        # Ensure content hash exists
        policy_hash = version.content_hash_sha256 or PolicyService.compute_canonical_hash(version.content)

        campaign = PolicyAttestationCampaign(
            organization_id=organization_id,
            campaign_code=campaign_in.campaign_code,
            title=campaign_in.title,
            description=campaign_in.description,
            policy_id=campaign_in.policy_id,
            version_id=campaign_in.version_id,
            policy_version_hash=policy_hash,
            target_type=campaign_in.target_type,
            target_role=campaign_in.target_role,
            due_date=campaign_in.due_date,
            grace_period_days=campaign_in.grace_period_days,
            status=CampaignStatusEnum.DRAFT,
            assessment_id=campaign_in.assessment_id,
            total_targeted_count=0,
            completed_count=0,
            created_by_id=current_user_id,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def update_campaign(
        db: Session,
        campaign_id: int,
        organization_id: int,
        campaign_in: PolicyAttestationCampaignUpdate,
    ) -> PolicyAttestationCampaign:
        campaign = PolicyService.get_campaign(db, campaign_id, organization_id)
        if not campaign:
            raise ValueError("Campaign not found in your organization")

        # Frozen after launch
        if campaign.status != CampaignStatusEnum.DRAFT:
            raise ValueError(
                f"Cannot modify campaign in status '{campaign.status.value}'. Only DRAFT campaigns can be modified."
            )

        update_data = campaign_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(campaign, field, value)

        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def launch_campaign(
        db: Session,
        campaign_id: int,
        organization_id: int,
        current_user_id: int,
    ) -> PolicyAttestationCampaign:
        campaign = PolicyService.get_campaign(db, campaign_id, organization_id)
        if not campaign:
            raise ValueError("Campaign not found in your organization")

        if campaign.status != CampaignStatusEnum.DRAFT:
            raise ValueError(
                f"Cannot launch campaign in status '{campaign.status.value}'. Must be DRAFT."
            )

        # Target population enumeration (excluding inactive users)
        user_query = db.query(User).filter(
            User.organization_id == organization_id,
            User.is_active == True,
        )
        if campaign.target_type == CampaignTargetTypeEnum.ROLE_BASED and campaign.target_role:
            user_query = user_query.filter(User.role == campaign.target_role)

        target_users = user_query.all()

        # Idempotent creation of UserAttestationRecord rows
        records = []
        for u in target_users:
            rec = UserAttestationRecord(
                organization_id=organization_id,
                campaign_id=campaign.id,
                policy_id=campaign.policy_id,
                version_id=campaign.version_id,
                user_id=u.id,
                status=AttestationRecordStatusEnum.PENDING,
                comprehension_passed=(campaign.assessment_id is None),
            )
            records.append(rec)

        db.add_all(records)
        campaign.total_targeted_count = len(records)
        campaign.status = CampaignStatusEnum.ACTIVE
        campaign.launched_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def close_campaign(
        db: Session,
        campaign_id: int,
        organization_id: int,
        current_user_id: int,
    ) -> PolicyAttestationCampaign:
        campaign = PolicyService.get_campaign(db, campaign_id, organization_id)
        if not campaign:
            raise ValueError("Campaign not found in your organization")

        campaign.status = CampaignStatusEnum.COMPLETED
        campaign.closed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(campaign)
        return campaign

    # ── User Attestation Submission ─────────────────────────────────────────

    @staticmethod
    def get_user_pending_attestations(
        db: Session, user_id: int, organization_id: int
    ) -> List[Dict[str, Any]]:
        records = (
            db.query(UserAttestationRecord)
            .filter(
                UserAttestationRecord.user_id == user_id,
                UserAttestationRecord.organization_id == organization_id,
                UserAttestationRecord.status == AttestationRecordStatusEnum.PENDING,
            )
            .options(
                joinedload(UserAttestationRecord.campaign),
                joinedload(UserAttestationRecord.policy),
                joinedload(UserAttestationRecord.version),
            )
            .all()
        )

        results = []
        for r in records:
            results.append({
                "id": r.id,
                "organization_id": r.organization_id,
                "campaign_id": r.campaign_id,
                "policy_id": r.policy_id,
                "version_id": r.version_id,
                "user_id": r.user_id,
                "status": r.status,
                "attested_at": r.attested_at,
                "ip_address": r.ip_address,
                "user_agent": r.user_agent,
                "acknowledgement_text": r.acknowledgement_text,
                "comprehension_passed": r.comprehension_passed,
                "attestation_receipt_hash": r.attestation_receipt_hash,
                "evidence_item_id": r.evidence_item_id,
                "created_at": r.created_at,
                "policy_title": r.policy.title if r.policy else None,
                "policy_version_number": r.version.version_number if r.version else None,
                "campaign_title": r.campaign.title if r.campaign else None,
                "due_date": r.campaign.due_date if r.campaign else None,
            })
        return results

    @staticmethod
    def submit_user_attestation(
        db: Session,
        campaign_id: int,
        organization_id: int,
        current_user_id: int,
        attest_in: UserAttestationSubmit,
        client_ip: Optional[str] = None,
        client_ua: Optional[str] = None,
    ) -> UserAttestationRecord:
        campaign = PolicyService.get_campaign(db, campaign_id, organization_id)
        if not campaign:
            raise ValueError("Attestation campaign not found in your organization")

        if campaign.status != CampaignStatusEnum.ACTIVE:
            raise ValueError(f"Cannot submit attestation for campaign in status '{campaign.status.value}'. Campaign is not ACTIVE.")

        record = (
            db.query(UserAttestationRecord)
            .filter(
                UserAttestationRecord.campaign_id == campaign_id,
                UserAttestationRecord.user_id == current_user_id,
                UserAttestationRecord.organization_id == organization_id,
            )
            .first()
        )
        if not record:
            raise ValueError("You are not assigned to this attestation campaign.")

        if record.status == AttestationRecordStatusEnum.ATTESTED:
            raise ValueError("Duplicate attestation: You have already attested to this policy campaign.")

        # STRICT HASH CHECK: client verifies policy version hash
        if attest_in.policy_version_hash != campaign.policy_version_hash:
            raise ValueError(
                f"Policy version hash mismatch. Expected: {campaign.policy_version_hash}, Provided: {attest_in.policy_version_hash}"
            )

        # COMPREHENSION TEST CHECK: Reusing existing Assessment engine
        if campaign.assessment_id:
            assessment = (
                db.query(Assessment)
                .filter(
                    Assessment.id == campaign.assessment_id,
                    Assessment.organization_id == organization_id,
                )
                .first()
            )
            if not assessment or assessment.status != AssessmentStatusEnum.COMPLETED or assessment.conclusion != AssessmentConclusionEnum.EFFECTIVE:
                raise ValueError(
                    "Mandatory comprehension assessment not passed. You must complete and pass the assigned assessment before attesting."
                )

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # Deterministic Tamper-Evident Cryptographic Attestation Receipt
        canonical_str = (
            f"{organization_id}|{current_user_id}|{campaign.id}|{campaign.version_id}|"
            f"{campaign.policy_version_hash}|{now_iso}|{client_ip or 'unknown'}"
        )
        receipt_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        record.status = AttestationRecordStatusEnum.ATTESTED
        record.attested_at = now
        record.ip_address = client_ip
        record.user_agent = client_ua
        record.acknowledgement_text = attest_in.acknowledgement_text
        record.attestation_receipt_hash = receipt_hash
        record.comprehension_passed = True

        campaign.completed_count += 1
        if campaign.completed_count >= campaign.total_targeted_count and campaign.total_targeted_count > 0:
            campaign.status = CampaignStatusEnum.COMPLETED
            campaign.closed_at = now

        db.commit()
        db.refresh(record)
        return record

    # ── Evidence Integration ────────────────────────────────────────────────

    @staticmethod
    def generate_campaign_evidence(
        db: Session,
        campaign_id: int,
        organization_id: int,
        current_user_id: int,
    ) -> EvidenceItem:
        """Generates a tamper-evident campaign attestation manifest and creates a Phase 3 EvidenceItem in UPLOADED status."""
        campaign = PolicyService.get_campaign(db, campaign_id, organization_id)
        if not campaign:
            raise ValueError("Campaign not found in your organization")

        records = (
            db.query(UserAttestationRecord)
            .filter(
                UserAttestationRecord.campaign_id == campaign_id,
                UserAttestationRecord.organization_id == organization_id,
            )
            .all()
        )

        now = datetime.now(timezone.utc)
        manifest_data = {
            "campaign_id": campaign.id,
            "campaign_code": campaign.campaign_code,
            "campaign_title": campaign.title,
            "policy_id": campaign.policy_id,
            "policy_version_id": campaign.version_id,
            "policy_version_hash": campaign.policy_version_hash,
            "total_targeted": campaign.total_targeted_count,
            "total_completed": campaign.completed_count,
            "completion_rate": round((campaign.completed_count / campaign.total_targeted_count * 100), 2) if campaign.total_targeted_count else 0.0,
            "launched_at": campaign.launched_at.isoformat() if campaign.launched_at else None,
            "closed_at": campaign.closed_at.isoformat() if campaign.closed_at else None,
            "generated_at": now.isoformat(),
            "attestation_receipts": [
                {
                    "user_id": r.user_id,
                    "attested_at": r.attested_at.isoformat() if r.attested_at else None,
                    "receipt_hash": r.attestation_receipt_hash,
                }
                for r in records if r.status == AttestationRecordStatusEnum.ATTESTED
            ],
        }

        # Deterministic key-sorted JSON serialization for manifest
        manifest_json_bytes = json.dumps(manifest_data, sort_keys=True).encode("utf-8")
        manifest_sha256 = hashlib.sha256(manifest_json_bytes).hexdigest()

        # Deterministically resolve associated control through PolicyControlMapping
        ctrl = (
            db.query(OrganizationControl)
            .join(
                PolicyControlMapping,
                (PolicyControlMapping.subcategory_id == OrganizationControl.subcategory_id)
                & (PolicyControlMapping.organization_id == OrganizationControl.organization_id),
            )
            .filter(
                PolicyControlMapping.policy_id == campaign.policy_id,
                PolicyControlMapping.organization_id == organization_id,
                OrganizationControl.organization_id == organization_id,
            )
            .order_by(OrganizationControl.id.asc())
            .first()
        )
        if not ctrl:
            raise ValueError(
                "Cannot generate evidence manifest: Policy has no mapped OrganizationControl in your organization."
            )

        storage_dir = os.path.join(settings.EVIDENCE_STORAGE_ROOT, f"org_{organization_id}")
        os.makedirs(storage_dir, exist_ok=True)
        stored_filename = f"attestation_manifest_{campaign.campaign_code}_{int(now.timestamp())}.json"
        storage_path = os.path.join(storage_dir, stored_filename)

        with open(storage_path, "wb") as f:
            f.write(manifest_json_bytes)

        # STRICT INVARIANT: status = EvidenceStatusEnum.UPLOADED (Never auto-accepted)
        evidence_item = EvidenceItem(
            organization_id=organization_id,
            organization_control_id=ctrl.id,
            uploaded_by_id=current_user_id,
            title=f"Policy Attestation Manifest: {campaign.title} ({campaign.campaign_code})",
            description=f"Automated workforce attestation evidence manifest for policy campaign {campaign.campaign_code}. SHA256: {manifest_sha256}",
            original_filename=f"attestation_manifest_{campaign.campaign_code}.json",
            stored_filename=stored_filename,
            file_extension=".json",
            content_type="application/json",
            file_size=len(manifest_json_bytes),
            sha256_hash=manifest_sha256,
            storage_key=storage_path,
            status=EvidenceStatusEnum.UPLOADED,
        )
        db.add(evidence_item)
        db.commit()
        db.refresh(evidence_item)

        # Update evidence_item_id on attested records
        for r in records:
            if r.status == AttestationRecordStatusEnum.ATTESTED:
                r.evidence_item_id = evidence_item.id
        db.commit()

        return evidence_item

    # ── Control Mapping Operations ──────────────────────────────────────────

    @staticmethod
    def add_control_mapping(
        db: Session, policy_id: int, organization_id: int, subcategory_id: int
    ) -> Optional[PolicyControlMapping]:
        pol = (
            db.query(Policy)
            .filter(
                Policy.id == policy_id,
                Policy.organization_id == organization_id,
            )
            .first()
        )
        if not pol:
            return None

        if pol.status == PolicyStatusEnum.ARCHIVED:
            raise ValueError("Cannot map controls to an archived policy. Restore policy to DRAFT status first.")

        sub = db.query(FrameworkSubcategory).filter(FrameworkSubcategory.id == subcategory_id).first()
        if not sub:
            raise ValueError(f"Subcategory ID {subcategory_id} not found in framework catalog")

        existing = (
            db.query(PolicyControlMapping)
            .filter(
                PolicyControlMapping.organization_id == organization_id,
                PolicyControlMapping.policy_id == policy_id,
                PolicyControlMapping.subcategory_id == subcategory_id,
            )
            .first()
        )
        if existing:
            return existing

        mapping = PolicyControlMapping(
            organization_id=organization_id,
            policy_id=policy_id,
            subcategory_id=subcategory_id,
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping

    @staticmethod
    def remove_control_mapping(
        db: Session, policy_id: int, organization_id: int, subcategory_id: int
    ) -> bool:
        pol = (
            db.query(Policy)
            .filter(
                Policy.id == policy_id,
                Policy.organization_id == organization_id,
            )
            .first()
        )
        if not pol:
            return False

        if pol.status == PolicyStatusEnum.ARCHIVED:
            raise ValueError("Cannot unmap controls from an archived policy. Restore policy to DRAFT status first.")

        mapping = (
            db.query(PolicyControlMapping)
            .filter(
                PolicyControlMapping.organization_id == organization_id,
                PolicyControlMapping.policy_id == policy_id,
                PolicyControlMapping.subcategory_id == subcategory_id,
            )
            .first()
        )
        if not mapping:
            return False

        db.delete(mapping)
        db.commit()
        return True