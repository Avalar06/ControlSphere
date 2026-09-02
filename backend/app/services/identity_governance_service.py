from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cloudsec import CloudAsset
from app.models.identity_governance import (
    AccessCertificationCampaign,
    AccessCertificationItem,
    AssignmentTypeEnum,
    CampaignStatusEnum,
    CampaignTypeEnum,
    CertificationDecisionEnum,
    EmploymentStatusEnum,
    GovernedIdentity,
    IdentityEntitlement,
    IdentityEntitlementAssignment,
    IdentityRiskBandEnum,
    IdentityTypeEnum,
    JITAccessRequest,
    JITApprovalStatusEnum,
    SoDConflictPolicy,
    SoDConflictViolation,
    SoDPolicySeverityEnum,
    SoDViolationStatusEnum,
    SystemTypeEnum,
    TrustLevelEnum,
    ZeroTrustAssessment,
)
from app.models.remediation import RemediationPlan
from app.models.user import User
from app.schemas.identity_governance import (
    AccessCertificationCampaignCreate,
    AccessCertificationItemReview,
    EntitlementAssignmentCreate,
    GovernedIdentityCreate,
    GovernedIdentityUpdate,
    IdentityEntitlementCreate,
    IdentityPostureSummaryResponse,
    JITAccessRequestCreate,
    JITAccessReviewRequest,
    SoDConflictPolicyCreate,
    ZeroTrustAssessmentCreate,
    ZeroTrustPreviewRequest,
    ZeroTrustPreviewResponse,
)
from app.services.audit_service import AuditService


class IdentityGovernanceService:
    """Authoritative service for Phase 19: IDENTITY-GRC."""

    @staticmethod
    def _audit_log(
        db: Session,
        organization_id: int,
        action: str,
        resource_type: str,
        actor_id: Optional[int] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict] = None,
        user_id: Optional[int] = None,
    ) -> None:
        effective_user_id = actor_id if actor_id is not None else user_id
        user = db.query(User).filter(User.id == effective_user_id).first() if effective_user_id else None
        actor_email = user.email if user else "system@control-sphere.internal"
        AuditService.log(
            db=db,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            actor_email=actor_email,
            actor_id=effective_user_id,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details or {},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Mathematical Formulas
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_identity_risk_score(
        entitlements: List[IdentityEntitlement],
        is_privileged: bool,
        mfa_enabled: bool,
        has_sod_violation: bool,
    ) -> Tuple[float, IdentityRiskBandEnum]:
        """
        Calculates authoritative Identity Risk Score (0.00 to 100.00).
        IRS = clamp(sum(w(entitlements)) + (Privileged ? 30 : 0) - (MFA ? 20 : 0) + (SoD ? 40 : 0), 0, 100)
        """
        entitlement_component = sum(float(e.risk_weight) * 5.0 for e in entitlements)
        privilege_penalty = 30.0 if is_privileged else 0.0
        mfa_credit = 20.0 if mfa_enabled else 0.0
        sod_penalty = 40.0 if has_sod_violation else 0.0

        raw_score = entitlement_component + privilege_penalty - mfa_credit + sod_penalty
        score = max(0.00, min(100.00, raw_score))
        score = round(score, 2)

        if score >= 75.0:
            band = IdentityRiskBandEnum.CRITICAL
        elif score >= 50.0:
            band = IdentityRiskBandEnum.HIGH
        elif score >= 25.0:
            band = IdentityRiskBandEnum.MODERATE
        else:
            band = IdentityRiskBandEnum.LOW

        return score, band

    @staticmethod
    def calculate_zero_trust_assurance(
        device_health: float,
        auth_strength: float,
        context_risk: float,
        anomaly_score: float,
    ) -> Tuple[float, TrustLevelEnum, Dict[str, float]]:
        """
        Calculates authoritative Zero Trust Assurance Score (0.00 to 100.00).
        ZTAS = clamp(0.35 * AuthStrength + 0.30 * DeviceHealth + 0.20 * (100 - ContextRisk) + 0.15 * (100 - AnomalyScore), 0, 100)
        """
        auth_comp = max(0.0, min(100.0, auth_strength)) * 0.35
        device_comp = max(0.0, min(100.0, device_health)) * 0.30
        context_comp = max(0.0, min(100.0, (100.0 - context_risk))) * 0.20
        anomaly_comp = max(0.0, min(100.0, (100.0 - anomaly_score))) * 0.15

        raw_score = auth_comp + device_comp + context_comp + anomaly_comp
        score = max(0.00, min(100.00, raw_score))
        score = round(score, 2)

        if score >= 85.0:
            level = TrustLevelEnum.HIGH_TRUST
        elif score >= 60.0:
            level = TrustLevelEnum.CONDITIONAL_TRUST
        elif score >= 35.0:
            level = TrustLevelEnum.LOW_TRUST
        else:
            level = TrustLevelEnum.UNTRUSTED

        breakdown = {
            "auth_component": auth_comp,
            "device_component": device_comp,
            "context_component": context_comp,
            "anomaly_component": anomaly_comp,
        }

        return score, level, breakdown

    # ─────────────────────────────────────────────────────────────────────────
    # Governed Identities
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create_identity(
        cls, db: Session, org_id: int, user_id: int, data: GovernedIdentityCreate
    ) -> GovernedIdentity:
        existing = (
            db.query(GovernedIdentity)
            .filter(
                GovernedIdentity.organization_id == org_id,
                (GovernedIdentity.identity_code == data.identity_code)
                | (GovernedIdentity.email == data.email),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Identity with code '{data.identity_code}' or email '{data.email}' already exists in tenant.",
            )

        if data.cloud_asset_id:
            asset = (
                db.query(CloudAsset)
                .filter(
                    CloudAsset.id == data.cloud_asset_id,
                    CloudAsset.organization_id == org_id,
                )
                .first()
            )
            if not asset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Cloud Asset #{data.cloud_asset_id} not found in tenant.",
                )

        if data.user_id:
            u = (
                db.query(User)
                .filter(
                    User.id == data.user_id,
                    User.organization_id == org_id,
                )
                .first()
            )
            if not u:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Platform User #{data.user_id} not found in tenant.",
                )

        # Calculate initial baseline risk score
        risk_score, risk_band = cls.calculate_identity_risk_score(
            entitlements=[],
            is_privileged=data.is_privileged,
            mfa_enabled=data.mfa_enabled,
            has_sod_violation=False,
        )

        identity = GovernedIdentity(
            organization_id=org_id,
            identity_code=data.identity_code,
            email=data.email,
            full_name=data.full_name,
            identity_type=data.identity_type,
            department=data.department,
            employment_status=data.employment_status,
            risk_score=risk_score,
            risk_band=risk_band,
            is_privileged=data.is_privileged,
            mfa_enabled=data.mfa_enabled,
            cloud_asset_id=data.cloud_asset_id,
            user_id=data.user_id,
        )
        db.add(identity)
        db.commit()
        db.refresh(identity)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="identity.create",
            resource_type="GovernedIdentity",
            resource_id=identity.id,
            details={"identity_code": identity.identity_code, "type": identity.identity_type.value},
        )
        return identity

    @classmethod
    def get_identity(cls, db: Session, org_id: int, identity_id: int) -> GovernedIdentity:
        identity = (
            db.query(GovernedIdentity)
            .filter(
                GovernedIdentity.id == identity_id,
                GovernedIdentity.organization_id == org_id,
            )
            .first()
        )
        if not identity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Governed Identity #{identity_id} not found.",
            )
        return identity

    @classmethod
    def list_identities(
        cls,
        db: Session,
        org_id: int,
        identity_type: Optional[IdentityTypeEnum] = None,
        employment_status: Optional[EmploymentStatusEnum] = None,
        risk_band: Optional[IdentityRiskBandEnum] = None,
    ) -> List[GovernedIdentity]:
        q = db.query(GovernedIdentity).filter(GovernedIdentity.organization_id == org_id)
        if identity_type:
            q = q.filter(GovernedIdentity.identity_type == identity_type)
        if employment_status:
            q = q.filter(GovernedIdentity.employment_status == employment_status)
        if risk_band:
            q = q.filter(GovernedIdentity.risk_band == risk_band)
        return q.order_by(GovernedIdentity.created_at.desc()).all()

    @classmethod
    def update_identity(
        cls, db: Session, org_id: int, user_id: int, identity_id: int, data: GovernedIdentityUpdate
    ) -> GovernedIdentity:
        identity = cls.get_identity(db, org_id, identity_id)

        if data.cloud_asset_id is not None:
            if data.cloud_asset_id > 0:
                asset = (
                    db.query(CloudAsset)
                    .filter(
                        CloudAsset.id == data.cloud_asset_id,
                        CloudAsset.organization_id == org_id,
                    )
                    .first()
                )
                if not asset:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Cloud Asset #{data.cloud_asset_id} not found in tenant.",
                    )
                identity.cloud_asset_id = data.cloud_asset_id
            else:
                identity.cloud_asset_id = None

        if data.user_id is not None:
            if data.user_id > 0:
                u = (
                    db.query(User)
                    .filter(
                        User.id == data.user_id,
                        User.organization_id == org_id,
                    )
                    .first()
                )
                if not u:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Platform User #{data.user_id} not found in tenant.",
                    )
                identity.user_id = data.user_id
            else:
                identity.user_id = None

        if data.full_name is not None:
            identity.full_name = data.full_name
        if data.department is not None:
            identity.department = data.department
        if data.employment_status is not None:
            identity.employment_status = data.employment_status
        if data.is_privileged is not None:
            identity.is_privileged = data.is_privileged
        if data.mfa_enabled is not None:
            identity.mfa_enabled = data.mfa_enabled

        # Recalculate identity risk score
        active_assignments = (
            db.query(IdentityEntitlementAssignment)
            .filter(
                IdentityEntitlementAssignment.identity_id == identity.id,
                IdentityEntitlementAssignment.organization_id == org_id,
                IdentityEntitlementAssignment.is_active == True,
            )
            .all()
        )
        entitlements = [a.entitlement for a in active_assignments if a.entitlement]

        sod_violations = (
            db.query(SoDConflictViolation)
            .filter(
                SoDConflictViolation.identity_id == identity.id,
                SoDConflictViolation.organization_id == org_id,
                SoDConflictViolation.status == SoDViolationStatusEnum.ACTIVE_VIOLATION,
            )
            .count()
        )

        score, band = cls.calculate_identity_risk_score(
            entitlements=entitlements,
            is_privileged=identity.is_privileged,
            mfa_enabled=identity.mfa_enabled,
            has_sod_violation=sod_violations > 0,
        )
        identity.risk_score = score
        identity.risk_band = band

        db.commit()
        db.refresh(identity)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="identity.update",
            resource_type="GovernedIdentity",
            resource_id=identity.id,
            details={"identity_code": identity.identity_code},
        )
        return identity

    @classmethod
    def delete_identity(cls, db: Session, org_id: int, user_id: int, identity_id: int) -> bool:
        identity = cls.get_identity(db, org_id, identity_id)
        if identity.employment_status == EmploymentStatusEnum.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active identities cannot be directly deleted. Suspend or terminate the identity first.",
            )

        db.delete(identity)
        db.commit()

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="identity.delete",
            resource_type="GovernedIdentity",
            resource_id=identity_id,
            details={"identity_code": identity.identity_code},
        )
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Entitlements & Assignments
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create_entitlement(
        cls, db: Session, org_id: int, user_id: int, data: IdentityEntitlementCreate
    ) -> IdentityEntitlement:
        existing = (
            db.query(IdentityEntitlement)
            .filter(
                IdentityEntitlement.organization_id == org_id,
                IdentityEntitlement.entitlement_code == data.entitlement_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Entitlement code '{data.entitlement_code}' already exists in tenant.",
            )

        ent = IdentityEntitlement(
            organization_id=org_id,
            entitlement_code=data.entitlement_code,
            name=data.name,
            system_type=data.system_type,
            resource_name=data.resource_name,
            permission_scope=data.permission_scope,
            is_privileged=data.is_privileged,
            is_high_risk=data.is_high_risk,
            risk_weight=data.risk_weight,
            description=data.description,
        )
        db.add(ent)
        db.commit()
        db.refresh(ent)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="identity.entitlement.create",
            resource_type="IdentityEntitlement",
            resource_id=ent.id,
            details={"code": ent.entitlement_code, "system": ent.system_type.value},
        )
        return ent

    @classmethod
    def list_entitlements(
        cls,
        db: Session,
        org_id: int,
        system_type: Optional[SystemTypeEnum] = None,
        is_privileged: Optional[bool] = None,
    ) -> List[IdentityEntitlement]:
        q = db.query(IdentityEntitlement).filter(IdentityEntitlement.organization_id == org_id)
        if system_type:
            q = q.filter(IdentityEntitlement.system_type == system_type)
        if is_privileged is not None:
            q = q.filter(IdentityEntitlement.is_privileged == is_privileged)
        return q.order_by(IdentityEntitlement.entitlement_code.asc()).all()

    @classmethod
    def assign_entitlement(
        cls, db: Session, org_id: int, user_id: int, identity_id: int, data: EntitlementAssignmentCreate
    ) -> IdentityEntitlementAssignment:
        identity = cls.get_identity(db, org_id, identity_id)

        ent = (
            db.query(IdentityEntitlement)
            .filter(
                IdentityEntitlement.id == data.entitlement_id,
                IdentityEntitlement.organization_id == org_id,
            )
            .first()
        )
        if not ent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entitlement #{data.entitlement_id} not found in tenant.",
            )

        existing = (
            db.query(IdentityEntitlementAssignment)
            .filter(
                IdentityEntitlementAssignment.organization_id == org_id,
                IdentityEntitlementAssignment.identity_id == identity_id,
                IdentityEntitlementAssignment.entitlement_id == data.entitlement_id,
            )
            .first()
        )
        if existing:
            existing.is_active = True
            existing.assignment_type = data.assignment_type
            existing.expires_at = data.expires_at
            assignment = existing
        else:
            assignment = IdentityEntitlementAssignment(
                organization_id=org_id,
                identity_id=identity_id,
                entitlement_id=data.entitlement_id,
                assignment_type=data.assignment_type,
                expires_at=data.expires_at,
                is_active=True,
            )
            db.add(assignment)

        # Check for SoD Conflict Policy triggers
        sod_policies = (
            db.query(SoDConflictPolicy)
            .filter(
                SoDConflictPolicy.organization_id == org_id,
                (
                    (SoDConflictPolicy.entitlement_a_id == ent.id)
                    | (SoDConflictPolicy.entitlement_b_id == ent.id)
                ),
            )
            .all()
        )
        for policy in sod_policies:
            conflicting_id = (
                policy.entitlement_b_id
                if policy.entitlement_a_id == ent.id
                else policy.entitlement_a_id
            )
            has_conflict = (
                db.query(IdentityEntitlementAssignment)
                .filter(
                    IdentityEntitlementAssignment.identity_id == identity_id,
                    IdentityEntitlementAssignment.entitlement_id == conflicting_id,
                    IdentityEntitlementAssignment.is_active == True,
                )
                .first()
            )
            if has_conflict:
                # Record SoD violation
                violation = SoDConflictViolation(
                    organization_id=org_id,
                    identity_id=identity_id,
                    policy_id=policy.id,
                    status=SoDViolationStatusEnum.ACTIVE_VIOLATION,
                )
                db.add(violation)

        # Recalculate identity risk score
        db.flush()
        active_assignments = (
            db.query(IdentityEntitlementAssignment)
            .filter(
                IdentityEntitlementAssignment.identity_id == identity.id,
                IdentityEntitlementAssignment.organization_id == org_id,
                IdentityEntitlementAssignment.is_active == True,
            )
            .all()
        )
        all_ents = [a.entitlement for a in active_assignments if a.entitlement]
        sod_count = (
            db.query(SoDConflictViolation)
            .filter(
                SoDConflictViolation.identity_id == identity.id,
                SoDConflictViolation.status == SoDViolationStatusEnum.ACTIVE_VIOLATION,
            )
            .count()
        )
        score, band = cls.calculate_identity_risk_score(
            all_ents, identity.is_privileged, identity.mfa_enabled, sod_count > 0
        )
        identity.risk_score = score
        identity.risk_band = band

        db.commit()
        db.refresh(assignment)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="identity.entitlement.assign",
            resource_type="IdentityEntitlementAssignment",
            resource_id=assignment.id,
            details={"identity_id": identity.id, "entitlement_id": ent.id},
        )
        return assignment

    @classmethod
    def list_identity_assignments(
        cls, db: Session, org_id: int, identity_id: int
    ) -> List[IdentityEntitlementAssignment]:
        cls.get_identity(db, org_id, identity_id)
        return (
            db.query(IdentityEntitlementAssignment)
            .filter(
                IdentityEntitlementAssignment.organization_id == org_id,
                IdentityEntitlementAssignment.identity_id == identity_id,
            )
            .all()
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Access Certification Campaigns (Four-Eyes SoD)
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create_campaign(
        cls, db: Session, org_id: int, user_id: int, data: AccessCertificationCampaignCreate
    ) -> AccessCertificationCampaign:
        existing = (
            db.query(AccessCertificationCampaign)
            .filter(
                AccessCertificationCampaign.organization_id == org_id,
                AccessCertificationCampaign.campaign_code == data.campaign_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Campaign code '{data.campaign_code}' already exists in tenant.",
            )

        campaign = AccessCertificationCampaign(
            organization_id=org_id,
            campaign_code=data.campaign_code,
            title=data.title,
            description=data.description,
            campaign_type=data.campaign_type,
            status=CampaignStatusEnum.ACTIVE,
            total_items_count=0,
            certified_items_count=0,
            revoked_items_count=0,
            deadline=data.deadline,
            created_by_id=user_id,
        )
        db.add(campaign)
        db.flush()

        # Seed certification items for all active entitlement assignments
        assignments = (
            db.query(IdentityEntitlementAssignment)
            .filter(
                IdentityEntitlementAssignment.organization_id == org_id,
                IdentityEntitlementAssignment.is_active == True,
            )
            .all()
        )

        for a in assignments:
            item = AccessCertificationItem(
                organization_id=org_id,
                campaign_id=campaign.id,
                identity_id=a.identity_id,
                entitlement_id=a.entitlement_id,
                decision=CertificationDecisionEnum.PENDING,
            )
            db.add(item)

        campaign.total_items_count = len(assignments)
        db.commit()
        db.refresh(campaign)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="identity.campaign.create",
            resource_type="AccessCertificationCampaign",
            resource_id=campaign.id,
            details={"code": campaign.campaign_code, "items_count": campaign.total_items_count},
        )
        return campaign

    @classmethod
    def list_campaigns(
        cls, db: Session, org_id: int, status_filter: Optional[CampaignStatusEnum] = None
    ) -> List[AccessCertificationCampaign]:
        q = db.query(AccessCertificationCampaign).filter(
            AccessCertificationCampaign.organization_id == org_id
        )
        if status_filter:
            q = q.filter(AccessCertificationCampaign.status == status_filter)
        return q.order_by(AccessCertificationCampaign.created_at.desc()).all()

    @classmethod
    def get_campaign(
        cls, db: Session, org_id: int, campaign_id: int
    ) -> AccessCertificationCampaign:
        camp = (
            db.query(AccessCertificationCampaign)
            .filter(
                AccessCertificationCampaign.id == campaign_id,
                AccessCertificationCampaign.organization_id == org_id,
            )
            .first()
        )
        if not camp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Access Campaign #{campaign_id} not found.",
            )
        return camp

    @classmethod
    def list_campaign_items(
        cls,
        db: Session,
        org_id: int,
        campaign_id: int,
        decision: Optional[CertificationDecisionEnum] = None,
    ) -> List[AccessCertificationItem]:
        cls.get_campaign(db, org_id, campaign_id)
        q = db.query(AccessCertificationItem).filter(
            AccessCertificationItem.organization_id == org_id,
            AccessCertificationItem.campaign_id == campaign_id,
        )
        if decision:
            q = q.filter(AccessCertificationItem.decision == decision)
        return q.order_by(AccessCertificationItem.id.asc()).all()

    @classmethod
    def review_certification_item(
        cls,
        db: Session,
        org_id: int,
        reviewer_id: int,
        item_id: int,
        review: AccessCertificationItemReview,
    ) -> AccessCertificationItem:
        item = (
            db.query(AccessCertificationItem)
            .filter(
                AccessCertificationItem.id == item_id,
                AccessCertificationItem.organization_id == org_id,
            )
            .first()
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification Item #{item_id} not found.",
            )

        campaign = item.campaign
        if campaign.status == CampaignStatusEnum.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot review items in a finalized access certification campaign.",
            )

        # Four-Eyes SoD Rule: Reviewer cannot certify themselves
        if item.identity.user_id == reviewer_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Four-Eyes SoD Violation: Users are strictly prohibited from certifying their own access entitlements.",
            )

        if review.remediation_plan_id:
            plan = (
                db.query(RemediationPlan)
                .filter(
                    RemediationPlan.id == review.remediation_plan_id,
                    RemediationPlan.organization_id == org_id,
                )
                .first()
            )
            if not plan:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Remediation Plan #{review.remediation_plan_id} not found in tenant.",
                )

        item.decision = review.decision
        item.decision_justification = review.decision_justification
        item.reviewer_id = reviewer_id
        item.reviewed_at = datetime.now(timezone.utc)
        item.remediation_plan_id = review.remediation_plan_id

        # If revoked, deactivate the assignment immediately
        if review.decision == CertificationDecisionEnum.REVOKED:
            assignment = (
                db.query(IdentityEntitlementAssignment)
                .filter(
                    IdentityEntitlementAssignment.identity_id == item.identity_id,
                    IdentityEntitlementAssignment.entitlement_id == item.entitlement_id,
                    IdentityEntitlementAssignment.organization_id == org_id,
                )
                .first()
            )
            if assignment:
                assignment.is_active = False

        # Recalculate campaign progress
        items = (
            db.query(AccessCertificationItem)
            .filter(AccessCertificationItem.campaign_id == campaign.id)
            .all()
        )
        campaign.certified_items_count = sum(
            1 for it in items if it.decision == CertificationDecisionEnum.CERTIFIED
        )
        campaign.revoked_items_count = sum(
            1 for it in items if it.decision == CertificationDecisionEnum.REVOKED
        )

        db.commit()
        db.refresh(item)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=reviewer_id,
            action="identity.cert_item.review",
            resource_type="AccessCertificationItem",
            resource_id=item.id,
            details={"decision": item.decision.value, "campaign_id": campaign.id},
        )
        return item

    @classmethod
    def finalize_campaign(
        cls, db: Session, org_id: int, user_id: int, campaign_id: int
    ) -> AccessCertificationCampaign:
        campaign = cls.get_campaign(db, org_id, campaign_id)
        if campaign.status == CampaignStatusEnum.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Access Certification Campaign is already finalized.",
            )

        campaign.status = CampaignStatusEnum.FINALIZED
        campaign.finalized_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(campaign)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="identity.campaign.finalize",
            resource_type="AccessCertificationCampaign",
            resource_id=campaign.id,
            details={"campaign_code": campaign.campaign_code},
        )
        return campaign

    # ─────────────────────────────────────────────────────────────────────────
    # Just-In-Time (JIT) Privileged Access (Four-Eyes SoD)
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create_jit_request(
        cls, db: Session, org_id: int, user_id: int, data: JITAccessRequestCreate
    ) -> JITAccessRequest:
        identity = cls.get_identity(db, org_id, data.identity_id)

        ent = (
            db.query(IdentityEntitlement)
            .filter(
                IdentityEntitlement.id == data.entitlement_id,
                IdentityEntitlement.organization_id == org_id,
            )
            .first()
        )
        if not ent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entitlement #{data.entitlement_id} not found in tenant.",
            )

        existing = (
            db.query(JITAccessRequest)
            .filter(
                JITAccessRequest.organization_id == org_id,
                JITAccessRequest.request_code == data.request_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"JIT request code '{data.request_code}' already exists in tenant.",
            )

        req = JITAccessRequest(
            organization_id=org_id,
            request_code=data.request_code,
            identity_id=data.identity_id,
            entitlement_id=data.entitlement_id,
            requested_duration_minutes=data.requested_duration_minutes,
            business_justification=data.business_justification,
            approval_status=JITApprovalStatusEnum.PENDING,
            requested_by_id=user_id,
            is_active=False,
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="identity.jit.request",
            resource_type="JITAccessRequest",
            resource_id=req.id,
            details={"code": req.request_code, "duration": req.requested_duration_minutes},
        )
        return req

    @classmethod
    def list_jit_requests(
        cls, db: Session, org_id: int, status_filter: Optional[JITApprovalStatusEnum] = None
    ) -> List[JITAccessRequest]:
        q = db.query(JITAccessRequest).filter(JITAccessRequest.organization_id == org_id)
        if status_filter:
            q = q.filter(JITAccessRequest.approval_status == status_filter)
        return q.order_by(JITAccessRequest.created_at.desc()).all()

    @classmethod
    def review_jit_request(
        cls,
        db: Session,
        org_id: int,
        reviewer_id: int,
        request_id: int,
        review: JITAccessReviewRequest,
    ) -> JITAccessRequest:
        req = (
            db.query(JITAccessRequest)
            .filter(
                JITAccessRequest.id == request_id,
                JITAccessRequest.organization_id == org_id,
            )
            .first()
        )
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"JIT Access Request #{request_id} not found.",
            )

        if req.approval_status != JITApprovalStatusEnum.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"JIT request is already in terminal state '{req.approval_status.value}'.",
            )

        # Four-Eyes SoD Rule: Requester cannot approve their own JIT elevation
        if req.requested_by_id == reviewer_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Four-Eyes SoD Violation: Requesters cannot approve their own Just-In-Time privilege elevation.",
            )

        req.approved_by_id = reviewer_id
        if review.approved:
            now = datetime.now(timezone.utc)
            req.approval_status = JITApprovalStatusEnum.APPROVED
            req.valid_from = now
            req.valid_until = now + timedelta(minutes=req.requested_duration_minutes)
            req.is_active = True
        else:
            req.approval_status = JITApprovalStatusEnum.REJECTED
            req.is_active = False

        db.commit()
        db.refresh(req)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=reviewer_id,
            action="identity.jit.review",
            resource_type="JITAccessRequest",
            resource_id=req.id,
            details={"approved": review.approved, "request_code": req.request_code},
        )
        return req

    # ─────────────────────────────────────────────────────────────────────────
    # Zero Trust Assurance
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def assess_zero_trust(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        identity_id: int,
        data: ZeroTrustAssessmentCreate,
    ) -> ZeroTrustAssessment:
        identity = cls.get_identity(db, org_id, identity_id)

        existing = (
            db.query(ZeroTrustAssessment)
            .filter(
                ZeroTrustAssessment.organization_id == org_id,
                ZeroTrustAssessment.assessment_code == data.assessment_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Zero Trust assessment code '{data.assessment_code}' already exists in tenant.",
            )

        score, trust_lvl, _ = cls.calculate_zero_trust_assurance(
            data.device_health_score,
            data.auth_strength_score,
            data.context_risk_score,
            data.behavioral_anomaly_score,
        )

        assessment = ZeroTrustAssessment(
            organization_id=org_id,
            assessment_code=data.assessment_code,
            identity_id=identity_id,
            device_health_score=data.device_health_score,
            auth_strength_score=data.auth_strength_score,
            context_risk_score=data.context_risk_score,
            behavioral_anomaly_score=data.behavioral_anomaly_score,
            zero_trust_assurance_score=score,
            trust_level=trust_lvl,
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="identity.zero_trust.assess",
            resource_type="ZeroTrustAssessment",
            resource_id=assessment.id,
            details={"identity_id": identity.id, "score": float(score)},
        )
        return assessment

    @classmethod
    def preview_zero_trust(cls, data: ZeroTrustPreviewRequest) -> ZeroTrustPreviewResponse:
        score, trust_lvl, breakdown = cls.calculate_zero_trust_assurance(
            data.device_health_score,
            data.auth_strength_score,
            data.context_risk_score,
            data.behavioral_anomaly_score,
        )
        return ZeroTrustPreviewResponse(
            zero_trust_assurance_score=score,
            trust_level=trust_lvl,
            breakdown=breakdown,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # SoD Policies & Violations
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create_sod_policy(
        cls, db: Session, org_id: int, user_id: int, data: SoDConflictPolicyCreate
    ) -> SoDConflictPolicy:
        if data.entitlement_a_id == data.entitlement_b_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="SoD Policy requires two distinct conflicting entitlements.",
            )

        # Validate entitlements exist in tenant
        for ent_id in [data.entitlement_a_id, data.entitlement_b_id]:
            ent = (
                db.query(IdentityEntitlement)
                .filter(
                    IdentityEntitlement.id == ent_id,
                    IdentityEntitlement.organization_id == org_id,
                )
                .first()
            )
            if not ent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Entitlement #{ent_id} not found in tenant.",
                )

        existing = (
            db.query(SoDConflictPolicy)
            .filter(
                SoDConflictPolicy.organization_id == org_id,
                SoDConflictPolicy.policy_code == data.policy_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SoD policy code '{data.policy_code}' already exists in tenant.",
            )

        policy = SoDConflictPolicy(
            organization_id=org_id,
            policy_code=data.policy_code,
            name=data.name,
            entitlement_a_id=data.entitlement_a_id,
            entitlement_b_id=data.entitlement_b_id,
            severity=data.severity,
            description=data.description,
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="identity.sod_policy.create",
            resource_type="SoDConflictPolicy",
            resource_id=policy.id,
            details={"code": policy.policy_code},
        )
        return policy

    @classmethod
    def list_sod_policies(cls, db: Session, org_id: int) -> List[SoDConflictPolicy]:
        return (
            db.query(SoDConflictPolicy)
            .filter(SoDConflictPolicy.organization_id == org_id)
            .order_by(SoDConflictPolicy.policy_code.asc())
            .all()
        )

    @classmethod
    def list_sod_violations(
        cls,
        db: Session,
        org_id: int,
        identity_id: Optional[int] = None,
        status_filter: Optional[SoDViolationStatusEnum] = None,
    ) -> List[SoDConflictViolation]:
        q = db.query(SoDConflictViolation).filter(SoDConflictViolation.organization_id == org_id)
        if identity_id:
            q = q.filter(SoDConflictViolation.identity_id == identity_id)
        if status_filter:
            q = q.filter(SoDConflictViolation.status == status_filter)
        return q.order_by(SoDConflictViolation.detected_at.desc()).all()

    # ─────────────────────────────────────────────────────────────────────────
    # Posture Summary
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def get_posture_summary(cls, db: Session, org_id: int) -> IdentityPostureSummaryResponse:
        identities = (
            db.query(GovernedIdentity).filter(GovernedIdentity.organization_id == org_id).all()
        )
        entitlements = (
            db.query(IdentityEntitlement).filter(IdentityEntitlement.organization_id == org_id).all()
        )
        violations = (
            db.query(SoDConflictViolation)
            .filter(SoDConflictViolation.organization_id == org_id)
            .all()
        )
        campaign_items = (
            db.query(AccessCertificationItem)
            .filter(AccessCertificationItem.organization_id == org_id)
            .all()
        )
        jit_requests = (
            db.query(JITAccessRequest).filter(JITAccessRequest.organization_id == org_id).all()
        )
        zt_assessments = (
            db.query(ZeroTrustAssessment).filter(ZeroTrustAssessment.organization_id == org_id).all()
        )

        total_identities = len(identities)
        privileged = sum(1 for i in identities if i.is_privileged)
        high_risk = sum(
            1 for i in identities if i.risk_band in [IdentityRiskBandEnum.HIGH, IdentityRiskBandEnum.CRITICAL]
        )
        active_sod = sum(
            1 for v in violations if v.status == SoDViolationStatusEnum.ACTIVE_VIOLATION
        )
        pending_certs = sum(
            1 for it in campaign_items if it.decision == CertificationDecisionEnum.PENDING
        )
        pending_jit = sum(
            1 for r in jit_requests if r.approval_status == JITApprovalStatusEnum.PENDING
        )

        avg_risk = (
            sum(float(i.risk_score) for i in identities) / total_identities
            if total_identities > 0
            else 0.00
        )
        avg_zt = (
            sum(float(z.zero_trust_assurance_score) for z in zt_assessments) / len(zt_assessments)
            if len(zt_assessments) > 0
            else 100.00
        )

        type_dist: Dict[str, int] = {}
        for i in identities:
            type_dist[i.identity_type.value] = type_dist.get(i.identity_type.value, 0) + 1

        sys_dist: Dict[str, int] = {}
        for e in entitlements:
            sys_dist[e.system_type.value] = sys_dist.get(e.system_type.value, 0) + 1

        return IdentityPostureSummaryResponse(
            total_identities=total_identities,
            privileged_identities_count=privileged,
            high_risk_identities_count=high_risk,
            active_sod_violations_count=active_sod,
            pending_certifications_count=pending_certs,
            pending_jit_requests_count=pending_jit,
            average_identity_risk_score=round(avg_risk, 2),
            average_zero_trust_score=round(avg_zt, 2),
            identity_type_distribution=type_dist,
            system_entitlement_distribution=sys_dist,
        )
