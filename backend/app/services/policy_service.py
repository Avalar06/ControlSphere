import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.core.config import settings
from app.core.permissions import Permission, RoleEnum, has_permission
from app.core.risk_engine import calculate_exception_effective_status
from app.models.assessment import Assessment, AssessmentConclusionEnum, AssessmentStatusEnum
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.exception import ExceptionStatusEnum, ExceptionTypeEnum, SecurityException
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
    PolicyAttestationExemptionCreate,
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
                "versions": pol.versions,
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
                joinedload(Policy.versions).joinedload(PolicyVersion.approved_by),
                joinedload(Policy.versions)
                .joinedload(PolicyVersion.reviews)
                .joinedload(PolicyReviewWorkflow.created_by),
                joinedload(Policy.versions)
                .joinedload(PolicyVersion.reviews)
                .joinedload(PolicyReviewWorkflow.reviewed_by),
                joinedload(Policy.versions)
                .joinedload(PolicyVersion.reviews)
                .joinedload(PolicyReviewWorkflow.approved_by),
                joinedload(Policy.versions)
                .joinedload(PolicyVersion.reviews)
                .joinedload(PolicyReviewWorkflow.assigned_reviewer),
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
            .filter(
                PolicyVersion.policy_id == policy_id,
                PolicyVersion.organization_id == organization_id,
            )
            .options(
                joinedload(PolicyVersion.created_by),
                joinedload(PolicyVersion.approved_by),
                joinedload(PolicyVersion.reviews).joinedload(PolicyReviewWorkflow.assigned_reviewer),
                joinedload(PolicyVersion.reviews).joinedload(PolicyReviewWorkflow.reviewed_by),
                joinedload(PolicyVersion.reviews).joinedload(PolicyReviewWorkflow.approved_by),
                joinedload(PolicyVersion.reviews).joinedload(PolicyReviewWorkflow.created_by),
            )
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
            .filter(
                PolicyVersion.id == version_id,
                PolicyVersion.policy_id == policy_id,
                PolicyVersion.organization_id == organization_id,
            )
            .options(
                joinedload(PolicyVersion.created_by),
                joinedload(PolicyVersion.approved_by),
                joinedload(PolicyVersion.reviews).joinedload(PolicyReviewWorkflow.assigned_reviewer),
                joinedload(PolicyVersion.reviews).joinedload(PolicyReviewWorkflow.reviewed_by),
                joinedload(PolicyVersion.reviews).joinedload(PolicyReviewWorkflow.approved_by),
                joinedload(PolicyVersion.reviews).joinedload(PolicyReviewWorkflow.created_by),
            )
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
    def list_version_reviews(
        db: Session,
        policy_id: int,
        version_id: int,
        organization_id: int,
    ) -> List[PolicyReviewWorkflow]:
        version = PolicyService.get_policy_version(db, policy_id, version_id, organization_id)
        if not version:
            raise ValueError("Policy version not found in your organization")

        return (
            db.query(PolicyReviewWorkflow)
            .filter(
                PolicyReviewWorkflow.policy_id == policy_id,
                PolicyReviewWorkflow.version_id == version_id,
                PolicyReviewWorkflow.organization_id == organization_id,
            )
            .options(
                joinedload(PolicyReviewWorkflow.assigned_reviewer),
                joinedload(PolicyReviewWorkflow.reviewed_by),
                joinedload(PolicyReviewWorkflow.approved_by),
                joinedload(PolicyReviewWorkflow.created_by),
            )
            .order_by(PolicyReviewWorkflow.created_at.desc(), PolicyReviewWorkflow.id.desc())
            .all()
        )

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

        pol = db.query(Policy).filter(Policy.id == policy_id, Policy.organization_id == organization_id).first()
        if pol and pol.status == PolicyStatusEnum.ARCHIVED:
            raise ValueError("Cannot submit version for review on an archived policy.")

        if version.status not in [PolicyVersionStatusEnum.DRAFT]:
            raise ValueError(f"Cannot submit version in status '{version.status.value}' for review. Must be DRAFT.")

        existing_pending = (
            db.query(PolicyReviewWorkflow)
            .filter(
                PolicyReviewWorkflow.version_id == version.id,
                PolicyReviewWorkflow.organization_id == organization_id,
                PolicyReviewWorkflow.status == PolicyReviewStatusEnum.PENDING,
            )
            .first()
        )
        if existing_pending:
            raise ValueError("Policy version already has a PENDING review workflow.")

        if review_in.assigned_reviewer_id is not None:
            reviewer = (
                db.query(User)
                .filter(
                    User.id == review_in.assigned_reviewer_id,
                    User.organization_id == organization_id,
                )
                .first()
            )
            if not reviewer:
                raise ValueError("Assigned reviewer not found in your organization")
            if not reviewer.is_active:
                raise ValueError("Assigned reviewer is inactive and cannot review policy versions")
            if not has_permission(reviewer.role, Permission.POLICY_APPROVE):
                raise ValueError(
                    "Assigned reviewer does not have required review permissions (POLICY_APPROVE)"
                )
            if version.created_by_id == reviewer.id or current_user_id == reviewer.id:
                raise ValueError(
                    "Four-Eyes Violation: Assigned reviewer cannot be the version author or workflow submitter."
                )

        # Freeze canonical SHA-256 hash upon review submission
        version.content_hash_sha256 = PolicyService.compute_canonical_hash(version.content)
        version.status = PolicyVersionStatusEnum.UNDER_REVIEW

        if pol and pol.status == PolicyStatusEnum.DRAFT:
            pol.status = PolicyStatusEnum.UNDER_REVIEW

        wf_seq = (
            db.query(PolicyReviewWorkflow)
            .filter(PolicyReviewWorkflow.version_id == version.id)
            .count()
            + 1
        )
        workflow_code = f"WF-REV-{version.id}-{int(datetime.now(timezone.utc).timestamp())}-{wf_seq}"
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
                PolicyReviewWorkflow.policy_id == policy_id,
                PolicyReviewWorkflow.organization_id == organization_id,
            )
            .first()
        )
        if not workflow:
            raise ValueError("Policy review workflow not found")

        if workflow.status != PolicyReviewStatusEnum.PENDING:
            raise ValueError(
                f"Cannot review workflow in '{workflow.status.value}' status. Workflow has already been decided."
            )

        if version.status != PolicyVersionStatusEnum.UNDER_REVIEW:
            raise ValueError(
                f"Cannot review policy version in '{version.status.value}' status. Version must be UNDER_REVIEW."
            )

        if workflow.assigned_reviewer_id is not None and workflow.assigned_reviewer_id != current_user_id:
            raise ValueError(
                "Access denied: Only the assigned reviewer for this workflow may record a review decision."
            )

        decision = action_in.decision.upper().strip()
        if decision == "REQUEST_CHANGES":
            decision = "CHANGES_REQUESTED"

        now = datetime.now(timezone.utc)

        if decision == "APPROVE":
            # STRICT FOUR-EYES CHECK: Author or workflow submitter cannot approve their own version
            if version.created_by_id == current_user_id:
                raise ValueError("Four-Eyes Violation: The author/creator of a policy version cannot approve it.")
            if workflow.created_by_id and workflow.created_by_id == current_user_id:
                raise ValueError("Four-Eyes Violation: The user who submitted the review workflow cannot approve it.")

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
            if pol and pol.status != PolicyStatusEnum.PUBLISHED:
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
            pol = db.query(Policy).filter(Policy.id == policy_id, Policy.organization_id == organization_id).first()
            if pol and pol.status == PolicyStatusEnum.UNDER_REVIEW:
                pol.status = PolicyStatusEnum.DRAFT

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

        pol = db.query(Policy).filter(Policy.id == policy_id, Policy.organization_id == organization_id).first()
        if pol and pol.status == PolicyStatusEnum.ARCHIVED:
            raise ValueError("Cannot publish a version of an archived policy.")

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

        # 1. Cannot delete if bound to an active campaign (checked first for backwards compatibility)
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

        # 2. Only DRAFT versions may be deleted
        if version.status != PolicyVersionStatusEnum.DRAFT:
            raise ValueError(
                f"Cannot delete policy version in '{version.status.value}' status. Only DRAFT versions can be deleted."
            )

        # 3. Cannot delete if bound to any campaign (DRAFT, COMPLETED, CANCELLED)
        any_campaign = (
            db.query(PolicyAttestationCampaign)
            .filter(
                PolicyAttestationCampaign.version_id == version.id,
                PolicyAttestationCampaign.organization_id == organization_id,
            )
            .first()
        )
        if any_campaign:
            raise ValueError(
                f"Cannot delete policy version: it is referenced by attestation campaign '{any_campaign.campaign_code}'."
            )

        # 4. Cannot delete if referenced by any user attestation records
        has_records = (
            db.query(UserAttestationRecord)
            .filter(
                UserAttestationRecord.version_id == version.id,
                UserAttestationRecord.organization_id == organization_id,
            )
            .first()
        )
        if has_records:
            raise ValueError("Cannot delete policy version: it has associated workforce attestation records.")

        # 5. Cannot delete if it has review workflow history
        has_reviews = (
            db.query(PolicyReviewWorkflow)
            .filter(
                PolicyReviewWorkflow.version_id == version.id,
                PolicyReviewWorkflow.organization_id == organization_id,
            )
            .first()
        )
        if has_reviews:
            raise ValueError("Cannot delete policy version: it has historical review workflow records.")

        # 6. Cannot delete the sole remaining version of a policy
        version_count = (
            db.query(PolicyVersion)
            .filter(
                PolicyVersion.policy_id == policy_id,
                PolicyVersion.organization_id == organization_id,
            )
            .count()
        )
        if version_count <= 1:
            raise ValueError("Cannot delete the sole remaining version of a policy.")

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
    def _validate_campaign_targeting_and_assessment(
        db: Session,
        organization_id: int,
        target_type: CampaignTargetTypeEnum,
        target_role: Optional[str],
        assessment_id: Optional[int],
    ) -> None:
        if target_type == CampaignTargetTypeEnum.ROLE_BASED:
            if not target_role or not target_role.strip():
                raise ValueError("target_role is required when target_type is ROLE_BASED.")
            valid_roles = {r.value for r in RoleEnum}
            if target_role not in valid_roles:
                raise ValueError(
                    f"Invalid target_role '{target_role}'. Must be a valid ControlSphere role."
                )

        if assessment_id is not None:
            assessment = (
                db.query(Assessment)
                .filter(
                    Assessment.id == assessment_id,
                    Assessment.organization_id == organization_id,
                )
                .first()
            )
            if not assessment:
                raise ValueError("Assigned comprehension assessment not found in your organization.")

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

        if pol.status == PolicyStatusEnum.ARCHIVED:
            raise ValueError("Cannot create an attestation campaign for an archived policy.")

        version = db.query(PolicyVersion).filter(
            PolicyVersion.id == campaign_in.version_id,
            PolicyVersion.policy_id == pol.id,
            PolicyVersion.organization_id == organization_id,
        ).first()
        if not version:
            raise ValueError("Target policy version not found for this policy")

        if version.status in (PolicyVersionStatusEnum.ARCHIVED, PolicyVersionStatusEnum.SUPERSEDED):
            raise ValueError(
                f"Cannot create an attestation campaign for a policy version in '{version.status.value}' status."
            )

        PolicyService._validate_campaign_targeting_and_assessment(
            db=db,
            organization_id=organization_id,
            target_type=campaign_in.target_type,
            target_role=campaign_in.target_role,
            assessment_id=campaign_in.assessment_id,
        )

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
            overdue_count=0,
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
        effective_target_type = update_data.get("target_type", campaign.target_type)
        effective_target_role = update_data.get("target_role", campaign.target_role)
        effective_assessment_id = update_data.get("assessment_id", campaign.assessment_id)

        PolicyService._validate_campaign_targeting_and_assessment(
            db=db,
            organization_id=organization_id,
            target_type=effective_target_type,
            target_role=effective_target_role,
            assessment_id=effective_assessment_id,
        )

        for field, value in update_data.items():
            setattr(campaign, field, value)

        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def reconcile_campaign_counters(
        db: Session,
        campaign: PolicyAttestationCampaign,
        now: Optional[datetime] = None,
    ) -> None:
        now = now or datetime.now(timezone.utc)
        records = (
            db.query(UserAttestationRecord)
            .filter(
                UserAttestationRecord.campaign_id == campaign.id,
                UserAttestationRecord.organization_id == campaign.organization_id,
            )
            .all()
        )
        satisfied = sum(
            1
            for r in records
            if r.status in (AttestationRecordStatusEnum.ATTESTED, AttestationRecordStatusEnum.EXEMPTED)
        )
        overdue = sum(1 for r in records if r.status == AttestationRecordStatusEnum.OVERDUE)
        campaign.completed_count = satisfied
        campaign.overdue_count = overdue
        if (
            campaign.status == CampaignStatusEnum.ACTIVE
            and campaign.total_targeted_count > 0
            and campaign.completed_count >= campaign.total_targeted_count
        ):
            campaign.status = CampaignStatusEnum.COMPLETED
            campaign.closed_at = now

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

        if campaign.policy and campaign.policy.status == PolicyStatusEnum.ARCHIVED:
            raise ValueError("Cannot launch campaign: target policy is ARCHIVED.")

        if campaign.version and campaign.version.status in (
            PolicyVersionStatusEnum.ARCHIVED,
            PolicyVersionStatusEnum.SUPERSEDED,
        ):
            raise ValueError(
                f"Cannot launch campaign: target policy version is in '{campaign.version.status.value}' status."
            )

        # Target population enumeration (excluding inactive users)
        user_query = db.query(User).filter(
            User.organization_id == organization_id,
            User.is_active == True,
        )
        if campaign.target_type == CampaignTargetTypeEnum.ROLE_BASED and campaign.target_role:
            user_query = user_query.filter(User.role == campaign.target_role)

        target_users = user_query.all()
        if not target_users:
            raise ValueError(
                "Cannot launch attestation campaign: target audience resolved to 0 active users in your organization."
            )

        if campaign.version:
            campaign.policy_version_hash = (
                campaign.version.content_hash_sha256
                or PolicyService.compute_canonical_hash(campaign.version.content)
            )

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
        campaign.completed_count = 0
        campaign.overdue_count = 0
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

        if campaign.status != CampaignStatusEnum.ACTIVE:
            raise ValueError(
                f"Cannot close campaign in status '{campaign.status.value}'. Only ACTIVE campaigns can be closed."
            )

        campaign.status = CampaignStatusEnum.COMPLETED
        campaign.closed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def cancel_campaign(
        db: Session,
        campaign_id: int,
        organization_id: int,
        current_user_id: int,
        reason: Optional[str] = None,
    ) -> PolicyAttestationCampaign:
        campaign = PolicyService.get_campaign(db, campaign_id, organization_id)
        if not campaign:
            raise ValueError("Campaign not found in your organization")

        if campaign.status not in (CampaignStatusEnum.DRAFT, CampaignStatusEnum.ACTIVE):
            raise ValueError(
                f"Cannot cancel campaign in status '{campaign.status.value}'. Only DRAFT or ACTIVE campaigns can be cancelled."
            )

        campaign.status = CampaignStatusEnum.CANCELLED
        campaign.closed_at = datetime.now(timezone.utc)
        if reason and reason.strip():
            campaign.description = (
                f"{campaign.description or ''}\n[Cancelled]: {reason.strip()}".strip()
            )
        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def _serialize_attestation_record(r: UserAttestationRecord) -> Dict[str, Any]:
        return {
            "id": r.id,
            "record_id": r.id,
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
            "exemption_exception_id": r.exemption_exception_id,
            "exemption_reason": r.exemption_reason,
            "exempted_by_id": r.exempted_by_id,
            "exempted_at": r.exempted_at,
            "created_at": r.created_at,
            "policy_title": r.policy.title if r.policy else None,
            "policy_version_number": r.version.version_number if r.version else None,
            "version_number": r.version.version_number if r.version else None,
            "policy_version_hash": (
                r.campaign.policy_version_hash
                if r.campaign and r.campaign.policy_version_hash
                else (r.version.content_hash_sha256 if r.version else None)
            ),
            "policy_content": r.version.content if r.version else None,
            "campaign_title": r.campaign.title if r.campaign else None,
            "campaign_code": r.campaign.campaign_code if r.campaign else None,
            "due_date": r.campaign.due_date if r.campaign else None,
            "assessment_id": r.campaign.assessment_id if r.campaign else None,
        }

    @staticmethod
    def list_campaign_records(
        db: Session,
        campaign_id: int,
        organization_id: int,
        status: Optional[AttestationRecordStatusEnum] = None,
    ) -> List[Dict[str, Any]]:
        campaign = PolicyService.get_campaign(db, campaign_id, organization_id)
        if not campaign:
            raise ValueError("Campaign not found in your organization")

        query = (
            db.query(UserAttestationRecord)
            .filter(
                UserAttestationRecord.campaign_id == campaign_id,
                UserAttestationRecord.organization_id == organization_id,
            )
            .options(
                joinedload(UserAttestationRecord.campaign),
                joinedload(UserAttestationRecord.policy),
                joinedload(UserAttestationRecord.version),
                joinedload(UserAttestationRecord.user),
                joinedload(UserAttestationRecord.exempted_by),
            )
        )
        if status is not None:
            query = query.filter(UserAttestationRecord.status == status)

        records = query.order_by(UserAttestationRecord.id.asc()).all()
        return [PolicyService._serialize_attestation_record(r) for r in records]

    @staticmethod
    def evaluate_campaign_overdue(
        db: Session,
        campaign_id: int,
        organization_id: int,
        as_of_date: Optional[date] = None,
    ) -> PolicyAttestationCampaign:
        campaign = PolicyService.get_campaign(db, campaign_id, organization_id)
        if not campaign:
            raise ValueError("Campaign not found in your organization")

        if campaign.status != CampaignStatusEnum.ACTIVE:
            raise ValueError(
                f"Cannot evaluate overdue records for campaign in status '{campaign.status.value}'. Must be ACTIVE."
            )

        now = datetime.now(timezone.utc)
        ref_date = as_of_date or now.date()

        if campaign.due_date is not None:
            due_date_val = (
                campaign.due_date.date()
                if isinstance(campaign.due_date, datetime)
                else campaign.due_date
            )
            grace_days = campaign.grace_period_days if campaign.grace_period_days is not None else 0
            effective_deadline = due_date_val + timedelta(days=grace_days)
            if ref_date > effective_deadline:
                pending_records = (
                    db.query(UserAttestationRecord)
                    .filter(
                        UserAttestationRecord.campaign_id == campaign.id,
                        UserAttestationRecord.organization_id == organization_id,
                        UserAttestationRecord.status == AttestationRecordStatusEnum.PENDING,
                    )
                    .all()
                )
                for rec in pending_records:
                    rec.status = AttestationRecordStatusEnum.OVERDUE
                if pending_records:
                    campaign.reminder_sent_at = now

        db.flush()
        PolicyService.reconcile_campaign_counters(db, campaign, now)
        db.commit()
        db.refresh(campaign)
        return campaign

    @staticmethod
    def exempt_user_attestation(
        db: Session,
        campaign_id: int,
        record_id: int,
        organization_id: int,
        current_user_id: int,
        exempt_in: PolicyAttestationExemptionCreate,
    ) -> Dict[str, Any]:
        campaign = PolicyService.get_campaign(db, campaign_id, organization_id)
        if not campaign:
            raise ValueError("Attestation campaign not found in your organization")

        if campaign.status != CampaignStatusEnum.ACTIVE:
            raise ValueError(
                f"Cannot exempt attestation record on campaign in status '{campaign.status.value}'. Campaign must be ACTIVE."
            )

        record = (
            db.query(UserAttestationRecord)
            .filter(
                UserAttestationRecord.id == record_id,
                UserAttestationRecord.campaign_id == campaign_id,
                UserAttestationRecord.organization_id == organization_id,
            )
            .options(
                joinedload(UserAttestationRecord.campaign),
                joinedload(UserAttestationRecord.policy),
                joinedload(UserAttestationRecord.version),
            )
            .first()
        )
        if not record:
            raise ValueError("Attestation record not found in this campaign")

        if record.status == AttestationRecordStatusEnum.ATTESTED:
            raise ValueError("Cannot exempt an attestation record that has already been ATTESTED.")
        if record.status == AttestationRecordStatusEnum.EXEMPTED:
            raise ValueError("Attestation record is already EXEMPTED.")

        # Validate Phase 5 SecurityException
        sec_exc = (
            db.query(SecurityException)
            .filter(
                SecurityException.id == exempt_in.exemption_exception_id,
                SecurityException.organization_id == organization_id,
            )
            .first()
        )
        if not sec_exc:
            raise ValueError("Referenced SecurityException not found in your organization.")

        status_str = sec_exc.status.value if hasattr(sec_exc.status, "value") else str(sec_exc.status)
        effective_status = calculate_exception_effective_status(
            status_str, sec_exc.expiry_date, sec_exc.effective_date
        )
        if effective_status != "ACTIVE":
            raise ValueError(
                f"Referenced SecurityException must have effective status ACTIVE (current: '{effective_status}')."
            )

        if sec_exc.exception_type != ExceptionTypeEnum.POLICY_EXCEPTION:
            exc_type_str = (
                sec_exc.exception_type.value
                if hasattr(sec_exc.exception_type, "value")
                else str(sec_exc.exception_type)
            )
            raise ValueError(
                f"Referenced SecurityException must be of type POLICY_EXCEPTION (current: '{exc_type_str}')."
            )

        if sec_exc.linked_policy_id is not None and sec_exc.linked_policy_id != campaign.policy_id:
            raise ValueError(
                "Referenced SecurityException is linked to a different policy than this attestation campaign."
            )

        # Triple Four-Eyes SoD enforcement
        if record.user_id == current_user_id:
            raise ValueError("Four-Eyes Violation: You cannot grant a policy attestation exemption to yourself.")

        if sec_exc.reviewer_id is not None and sec_exc.reviewer_id == record.user_id:
            raise ValueError(
                "Four-Eyes Violation: Target user cannot be the approver/reviewer of their own policy exception."
            )

        if (
            sec_exc.requested_by_id is not None
            and sec_exc.reviewer_id is not None
            and sec_exc.requested_by_id == sec_exc.reviewer_id
        ):
            raise ValueError(
                "Four-Eyes Violation: Referenced SecurityException violates Four-Eyes governance (requester == reviewer)."
            )

        now = datetime.now(timezone.utc)
        canonical_str = (
            f"EXEMPT|{organization_id}|{record.user_id}|{campaign.id}|{campaign.version_id}|"
            f"{sec_exc.id}|{now.isoformat()}"
        )
        exemption_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        record.status = AttestationRecordStatusEnum.EXEMPTED
        record.exemption_exception_id = sec_exc.id
        record.exemption_reason = exempt_in.exemption_reason.strip()
        record.exempted_by_id = current_user_id
        record.exempted_at = now
        record.attestation_receipt_hash = exemption_hash

        db.flush()
        PolicyService.reconcile_campaign_counters(db, campaign, now)
        db.commit()
        db.refresh(record)
        return PolicyService._serialize_attestation_record(record)

    # ── User Attestation Submission ─────────────────────────────────────────

    @staticmethod
    def get_user_pending_attestations(
        db: Session, user_id: int, organization_id: int
    ) -> List[Dict[str, Any]]:
        records = (
            db.query(UserAttestationRecord)
            .join(
                PolicyAttestationCampaign,
                PolicyAttestationCampaign.id == UserAttestationRecord.campaign_id,
            )
            .filter(
                UserAttestationRecord.user_id == user_id,
                UserAttestationRecord.organization_id == organization_id,
                PolicyAttestationCampaign.organization_id == organization_id,
                PolicyAttestationCampaign.status == CampaignStatusEnum.ACTIVE,
                UserAttestationRecord.status.in_(
                    [AttestationRecordStatusEnum.PENDING, AttestationRecordStatusEnum.OVERDUE]
                ),
            )
            .options(
                joinedload(UserAttestationRecord.campaign),
                joinedload(UserAttestationRecord.policy),
                joinedload(UserAttestationRecord.version),
            )
            .order_by(UserAttestationRecord.id.asc())
            .all()
        )

        return [PolicyService._serialize_attestation_record(r) for r in records]

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

        if record.status == AttestationRecordStatusEnum.EXEMPTED:
            raise ValueError("This attestation record has already been exempted via an approved policy waiver.")

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

        db.flush()
        PolicyService.reconcile_campaign_counters(db, campaign, now)

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
            .order_by(UserAttestationRecord.id.asc())
            .all()
        )

        now = datetime.now(timezone.utc)
        PolicyService.reconcile_campaign_counters(db, campaign, now)

        manifest_data = {
            "campaign_id": campaign.id,
            "campaign_code": campaign.campaign_code,
            "campaign_title": campaign.title,
            "policy_id": campaign.policy_id,
            "policy_version_id": campaign.version_id,
            "policy_version_hash": campaign.policy_version_hash,
            "total_targeted": campaign.total_targeted_count,
            "total_completed": campaign.completed_count,
            "total_overdue": campaign.overdue_count,
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
            "exempted_receipts": [
                {
                    "user_id": r.user_id,
                    "exemption_exception_id": r.exemption_exception_id,
                    "exempted_by_id": r.exempted_by_id,
                    "exempted_at": r.exempted_at.isoformat() if r.exempted_at else None,
                    "receipt_hash": r.attestation_receipt_hash,
                }
                for r in records if r.status == AttestationRecordStatusEnum.EXEMPTED
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

        # Update evidence_item_id on attested and exempted records
        for r in records:
            if r.status in (AttestationRecordStatusEnum.ATTESTED, AttestationRecordStatusEnum.EXEMPTED):
                r.evidence_item_id = evidence_item.id
        db.commit()

        return evidence_item

    @staticmethod
    def get_policy_telemetry(db: Session, organization_id: int) -> Dict[str, Any]:
        today = datetime.now(timezone.utc).date()

        policies = (
            db.query(Policy)
            .filter(Policy.organization_id == organization_id)
            .all()
        )
        total_policies = len(policies)
        draft_policies = sum(1 for p in policies if p.status == PolicyStatusEnum.DRAFT)
        under_review_policies = sum(1 for p in policies if p.status == PolicyStatusEnum.UNDER_REVIEW)
        approved_policies = sum(1 for p in policies if p.status == PolicyStatusEnum.APPROVED)
        published_policies = sum(1 for p in policies if p.status == PolicyStatusEnum.PUBLISHED)
        archived_policies = sum(1 for p in policies if p.status == PolicyStatusEnum.ARCHIVED)
        overdue_review_policies = sum(
            1
            for p in policies
            if p.status != PolicyStatusEnum.ARCHIVED
            and p.review_date is not None
            and p.review_date < today
        )

        campaigns = (
            db.query(PolicyAttestationCampaign)
            .filter(PolicyAttestationCampaign.organization_id == organization_id)
            .all()
        )
        total_campaigns = len(campaigns)
        active_campaigns = sum(1 for c in campaigns if c.status == CampaignStatusEnum.ACTIVE)
        completed_campaigns = sum(1 for c in campaigns if c.status == CampaignStatusEnum.COMPLETED)
        cancelled_campaigns = sum(1 for c in campaigns if c.status == CampaignStatusEnum.CANCELLED)

        records = (
            db.query(UserAttestationRecord)
            .filter(UserAttestationRecord.organization_id == organization_id)
            .all()
        )
        total_targeted_records = len(records)
        attested_records = sum(1 for r in records if r.status == AttestationRecordStatusEnum.ATTESTED)
        exempted_records = sum(1 for r in records if r.status == AttestationRecordStatusEnum.EXEMPTED)
        pending_records = sum(1 for r in records if r.status == AttestationRecordStatusEnum.PENDING)
        overdue_records = sum(1 for r in records if r.status == AttestationRecordStatusEnum.OVERDUE)

        satisfied = attested_records + exempted_records
        overall_attestation_rate_pct = (
            round((satisfied / total_targeted_records) * 100.0, 2)
            if total_targeted_records > 0
            else 0.0
        )

        return {
            "total_policies": total_policies,
            "active_policy_count": published_policies,
            "draft_policies": draft_policies,
            "under_review_policies": under_review_policies,
            "policies_awaiting_approval": under_review_policies,
            "approved_policies": approved_policies,
            "published_policies": published_policies,
            "archived_policies": archived_policies,
            "overdue_review_policies": overdue_review_policies,
            "policies_due_for_review": overdue_review_policies,
            "total_campaigns": total_campaigns,
            "active_campaigns": active_campaigns,
            "completed_campaigns": completed_campaigns,
            "cancelled_campaigns": cancelled_campaigns,
            "total_targeted_records": total_targeted_records,
            "total_targeted_attestations": total_targeted_records,
            "target_count": total_targeted_records,
            "attested_records": attested_records,
            "total_attested_records": attested_records,
            "completed_attestations": attested_records,
            "exempted_records": exempted_records,
            "total_exempted_records": exempted_records,
            "exempted_attestations": exempted_records,
            "pending_records": pending_records,
            "total_pending_records": pending_records,
            "pending_attestations": pending_records,
            "overdue_records": overdue_records,
            "total_overdue_records": overdue_records,
            "overdue_attestations": overdue_records,
            "overall_attestation_rate_pct": overall_attestation_rate_pct,
            "overall_attestation_rate": overall_attestation_rate_pct,
            "completion_rate": overall_attestation_rate_pct,
        }



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