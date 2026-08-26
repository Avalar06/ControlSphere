from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.tprm import (
    BusinessCriticalityEnum,
    DataClassificationEnum,
    EngagementStatusEnum,
    HostingModelEnum,
    NetworkConnectivityEnum,
    PiiFinancialAccessEnum,
    Vendor,
    VendorAssessment,
    VendorAssessmentItem,
    VendorAssessmentStatusEnum,
    VendorAssessmentTypeEnum,
    VendorDocumentTypeEnum,
    VendorEngagement,
    VendorEvidenceLink,
    VendorResponseStatusEnum,
    VendorRiskBandEnum,
    VendorStatusEnum,
    VendorTierEnum,
)
from app.models.evidence import EvidenceItem, EvidenceStatusEnum


class TPRMService:
    """Authoritative Domain Engine for Phase 9 Third-Party & Vendor Risk Management."""

    # ─── 1. DETERMINISTIC SCORING CONSTANTS ──────────────────────────────────

    CRITICALITY_SCORES = {
        BusinessCriticalityEnum.CRITICAL: 100.0,
        BusinessCriticalityEnum.HIGH: 75.0,
        BusinessCriticalityEnum.MEDIUM: 50.0,
        BusinessCriticalityEnum.LOW: 25.0,
    }

    DATA_CLASSIFICATION_SCORES = {
        DataClassificationEnum.RESTRICTED: 100.0,
        DataClassificationEnum.CONFIDENTIAL: 75.0,
        DataClassificationEnum.INTERNAL: 50.0,
        DataClassificationEnum.PUBLIC: 10.0,
    }

    NETWORK_SCORES = {
        NetworkConnectivityEnum.DIRECT_API_VPN_DB: 100.0,
        NetworkConnectivityEnum.CORPORATE_SSO: 50.0,
        NetworkConnectivityEnum.ISOLATED_NO_CONNECTION: 10.0,
    }

    PII_FINANCIAL_SCORES = {
        PiiFinancialAccessEnum.DIRECT_PCI_PII_PHI: 100.0,
        PiiFinancialAccessEnum.METADATA_ONLY: 40.0,
        PiiFinancialAccessEnum.NONE: 0.0,
    }

    HOSTING_SCORES = {
        HostingModelEnum.MULTI_TENANT_SAAS: 100.0,
        HostingModelEnum.DEDICATED_CLOUD: 70.0,
        HostingModelEnum.ON_PREMISE: 40.0,
    }

    # Weights: 0.30 C + 0.30 D + 0.20 N + 0.10 P + 0.10 H
    WEIGHT_C = 0.30
    WEIGHT_D = 0.30
    WEIGHT_N = 0.20
    WEIGHT_P = 0.10
    WEIGHT_H = 0.10

    # ─── 2. INHERENT RISK & TIER ENGINE ──────────────────────────────────────

    @classmethod
    def calculate_engagement_risk(
        cls,
        criticality: BusinessCriticalityEnum,
        data_classification: DataClassificationEnum,
        network: NetworkConnectivityEnum,
        pii: PiiFinancialAccessEnum,
        hosting: HostingModelEnum,
    ) -> float:
        """Calculates single engagement inherent risk normalized 0.0 - 100.0."""
        c = cls.CRITICALITY_SCORES[criticality]
        d = cls.DATA_CLASSIFICATION_SCORES[data_classification]
        n = cls.NETWORK_SCORES[network]
        p = cls.PII_FINANCIAL_SCORES[pii]
        h = cls.HOSTING_SCORES[hosting]

        raw = (
            cls.WEIGHT_C * c
            + cls.WEIGHT_D * d
            + cls.WEIGHT_N * n
            + cls.WEIGHT_P * p
            + cls.WEIGHT_H * h
        )
        return round(min(max(raw, 0.0), 100.0), 1)

    @classmethod
    def calculate_vendor_inherent_risk_and_tier(
        cls, engagements: List[VendorEngagement]
    ) -> Tuple[float, VendorTierEnum]:
        """Calculates vendor inherent risk (max over active engagements) and deterministic tier."""
        active_engagements = [
            e for e in engagements if e.status == EngagementStatusEnum.ACTIVE
        ]

        if not active_engagements:
            return 0.0, VendorTierEnum.TIER_4_LOW

        # Maximum active engagement risk
        max_risk = 0.0
        has_critical_criticality = False

        for e in active_engagements:
            risk = cls.calculate_engagement_risk(
                e.criticality,
                e.data_classification,
                e.network_connectivity,
                e.pii_access,
                e.hosting_model,
            )
            e.calculated_risk_score = risk
            if risk > max_risk:
                max_risk = risk
            if e.criticality == BusinessCriticalityEnum.CRITICAL:
                has_critical_criticality = True

        inherent_risk = round(max_risk, 1)

        # Tier mapping
        if inherent_risk >= 80.0 or has_critical_criticality:
            calculated_tier = VendorTierEnum.TIER_1_CRITICAL
        elif inherent_risk >= 60.0:
            calculated_tier = VendorTierEnum.TIER_2_SIGNIFICANT
        elif inherent_risk >= 40.0:
            calculated_tier = VendorTierEnum.TIER_3_MODERATE
        else:
            calculated_tier = VendorTierEnum.TIER_4_LOW

        return inherent_risk, calculated_tier

    # ─── 3. ASSESSMENT SCORING ENGINE ────────────────────────────────────────

    @classmethod
    def calculate_assessment_score(cls, items: List[VendorAssessmentItem]) -> float:
        """Calculates assessment score based on item responses, excluding NOT_APPLICABLE."""
        applicable_items = [
            i for i in items if i.response_status != VendorResponseStatusEnum.NOT_APPLICABLE
        ]

        if not applicable_items:
            return 100.0

        total_weight = sum(i.weight for i in applicable_items)
        if total_weight <= 0:
            return 100.0

        weighted_score = 0.0
        for item in applicable_items:
            if item.response_status == VendorResponseStatusEnum.COMPLIANT:
                weighted_score += item.weight * 1.0
            elif item.response_status == VendorResponseStatusEnum.PARTIALLY_COMPLIANT:
                weighted_score += item.weight * 0.50
            elif item.response_status == VendorResponseStatusEnum.NON_COMPLIANT:
                weighted_score += item.weight * 0.0

        score = (weighted_score / total_weight) * 100.0
        return round(min(max(score, 0.0), 100.0), 1)

    # ─── 4. RESIDUAL RISK ENGINE ─────────────────────────────────────────────

    @classmethod
    def calculate_vendor_residual_risk(
        cls,
        inherent_risk: float,
        latest_assessment_score: Optional[float] = None,
        finding_penalties: float = 0.0,
        exception_penalties: float = 0.0,
    ) -> Tuple[float, VendorRiskBandEnum]:
        """
        Calculates vendor residual risk using risk retention floor and penalty accumulation:
        RiskFloor = 0.20 * InherentRisk
        BaseResidual = InherentRisk * (1.0 - 0.70 * AssessmentScore / 100.0)
        ResidualRisk = clamp(max(RiskFloor, BaseResidual) + FindingPenalties + ExceptionPenalties, 0.0, 100.0)
        """
        risk_floor = 0.20 * inherent_risk

        if latest_assessment_score is not None:
            norm_score = min(max(latest_assessment_score, 0.0), 100.0)
            base_residual = inherent_risk * (1.0 - (0.70 * (norm_score / 100.0)))
        else:
            base_residual = inherent_risk

        attenuated_risk = max(risk_floor, base_residual)
        total_residual = attenuated_risk + finding_penalties + exception_penalties
        clamped_residual = round(min(max(total_residual, 0.0), 100.0), 1)

        # Risk band mapping
        if clamped_residual < 40.0:
            band = VendorRiskBandEnum.LOW
        elif clamped_residual < 60.0:
            band = VendorRiskBandEnum.MODERATE
        elif clamped_residual < 80.0:
            band = VendorRiskBandEnum.HIGH
        else:
            band = VendorRiskBandEnum.CRITICAL

        return clamped_residual, band

    # ─── 5. VENDOR LIFECYCLE MANAGEMENT ──────────────────────────────────────

    LEGAL_VENDOR_TRANSITIONS = {
        VendorStatusEnum.PROSPECT: {
            VendorStatusEnum.DUE_DILIGENCE,
            VendorStatusEnum.TERMINATED,
        },
        VendorStatusEnum.DUE_DILIGENCE: {
            VendorStatusEnum.APPROVED,
            VendorStatusEnum.TERMINATED,
        },
        VendorStatusEnum.APPROVED: {
            VendorStatusEnum.ACTIVE,
            VendorStatusEnum.TERMINATED,
        },
        VendorStatusEnum.ACTIVE: {
            VendorStatusEnum.UNDER_REVIEW,
            VendorStatusEnum.OFFBOARDED,
            VendorStatusEnum.TERMINATED,
        },
        VendorStatusEnum.UNDER_REVIEW: {
            VendorStatusEnum.ACTIVE,
            VendorStatusEnum.OFFBOARDED,
            VendorStatusEnum.TERMINATED,
        },
        VendorStatusEnum.OFFBOARDED: {
            VendorStatusEnum.DUE_DILIGENCE,
            VendorStatusEnum.TERMINATED,
        },
        VendorStatusEnum.TERMINATED: set(),  # Terminal state
    }

    @classmethod
    def validate_vendor_transition(
        cls,
        current_status: VendorStatusEnum,
        new_status: VendorStatusEnum,
        db: Optional[Session] = None,
        vendor: Optional[Vendor] = None,
    ) -> None:
        """Validates that a vendor transition is legal according to the lifecycle state machine."""
        if current_status == new_status:
            return
        allowed = cls.LEGAL_VENDOR_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid vendor lifecycle transition from {current_status} to {new_status}. "
                f"Allowed target states: {sorted([s.value for s in allowed])}"
            )

        # DUE_DILIGENCE -> APPROVED requires at least one approved assessment
        if (
            current_status == VendorStatusEnum.DUE_DILIGENCE
            and new_status == VendorStatusEnum.APPROVED
            and db is not None
            and vendor is not None
        ):
            has_approved_assessment = (
                db.query(VendorAssessment)
                .filter(
                    VendorAssessment.vendor_id == vendor.id,
                    VendorAssessment.status.in_(
                        [VendorAssessmentStatusEnum.APPROVED, VendorAssessmentStatusEnum.SUPERSEDED]
                    ),
                )
                .first()
            )
            if not has_approved_assessment:
                raise ValueError(
                    "Vendor approval requires at least one approved vendor assessment."
                )

    # ─── 6. VENDOR ASSESSMENT LIFECYCLE & IMMUTABILITY ──────────────────────

    LEGAL_ASSESSMENT_TRANSITIONS = {
        VendorAssessmentStatusEnum.DRAFT: {
            VendorAssessmentStatusEnum.SUBMITTED,
        },
        VendorAssessmentStatusEnum.SUBMITTED: {
            VendorAssessmentStatusEnum.IN_REVIEW,
        },
        VendorAssessmentStatusEnum.IN_REVIEW: {
            VendorAssessmentStatusEnum.APPROVED,
            VendorAssessmentStatusEnum.REJECTED,
        },
        VendorAssessmentStatusEnum.REJECTED: {
            VendorAssessmentStatusEnum.DRAFT,
        },
        VendorAssessmentStatusEnum.APPROVED: {
            VendorAssessmentStatusEnum.SUPERSEDED,
        },
        VendorAssessmentStatusEnum.SUPERSEDED: set(),  # Immutable historical record
    }

    @classmethod
    def validate_assessment_transition(
        cls,
        current_status: VendorAssessmentStatusEnum,
        new_status: VendorAssessmentStatusEnum,
    ) -> None:
        """Validates assessment lifecycle transitions."""
        if current_status == new_status:
            return
        allowed = cls.LEGAL_ASSESSMENT_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid assessment transition from {current_status} to {new_status}. "
                f"Allowed target states: {sorted([s.value for s in allowed])}"
            )

    @classmethod
    def approve_assessment(
        cls,
        db: Session,
        assessment: VendorAssessment,
        reviewer_id: int,
        review_notes: Optional[str] = None,
    ) -> VendorAssessment:
        """
        Approves an in-review assessment with strict separation of duties,
        recalculates score, and supersedes previous approved assessments.
        """
        if assessment.status != VendorAssessmentStatusEnum.IN_REVIEW:
            raise ValueError(
                f"Only assessments in {VendorAssessmentStatusEnum.IN_REVIEW} can be approved."
            )

        # Separation of Duties check
        if assessment.assessor_id == reviewer_id:
            raise ValueError(
                "Separation of duties violation: The assessor cannot approve their own assessment."
            )

        # Calculate final authoritative score
        assessment.calculated_score = cls.calculate_assessment_score(assessment.items)
        now = datetime.now(timezone.utc)

        # Supersede any previously approved assessments for this vendor
        previous_approved = (
            db.query(VendorAssessment)
            .filter(
                VendorAssessment.vendor_id == assessment.vendor_id,
                VendorAssessment.status == VendorAssessmentStatusEnum.APPROVED,
                VendorAssessment.id != assessment.id,
            )
            .all()
        )
        for prev in previous_approved:
            prev.status = VendorAssessmentStatusEnum.SUPERSEDED
            prev.updated_at = now

        assessment.status = VendorAssessmentStatusEnum.APPROVED
        assessment.reviewer_id = reviewer_id
        assessment.reviewed_at = now
        assessment.review_notes = review_notes
        assessment.updated_at = now

        # Update vendor residual risk
        cls.recalculate_vendor_telemetry(db, assessment.vendor)

        db.flush()
        return assessment

    # ─── 7. RECALCULATE VENDOR COMPLETE TELEMETRY ────────────────────────────

    @classmethod
    def recalculate_vendor_telemetry(cls, db: Session, vendor: Vendor) -> Vendor:
        """Recalculates inherent risk, calculated tier, and residual risk for a vendor."""
        # 1. Inherent risk & Tier from active engagements
        inherent_risk, calculated_tier = cls.calculate_vendor_inherent_risk_and_tier(
            vendor.engagements
        )
        vendor.calculated_inherent_risk = inherent_risk
        vendor.calculated_tier = calculated_tier

        # 2. Latest approved assessment score
        latest_assessment = (
            db.query(VendorAssessment)
            .filter(
                VendorAssessment.vendor_id == vendor.id,
                VendorAssessment.status == VendorAssessmentStatusEnum.APPROVED,
            )
            .order_by(desc(VendorAssessment.reviewed_at))
            .first()
        )
        latest_score = latest_assessment.calculated_score if latest_assessment else None

        # 3. Calculate finding & exception penalties
        from app.models.exception import SecurityException, ExceptionStatusEnum, ExceptionTypeEnum
        active_exceptions = (
            db.query(SecurityException)
            .filter(
                SecurityException.organization_id == vendor.organization_id,
                SecurityException.status == ExceptionStatusEnum.ACTIVE,
                SecurityException.exception_type == ExceptionTypeEnum.THIRD_PARTY_VENDOR,
            )
            .count()
        )
        exception_penalties = active_exceptions * 10.0

        # Calculate finding penalties for items with non-zero findings
        finding_penalties = 0.0
        if latest_assessment:
            for item in latest_assessment.items:
                if item.findings_count > 0:
                    finding_penalties += min(item.findings_count * 8.0, 30.0)

        # 4. Residual risk & Risk band
        residual_risk, risk_band = cls.calculate_vendor_residual_risk(
            inherent_risk=inherent_risk,
            latest_assessment_score=latest_score,
            finding_penalties=finding_penalties,
            exception_penalties=exception_penalties,
        )
        vendor.residual_risk_score = residual_risk
        vendor.risk_band = risk_band
        vendor.updated_at = datetime.now(timezone.utc)

        db.flush()
        return vendor
