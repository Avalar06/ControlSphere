import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.models.harmonization import CommonControlMapping
from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.exception import (
    ExceptionStatusEnum,
    ExceptionTypeEnum,
    SecurityException,
)
from app.models.finding import (
    Finding,
    FindingSeverityEnum,
    FindingStatusEnum,
    FindingTypeEnum,
)
from app.models.framework import (
    Framework,
    FrameworkCategory,
    FrameworkFunction,
    FrameworkSubcategory,
)
from app.models.remediation import (
    RemediationPlan,
    RemediationRootCauseClassificationEnum,
    RemediationSeverityEnum,
    RemediationSourceTypeEnum,
    RemediationStatusEnum,
)
from app.models.risk import (
    Risk,
    RiskCategoryEnum,
    RiskSourceEnum,
    RiskStatusEnum,
    RiskTreatmentStrategyEnum,
)
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
    VendorContract,
    VendorContractStatusEnum,
    VendorContractTypeEnum,
    VendorDocumentTypeEnum,
    VendorEngagement,
    VendorEvidenceLink,
    VendorOffboardingItem,
    VendorOffboardingItemStatusEnum,
    VendorOffboardingRecord,
    VendorOffboardingStatusEnum,
    VendorOffboardingStepTypeEnum,
    VendorOffboardingTargetStatusEnum,
    VendorResponseStatusEnum,
    VendorRiskBandEnum,
    VendorSlaBreach,
    VendorSlaBreachSeverityEnum,
    VendorSlaBreachStatusEnum,
    VendorSlaComparisonOperatorEnum,
    VendorSlaMetricTypeEnum,
    VendorSlaObligation,
    VendorSlaObligationStatusEnum,
    VendorStatusEnum,
    VendorSubprocessor,
    VendorSubprocessorStatusEnum,
    VendorTierEnum,
)
from app.models.user import User
from app.schemas.tprm import (
    ConcentrationRiskNodeRead,
    ConcentrationRiskReportResponse,
    VendorAssessmentItemEscalateRequest,
    VendorContractCreate,
    VendorContractReview,
    VendorContractUpdate,
    VendorOffboardingCancelRequest,
    VendorOffboardingCompleteRequest,
    VendorOffboardingInitiateRequest,
    VendorOffboardingItemAttestRequest,
    VendorOffboardingItemWaiveRequest,
    VendorSlaBreachCreate,
    VendorSlaBreachEscalateRequest,
    VendorSlaBreachReopenRequest,
    VendorSlaBreachResolveRequest,
    VendorSlaBreachVerifyCloseRequest,
    VendorSlaBreachWaiveRequest,
    VendorSlaObligationCreate,
    VendorSlaObligationUpdate,
    VendorSubprocessorCreate,
    VendorSubprocessorReview,
    VendorSubprocessorUpdate,
)


class ConflictError(ValueError):
    """Domain exception mapped to HTTP 409 Conflict."""


class UnprocessableEntityError(ValueError):
    """Domain exception mapped to HTTP 422 Unprocessable Entity."""


class TPRMService:
    """Authoritative Domain Engine for Phase 9 & Batch 6 Third-Party & Vendor Risk Management."""

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

    FINDING_SEVERITY_PENALTY = {
        FindingSeverityEnum.CRITICAL: 15.0,
        FindingSeverityEnum.HIGH: 8.0,
        FindingSeverityEnum.MEDIUM: 3.0,
        FindingSeverityEnum.LOW: 1.0,
        FindingSeverityEnum.INFORMATIONAL: 0.0,
    }

    SLA_BREACH_SEVERITY_PENALTY = {
        VendorSlaBreachSeverityEnum.CRITICAL: 12.0,
        VendorSlaBreachSeverityEnum.HIGH: 7.0,
        VendorSlaBreachSeverityEnum.MAJOR: 7.0,
        VendorSlaBreachSeverityEnum.MEDIUM: 3.0,
        VendorSlaBreachSeverityEnum.MINOR: 1.0,
        VendorSlaBreachSeverityEnum.LOW: 1.0,
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
        sla_breach_penalties: float = 0.0,
        subprocessor_penalties: float = 0.0,
    ) -> Tuple[float, VendorRiskBandEnum]:
        """
        Calculates vendor residual risk using risk retention floor and multi-factor penalty accumulation:
        RiskFloor = 0.20 * InherentRisk
        BaseResidual = InherentRisk * (1.0 - 0.70 * AssessmentScore / 100.0)
        ResidualRisk = clamp(max(RiskFloor, BaseResidual) + Finding + Exception + SLABreach + Subprocessor, 0.0, 100.0)
        """
        risk_floor = 0.20 * inherent_risk

        if latest_assessment_score is not None:
            norm_score = min(max(latest_assessment_score, 0.0), 100.0)
            base_residual = inherent_risk * (1.0 - (0.70 * (norm_score / 100.0)))
        else:
            base_residual = inherent_risk

        attenuated_risk = max(risk_floor, base_residual)
        total_residual = (
            attenuated_risk
            + finding_penalties
            + exception_penalties
            + sla_breach_penalties
            + subprocessor_penalties
        )
        clamped_residual = round(min(max(total_residual, 0.0), 100.0), 1)

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

        if db is not None and vendor is not None:
            # 1. DUE_DILIGENCE -> APPROVED requires at least one approved assessment
            if (
                current_status == VendorStatusEnum.DUE_DILIGENCE
                and new_status == VendorStatusEnum.APPROVED
            ):
                has_approved_assessment = (
                    db.query(VendorAssessment)
                    .filter(
                        VendorAssessment.vendor_id == vendor.id,
                        VendorAssessment.status.in_(
                            [
                                VendorAssessmentStatusEnum.APPROVED,
                                VendorAssessmentStatusEnum.SUPERSEDED,
                            ]
                        ),
                    )
                    .first()
                )
                if not has_approved_assessment:
                    raise ValueError(
                        "Vendor approval requires at least one approved vendor assessment."
                    )

            # 2. APPROVED -> ACTIVE for Tier 1 / Tier 2 requires an APPROVED or ACTIVE contract
            if (
                current_status == VendorStatusEnum.APPROVED
                and new_status == VendorStatusEnum.ACTIVE
            ):
                eff_tier = vendor.effective_tier
                if eff_tier in (
                    VendorTierEnum.TIER_1_CRITICAL,
                    VendorTierEnum.TIER_2_SIGNIFICANT,
                ):
                    now = datetime.now(timezone.utc)
                    active_contracts = (
                        db.query(VendorContract)
                        .filter(
                            VendorContract.organization_id == vendor.organization_id,
                            VendorContract.vendor_id == vendor.id,
                            VendorContract.status.in_(
                                [
                                    VendorContractStatusEnum.APPROVED,
                                    VendorContractStatusEnum.ACTIVE,
                                ]
                            ),
                        )
                        .all()
                    )
                    valid_contract = False
                    for c in active_contracts:
                        exp = c.expiry_date
                        if exp is not None and exp.tzinfo is None:
                            exp = exp.replace(tzinfo=timezone.utc)
                        if exp is None or exp > now:
                            valid_contract = True
                            break
                    if not valid_contract:
                        raise ValueError(
                            f"Cannot activate {eff_tier.value} vendor without an APPROVED or ACTIVE non-expired contract."
                        )

            # 3. Direct transition to OFFBOARDED (or TERMINATED when offboarding or engagements/contracts exist)
            # requires a COMPLETED VendorOffboardingRecord
            if new_status == VendorStatusEnum.OFFBOARDED:
                completed_offboarding = (
                    db.query(VendorOffboardingRecord)
                    .filter(
                        VendorOffboardingRecord.organization_id == vendor.organization_id,
                        VendorOffboardingRecord.vendor_id == vendor.id,
                        VendorOffboardingRecord.status == VendorOffboardingStatusEnum.COMPLETED,
                    )
                    .first()
                )
                if not completed_offboarding:
                    raise ValueError(
                        "Direct transition to OFFBOARDED is prohibited without a COMPLETED and verified VendorOffboardingRecord."
                    )

            if (
                new_status == VendorStatusEnum.TERMINATED
                and current_status in (VendorStatusEnum.ACTIVE, VendorStatusEnum.UNDER_REVIEW)
            ):
                has_offboarding_or_scope = (
                    current_status == VendorStatusEnum.UNDER_REVIEW
                    or vendor.effective_tier != VendorTierEnum.TIER_4_LOW
                    or bool(vendor.engagements)
                    or bool(getattr(vendor, "contracts", []))
                    or bool(getattr(vendor, "subprocessors", []))
                    or bool(getattr(vendor, "offboarding_records", []))
                )
                if has_offboarding_or_scope:
                    completed_offboarding = (
                        db.query(VendorOffboardingRecord)
                        .filter(
                            VendorOffboardingRecord.organization_id == vendor.organization_id,
                            VendorOffboardingRecord.vendor_id == vendor.id,
                            VendorOffboardingRecord.status == VendorOffboardingStatusEnum.COMPLETED,
                        )
                        .first()
                    )
                    if not completed_offboarding:
                        raise ValueError(
                            "Direct transition to TERMINATED for an engaged or under-review vendor requires a COMPLETED and verified VendorOffboardingRecord."
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

        if assessment.assessor_id == reviewer_id:
            raise ValueError(
                "Separation of duties violation: The assessor cannot approve their own assessment."
            )

        assessment.calculated_score = cls.calculate_assessment_score(assessment.items)
        now = datetime.now(timezone.utc)

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

        cls.recalculate_vendor_telemetry(db, assessment.vendor)

        db.flush()
        return assessment

    # ─── 7. RECALCULATE VENDOR COMPLETE TELEMETRY ────────────────────────────

    @classmethod
    def compute_vendor_penalty_breakdown(
        cls,
        db: Session,
        vendor: Vendor,
        latest_assessment: Optional[VendorAssessment] = None,
    ) -> Dict[str, Any]:
        """Computes granular penalty breakdown across Findings, Exceptions, SLA Breaches, and Subprocessors."""
        organization_id = vendor.organization_id
        now = datetime.now(timezone.utc)
        today = now.date()

        # 1. Finding penalties:
        #    (a) Linked canonical Findings (OPEN, IN_REMEDIATION, PENDING_VALIDATION)
        #    (b) Legacy unlinked item.findings_count fallback
        linked_finding_ids = set()
        item_finding_rows = (
            db.query(VendorAssessmentItem.linked_finding_id)
            .join(
                VendorAssessment,
                VendorAssessment.id == VendorAssessmentItem.assessment_id,
            )
            .filter(
                VendorAssessment.organization_id == organization_id,
                VendorAssessment.vendor_id == vendor.id,
                VendorAssessmentItem.linked_finding_id.isnot(None),
            )
            .all()
        )
        for (fid,) in item_finding_rows:
            if fid:
                linked_finding_ids.add(fid)

        breach_finding_rows = (
            db.query(VendorSlaBreach.linked_finding_id)
            .filter(
                VendorSlaBreach.organization_id == organization_id,
                VendorSlaBreach.vendor_id == vendor.id,
                VendorSlaBreach.linked_finding_id.isnot(None),
            )
            .all()
        )
        for (fid,) in breach_finding_rows:
            if fid:
                linked_finding_ids.add(fid)

        raw_finding_penalty = 0.0
        if linked_finding_ids:
            open_findings = (
                db.query(Finding)
                .filter(
                    Finding.organization_id == organization_id,
                    Finding.id.in_(linked_finding_ids),
                    Finding.status.in_(
                        [
                            FindingStatusEnum.OPEN,
                            FindingStatusEnum.IN_REMEDIATION,
                            FindingStatusEnum.PENDING_VALIDATION,
                        ]
                    ),
                )
                .all()
            )
            for f in open_findings:
                raw_finding_penalty += cls.FINDING_SEVERITY_PENALTY.get(f.severity, 0.0)

        if latest_assessment:
            for item in latest_assessment.items:
                if item.findings_count > 0 and item.linked_finding_id is None:
                    raw_finding_penalty += min(item.findings_count * 8.0, 30.0)

        finding_penalties = round(min(raw_finding_penalty, 40.0), 1)

        # 2. Exception penalties:
        #    Strictly scoped to vendor-linked SecurityExceptions (SEC-B6-46)
        active_exceptions = (
            db.query(SecurityException)
            .filter(
                SecurityException.organization_id == organization_id,
                SecurityException.linked_vendor_id == vendor.id,
                SecurityException.status.in_(
                    [ExceptionStatusEnum.APPROVED, ExceptionStatusEnum.ACTIVE]
                ),
            )
            .all()
        )
        valid_exception_count = 0
        for exc in active_exceptions:
            if exc.expiry_date is None or exc.expiry_date >= today:
                valid_exception_count += 1
        exception_penalties = round(min(valid_exception_count * 10.0, 30.0), 1)

        # 3. SLA Breach penalties:
        open_breaches = (
            db.query(VendorSlaBreach)
            .filter(
                VendorSlaBreach.organization_id == organization_id,
                VendorSlaBreach.vendor_id == vendor.id,
                VendorSlaBreach.status.in_(
                    [
                        VendorSlaBreachStatusEnum.OPEN,
                        VendorSlaBreachStatusEnum.UNDER_INVESTIGATION,
                        VendorSlaBreachStatusEnum.ESCALATED,
                        VendorSlaBreachStatusEnum.ESCALATED_TO_FINDING,
                    ]
                ),
            )
            .all()
        )
        raw_sla_penalty = sum(
            cls.SLA_BREACH_SEVERITY_PENALTY.get(b.severity, 0.0) for b in open_breaches
        )
        sla_breach_penalties = round(min(raw_sla_penalty, 25.0), 1)

        # 4. Subprocessor penalties:
        subprocessors = (
            db.query(VendorSubprocessor)
            .filter(
                VendorSubprocessor.organization_id == organization_id,
                VendorSubprocessor.vendor_id == vendor.id,
            )
            .all()
        )
        raw_subprocessor_penalty = 0.0
        approved_subprocessors_count = 0
        for sp in subprocessors:
            if sp.status == VendorSubprocessorStatusEnum.APPROVED:
                approved_subprocessors_count += 1
            if sp.status == VendorSubprocessorStatusEnum.TERMINATED:
                continue
            if sp.status == VendorSubprocessorStatusEnum.SUSPENDED:
                raw_subprocessor_penalty += 6.0
            elif (
                sp.criticality == BusinessCriticalityEnum.CRITICAL
                and sp.status != VendorSubprocessorStatusEnum.APPROVED
            ):
                raw_subprocessor_penalty += 8.0
            elif (
                sp.data_classification == DataClassificationEnum.RESTRICTED
                and not sp.contractual_flowdown_verified
            ):
                raw_subprocessor_penalty += 5.0
        subprocessor_penalties = round(min(raw_subprocessor_penalty, 20.0), 1)

        return {
            "finding_penalties": finding_penalties,
            "exception_penalties": exception_penalties,
            "sla_breach_penalties": sla_breach_penalties,
            "subprocessor_penalties": subprocessor_penalties,
            "open_sla_breaches_count": len(open_breaches),
            "approved_subprocessors_count": approved_subprocessors_count,
        }

    @classmethod
    def recalculate_vendor_telemetry(
        cls,
        db: Session,
        vendor_or_id: Union[Vendor, int],
        organization_id: Optional[int] = None,
    ) -> Optional[Vendor]:
        """Recalculates inherent risk, calculated tier, Batch 6 counters, and multi-factor residual risk."""
        if isinstance(vendor_or_id, Vendor):
            vendor = vendor_or_id
        else:
            query = db.query(Vendor).filter(Vendor.id == vendor_or_id)
            if organization_id is not None:
                query = query.filter(Vendor.organization_id == organization_id)
            vendor = query.first()
            if not vendor:
                return None

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

        # 3. Calculate multi-factor penalties
        penalties = cls.compute_vendor_penalty_breakdown(
            db=db, vendor=vendor, latest_assessment=latest_assessment
        )

        # 4. Residual risk & Risk band
        residual_risk, risk_band = cls.calculate_vendor_residual_risk(
            inherent_risk=inherent_risk,
            latest_assessment_score=latest_score,
            finding_penalties=penalties["finding_penalties"],
            exception_penalties=penalties["exception_penalties"],
            sla_breach_penalties=penalties["sla_breach_penalties"],
            subprocessor_penalties=penalties["subprocessor_penalties"],
        )
        vendor.residual_risk_score = residual_risk
        vendor.risk_band = risk_band
        vendor.open_sla_breaches_count = penalties["open_sla_breaches_count"]
        vendor.approved_subprocessors_count = penalties["approved_subprocessors_count"]
        vendor.updated_at = datetime.now(timezone.utc)

        db.flush()
        return vendor

    # ─── 8. BATCH 6: EVIDENCE INTEGRITY & CONTROL RESOLUTION HELPERS ─────────

    @classmethod
    def _verify_evidence_integrity(
        cls,
        db: Session,
        evidence_id: int,
        organization_id: int,
        require_accepted: bool = True,
    ) -> EvidenceItem:
        evidence = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == evidence_id,
                EvidenceItem.organization_id == organization_id,
            )
            .first()
        )
        if not evidence:
            raise LookupError("Evidence item not found in your organization.")

        if evidence.status in (
            EvidenceStatusEnum.REJECTED,
            EvidenceStatusEnum.EXPIRED,
            EvidenceStatusEnum.SUPERSEDED,
        ):
            raise UnprocessableEntityError(
                f"Cannot link evidence in '{evidence.status.value}' status."
            )
        if require_accepted and evidence.status != EvidenceStatusEnum.ACCEPTED:
            raise UnprocessableEntityError(
                f"Evidence item must be in ACCEPTED status (current: {evidence.status.value})."
            )

        now_utc = datetime.now(timezone.utc)
        if evidence.valid_until is not None:
            valid_until = evidence.valid_until
            if valid_until.tzinfo is None:
                valid_until = valid_until.replace(tzinfo=timezone.utc)
            if valid_until < now_utc:
                raise UnprocessableEntityError(
                    "Evidence item has expired (valid_until is in the past)."
                )

        if not evidence.sha256_hash or len(evidence.sha256_hash.strip()) != 64:
            raise UnprocessableEntityError(
                "Evidence item lacks a valid 64-character SHA-256 cryptographic digest."
            )
        return evidence

    @classmethod
    def _verify_snapshot_digest(
        cls,
        db: Session,
        evidence_id: int,
        snapshot_hash: Optional[str],
        organization_id: int,
    ) -> EvidenceItem:
        ev = cls._verify_evidence_integrity(
            db, evidence_id, organization_id, require_accepted=True
        )
        if snapshot_hash and ev.sha256_hash != snapshot_hash:
            raise ConflictError(
                "Tamper-evident SHA-256 cryptographic digest mismatch detected on linked evidence."
            )
        return ev

    @classmethod
    def _resolve_organization_control(
        cls,
        db: Session,
        organization_id: int,
        explicit_control_id: Optional[int],
        fallback_control_id: Optional[int] = None,
        common_control_id: Optional[int] = None,
    ) -> OrganizationControl:
        ctrl_id = explicit_control_id or fallback_control_id
        if ctrl_id is not None:
            ctrl = (
                db.query(OrganizationControl)
                .filter(OrganizationControl.id == ctrl_id)
                .first()
            )
            if not ctrl:
                raise UnprocessableEntityError(
                    "Referenced organization control does not exist."
                )
            if ctrl.organization_id != organization_id:
                raise LookupError(
                    "Referenced organization control not found in your organization."
                )
            return ctrl

        if common_control_id is not None:
            mapping = (
                db.query(CommonControlMapping)
                .filter(
                    CommonControlMapping.organization_id == organization_id,
                    CommonControlMapping.rationalized_common_control_id == common_control_id,
                )
                .first()
            )
            if mapping and mapping.organization_control_id:
                ctrl = (
                    db.query(OrganizationControl)
                    .filter(
                        OrganizationControl.id == mapping.organization_control_id,
                        OrganizationControl.organization_id == organization_id,
                    )
                    .first()
                )
                if ctrl:
                    return ctrl

        raise UnprocessableEntityError(
            "Escalation requires a valid organization_control_id or mapped common control in your organization."
        )

    # ─── 9. BATCH 6: VENDOR CONTRACTS & LEGAL ASSURANCE ─────────────────────

    @classmethod
    def create_contract(
        cls,
        db: Session,
        vendor: Vendor,
        payload: VendorContractCreate,
        creator_id: int,
    ) -> VendorContract:
        organization_id = vendor.organization_id
        if vendor.vendor_status in (
            VendorStatusEnum.OFFBOARDED,
            VendorStatusEnum.TERMINATED,
        ):
            raise ValueError(
                f"Cannot create contract for vendor in '{vendor.vendor_status.value}' status."
            )

        existing = (
            db.query(VendorContract)
            .filter(
                VendorContract.organization_id == organization_id,
                VendorContract.vendor_id == vendor.id,
                VendorContract.contract_code == payload.contract_code.strip(),
            )
            .first()
        )
        if existing:
            raise ConflictError(
                f"Contract code '{payload.contract_code}' already exists for this vendor."
            )

        if payload.expiry_date and payload.expiry_date <= payload.effective_date:
            raise UnprocessableEntityError(
                "Contract expiry_date must be strictly after effective_date."
            )

        if payload.engagement_id is not None:
            eng = (
                db.query(VendorEngagement)
                .filter(
                    VendorEngagement.id == payload.engagement_id,
                    VendorEngagement.organization_id == organization_id,
                    VendorEngagement.vendor_id == vendor.id,
                )
                .first()
            )
            if not eng:
                raise LookupError("Linked engagement not found for this vendor.")

        sha256_snapshot = None
        if payload.evidence_id is not None:
            ev = cls._verify_evidence_integrity(
                db, payload.evidence_id, organization_id, require_accepted=True
            )
            sha256_snapshot = ev.sha256_hash

        contract = VendorContract(
            organization_id=organization_id,
            vendor_id=vendor.id,
            engagement_id=payload.engagement_id,
            contract_code=payload.contract_code.strip(),
            title=payload.title.strip(),
            contract_type=payload.contract_type,
            status=VendorContractStatusEnum.DRAFT,
            effective_date=payload.effective_date,
            expiry_date=payload.expiry_date,
            auto_renew=payload.auto_renew,
            notice_period_days=payload.notice_period_days,
            dpa_included=payload.dpa_included,
            right_to_audit_clause=payload.right_to_audit_clause,
            subprocessor_authorization_clause=payload.subprocessor_authorization_clause,
            exit_strategy_clause=payload.exit_strategy_clause,
            incident_notification_hours_clause=payload.incident_notification_hours_clause,
            governing_jurisdiction=payload.governing_jurisdiction,
            regulatory_mandates_applicable=payload.regulatory_mandates_applicable,
            evidence_id=payload.evidence_id,
            evidence_sha256_snapshot=sha256_snapshot,
            created_by_id=creator_id,
        )
        db.add(contract)
        db.flush()
        return contract

    @classmethod
    def update_contract(
        cls,
        db: Session,
        contract: VendorContract,
        payload: VendorContractUpdate,
    ) -> VendorContract:
        if contract.status not in (
            VendorContractStatusEnum.DRAFT,
            VendorContractStatusEnum.REJECTED,
        ):
            raise ValueError(
                f"Cannot modify contract in '{contract.status.value}' status; only DRAFT or REJECTED contracts are editable."
            )

        update_data = payload.model_dump(exclude_unset=True)
        new_eff = update_data.get("effective_date", contract.effective_date)
        new_exp = update_data.get("expiry_date", contract.expiry_date)
        if new_eff and new_exp and new_exp <= new_eff:
            raise UnprocessableEntityError(
                "Contract expiry_date must be strictly after effective_date."
            )

        if "engagement_id" in update_data and update_data["engagement_id"] is not None:
            eng = (
                db.query(VendorEngagement)
                .filter(
                    VendorEngagement.id == update_data["engagement_id"],
                    VendorEngagement.organization_id == contract.organization_id,
                    VendorEngagement.vendor_id == contract.vendor_id,
                )
                .first()
            )
            if not eng:
                raise LookupError("Linked engagement not found for this vendor.")

        if "evidence_id" in update_data:
            if update_data["evidence_id"] is not None:
                ev = cls._verify_evidence_integrity(
                    db,
                    update_data["evidence_id"],
                    contract.organization_id,
                    require_accepted=True,
                )
                contract.evidence_sha256_snapshot = ev.sha256_hash
            else:
                contract.evidence_sha256_snapshot = None

        for k, v in update_data.items():
            setattr(contract, k, v)

        contract.updated_at = datetime.now(timezone.utc)
        db.flush()
        return contract

    @classmethod
    def submit_contract(
        cls,
        db: Session,
        contract: VendorContract,
        submitter_id: int,
    ) -> VendorContract:
        if contract.status not in (
            VendorContractStatusEnum.DRAFT,
            VendorContractStatusEnum.REJECTED,
        ):
            raise ValueError(
                f"Only DRAFT or REJECTED contracts can be submitted for review (current: {contract.status.value})."
            )
        contract.status = VendorContractStatusEnum.UNDER_REVIEW
        contract.submitted_by_id = submitter_id
        contract.submitted_at = datetime.now(timezone.utc)
        contract.updated_at = datetime.now(timezone.utc)
        db.flush()
        return contract

    @classmethod
    def approve_contract(
        cls,
        db: Session,
        contract: VendorContract,
        approver_id: int,
        payload: VendorContractReview,
    ) -> VendorContract:
        if contract.status in (
            VendorContractStatusEnum.APPROVED,
            VendorContractStatusEnum.ACTIVE,
        ):
            raise ConflictError("Contract is already approved.")
        if contract.status != VendorContractStatusEnum.UNDER_REVIEW:
            raise ValueError(
                f"Only UNDER_REVIEW contracts can be approved (current: {contract.status.value})."
            )
        if contract.created_by_id == approver_id or contract.submitted_by_id == approver_id:
            raise PermissionError(
                "Four-eyes separation of duties violation: Contract creator or submitter cannot approve their own contract."
            )

        if contract.contract_type in (
            VendorContractTypeEnum.MSA,
            VendorContractTypeEnum.DPA,
            VendorContractTypeEnum.SLA_ADDENDUM,
        ) and contract.evidence_id is None:
            raise UnprocessableEntityError(
                f"Approving a {contract.contract_type.value} contract requires an ACCEPTED EvidenceItem."
            )

        if contract.evidence_id is not None:
            ev = cls._verify_snapshot_digest(
                db,
                contract.evidence_id,
                contract.evidence_sha256_snapshot,
                contract.organization_id,
            )
            contract.evidence_sha256_snapshot = ev.sha256_hash

        now = datetime.now(timezone.utc)
        eff = contract.effective_date
        if eff.tzinfo is None:
            eff = eff.replace(tzinfo=timezone.utc)

        prior_contracts = (
            db.query(VendorContract)
            .filter(
                VendorContract.organization_id == contract.organization_id,
                VendorContract.vendor_id == contract.vendor_id,
                VendorContract.contract_type == contract.contract_type,
                VendorContract.status.in_(
                    [VendorContractStatusEnum.APPROVED, VendorContractStatusEnum.ACTIVE]
                ),
                VendorContract.id != contract.id,
            )
            .all()
        )
        for p in prior_contracts:
            p.status = VendorContractStatusEnum.SUPERSEDED
            p.updated_at = now

        contract.status = (
            VendorContractStatusEnum.ACTIVE
            if eff <= now
            else VendorContractStatusEnum.APPROVED
        )
        contract.approved_by_id = approver_id
        contract.approved_at = now
        contract.review_notes = payload.review_notes
        contract.updated_at = now
        db.flush()
        return contract

    @classmethod
    def reject_contract(
        cls,
        db: Session,
        contract: VendorContract,
        reviewer_id: int,
        payload: VendorContractReview,
    ) -> VendorContract:
        if contract.status != VendorContractStatusEnum.UNDER_REVIEW:
            raise ValueError(
                f"Only UNDER_REVIEW contracts can be rejected (current: {contract.status.value})."
            )
        if contract.created_by_id == reviewer_id or contract.submitted_by_id == reviewer_id:
            raise PermissionError(
                "Four-eyes separation of duties violation: Contract creator or submitter cannot reject their own contract."
            )
        reason = payload.rejection_reason or payload.reason or payload.review_notes
        if not reason or len(reason.strip()) < 5:
            raise ValueError("Rejection reason (minimum 5 characters) is required.")

        contract.status = VendorContractStatusEnum.DRAFT
        contract.rejection_reason = reason.strip()
        contract.review_notes = payload.review_notes
        contract.updated_at = datetime.now(timezone.utc)
        db.flush()
        return contract

    # ─── 10. BATCH 6: SUBPROCESSORS & CONCENTRATION RISK ────────────────────

    @classmethod
    def _validate_no_subprocessor_cycle(
        cls,
        db: Session,
        organization_id: int,
        vendor_id: int,
        subprocessor_vendor_id: Optional[int],
    ) -> None:
        if subprocessor_vendor_id is None:
            return
        if subprocessor_vendor_id == vendor_id:
            raise UnprocessableEntityError(
                "Self-referential subprocessor error: A vendor cannot be registered as its own subprocessor."
            )

        target_vendor = (
            db.query(Vendor)
            .filter(
                Vendor.id == subprocessor_vendor_id,
                Vendor.organization_id == organization_id,
            )
            .first()
        )
        if not target_vendor:
            raise LookupError(
                "Referenced subprocessor vendor not found in your organization."
            )

        # Graph BFS/DFS from subprocessor_vendor_id to ensure vendor_id is not reachable
        visited = set()
        queue = [subprocessor_vendor_id]
        while queue:
            curr = queue.pop(0)
            if curr == vendor_id:
                raise UnprocessableEntityError(
                    "Circular fourth-party dependency detected in subprocessor lineage graph."
                )
            if curr in visited:
                continue
            visited.add(curr)
            children = (
                db.query(VendorSubprocessor.subprocessor_vendor_id)
                .filter(
                    VendorSubprocessor.organization_id == organization_id,
                    VendorSubprocessor.vendor_id == curr,
                    VendorSubprocessor.subprocessor_vendor_id.isnot(None),
                    VendorSubprocessor.status
                    != VendorSubprocessorStatusEnum.TERMINATED,
                )
                .all()
            )
            for (child_vid,) in children:
                if child_vid is not None:
                    queue.append(child_vid)

    @classmethod
    def create_subprocessor(
        cls,
        db: Session,
        vendor: Vendor,
        payload: VendorSubprocessorCreate,
        creator_id: int,
    ) -> VendorSubprocessor:
        organization_id = vendor.organization_id
        if vendor.vendor_status in (
            VendorStatusEnum.OFFBOARDED,
            VendorStatusEnum.TERMINATED,
        ):
            raise ValueError(
                f"Cannot register subprocessor for vendor in '{vendor.vendor_status.value}' status."
            )

        subprocessor_code = (
            payload.subprocessor_code.strip()
            if payload.subprocessor_code
            else f"SUB-{vendor.id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        )

        existing_code = (
            db.query(VendorSubprocessor)
            .filter(
                VendorSubprocessor.organization_id == organization_id,
                VendorSubprocessor.vendor_id == vendor.id,
                VendorSubprocessor.subprocessor_code == subprocessor_code,
            )
            .first()
        )
        if existing_code:
            raise ConflictError(
                f"Subprocessor code '{subprocessor_code}' already exists for this vendor."
            )

        cls._validate_no_subprocessor_cycle(
            db, organization_id, vendor.id, payload.subprocessor_vendor_id
        )

        norm_name = " ".join(payload.subprocessor_name.lower().strip().split())
        norm_fn = " ".join(payload.service_function.lower().strip().split())

        if payload.subprocessor_vendor_id is not None:
            existing_edge = (
                db.query(VendorSubprocessor)
                .filter(
                    VendorSubprocessor.organization_id == organization_id,
                    VendorSubprocessor.vendor_id == vendor.id,
                    VendorSubprocessor.subprocessor_vendor_id
                    == payload.subprocessor_vendor_id,
                    VendorSubprocessor.status
                    != VendorSubprocessorStatusEnum.TERMINATED,
                )
                .first()
            )
            if existing_edge:
                raise ConflictError(
                    "This fourth-party vendor is already registered as an active subprocessor for this vendor."
                )

        existing_vendor_sps = (
            db.query(VendorSubprocessor)
            .filter(
                VendorSubprocessor.organization_id == organization_id,
                VendorSubprocessor.vendor_id == vendor.id,
                VendorSubprocessor.status != VendorSubprocessorStatusEnum.TERMINATED,
            )
            .all()
        )
        for existing_sp in existing_vendor_sps:
            ex_name = " ".join((existing_sp.subprocessor_name or "").lower().strip().split())
            ex_fn = " ".join((existing_sp.service_function or "").lower().strip().split())
            if ex_name == norm_name and ex_fn == norm_fn:
                raise ConflictError(
                    f"Subprocessor '{payload.subprocessor_name}' with function '{payload.service_function}' is already registered for this vendor."
                )

        if payload.engagement_id is not None:
            eng = (
                db.query(VendorEngagement)
                .filter(
                    VendorEngagement.id == payload.engagement_id,
                    VendorEngagement.organization_id == organization_id,
                    VendorEngagement.vendor_id == vendor.id,
                )
                .first()
            )
            if not eng:
                raise LookupError("Linked engagement not found for this vendor.")

        if payload.linked_risk_id is not None:
            rsk = (
                db.query(Risk)
                .filter(
                    Risk.id == payload.linked_risk_id,
                    Risk.organization_id == organization_id,
                )
                .first()
            )
            if not rsk:
                raise LookupError("Linked risk not found in your organization.")

        sha256_snapshot = None
        if payload.evidence_id is not None:
            ev = cls._verify_evidence_integrity(
                db, payload.evidence_id, organization_id, require_accepted=True
            )
            sha256_snapshot = ev.sha256_hash

        sp = VendorSubprocessor(
            organization_id=organization_id,
            vendor_id=vendor.id,
            engagement_id=payload.engagement_id,
            subprocessor_vendor_id=payload.subprocessor_vendor_id,
            subprocessor_code=subprocessor_code,
            subprocessor_name=payload.subprocessor_name.strip(),
            subprocessor_domain=(
                payload.subprocessor_domain.strip().lower()
                if payload.subprocessor_domain
                else None
            ),
            service_function=payload.service_function.strip(),
            hosting_region=payload.hosting_region.strip(),
            jurisdiction=payload.jurisdiction.strip(),
            criticality=payload.criticality,
            data_classification=payload.data_classification,
            pii_access=payload.pii_access,
            status=VendorSubprocessorStatusEnum.REGISTERED,
            contractual_flowdown_verified=payload.contractual_flowdown_verified,
            evidence_id=payload.evidence_id,
            evidence_sha256_snapshot=sha256_snapshot,
            linked_risk_id=payload.linked_risk_id,
            registered_by_id=creator_id,
        )
        db.add(sp)
        db.flush()
        cls.recalculate_vendor_telemetry(db, vendor)
        return sp

    @classmethod
    def update_subprocessor(
        cls,
        db: Session,
        sp: VendorSubprocessor,
        payload: VendorSubprocessorUpdate,
    ) -> VendorSubprocessor:
        if sp.status == VendorSubprocessorStatusEnum.TERMINATED:
            raise ValueError("Cannot update a TERMINATED subprocessor.")

        update_data = payload.model_dump(exclude_unset=True)
        if "subprocessor_vendor_id" in update_data:
            cls._validate_no_subprocessor_cycle(
                db,
                sp.organization_id,
                sp.vendor_id,
                update_data["subprocessor_vendor_id"],
            )
            if update_data["subprocessor_vendor_id"] is not None:
                existing_edge = (
                    db.query(VendorSubprocessor)
                    .filter(
                        VendorSubprocessor.organization_id == sp.organization_id,
                        VendorSubprocessor.vendor_id == sp.vendor_id,
                        VendorSubprocessor.subprocessor_vendor_id
                        == update_data["subprocessor_vendor_id"],
                        VendorSubprocessor.id != sp.id,
                        VendorSubprocessor.status
                        != VendorSubprocessorStatusEnum.TERMINATED,
                    )
                    .first()
                )
                if existing_edge:
                    raise ConflictError(
                        "This fourth-party vendor is already registered as an active subprocessor for this vendor."
                    )

        if "engagement_id" in update_data and update_data["engagement_id"] is not None:
            eng = (
                db.query(VendorEngagement)
                .filter(
                    VendorEngagement.id == update_data["engagement_id"],
                    VendorEngagement.organization_id == sp.organization_id,
                    VendorEngagement.vendor_id == sp.vendor_id,
                )
                .first()
            )
            if not eng:
                raise LookupError("Linked engagement not found for this vendor.")

        if "linked_risk_id" in update_data and update_data["linked_risk_id"] is not None:
            rsk = (
                db.query(Risk)
                .filter(
                    Risk.id == update_data["linked_risk_id"],
                    Risk.organization_id == sp.organization_id,
                )
                .first()
            )
            if not rsk:
                raise LookupError("Linked risk not found in your organization.")

        if "evidence_id" in update_data:
            if update_data["evidence_id"] is not None:
                ev = cls._verify_evidence_integrity(
                    db,
                    update_data["evidence_id"],
                    sp.organization_id,
                    require_accepted=True,
                )
                sp.evidence_sha256_snapshot = ev.sha256_hash
            else:
                sp.evidence_sha256_snapshot = None

        for k, v in update_data.items():
            if k == "subprocessor_domain" and v:
                v = v.strip().lower()
            setattr(sp, k, v)

        sp.updated_at = datetime.now(timezone.utc)
        db.flush()
        cls.recalculate_vendor_telemetry(db, sp.vendor)
        return sp

    @classmethod
    def submit_subprocessor(
        cls,
        db: Session,
        sp: VendorSubprocessor,
        submitter_id: int,
    ) -> VendorSubprocessor:
        if sp.status not in (
            VendorSubprocessorStatusEnum.REGISTERED,
            VendorSubprocessorStatusEnum.REJECTED,
            VendorSubprocessorStatusEnum.SUSPENDED,
        ):
            raise ValueError(
                f"Only REGISTERED, REJECTED, or SUSPENDED subprocessors can be submitted for review (current: {sp.status.value})."
            )
        sp.status = VendorSubprocessorStatusEnum.UNDER_REVIEW
        sp.submitted_by_id = submitter_id
        sp.submitted_at = datetime.now(timezone.utc)
        sp.updated_at = datetime.now(timezone.utc)
        db.flush()
        return sp

    @classmethod
    def approve_subprocessor(
        cls,
        db: Session,
        sp: VendorSubprocessor,
        approver_id: int,
        payload: VendorSubprocessorReview,
    ) -> VendorSubprocessor:
        if sp.status == VendorSubprocessorStatusEnum.APPROVED:
            raise ConflictError("Subprocessor is already in APPROVED status.")
        if sp.status not in (
            VendorSubprocessorStatusEnum.UNDER_REVIEW,
            VendorSubprocessorStatusEnum.PENDING_REVIEW,
            VendorSubprocessorStatusEnum.REGISTERED,
        ):
            raise ValueError(
                f"Only UNDER_REVIEW or PENDING_REVIEW subprocessors can be approved (current: {sp.status.value})."
            )
        if sp.registered_by_id == approver_id or sp.submitted_by_id == approver_id:
            raise PermissionError(
                "Four-eyes separation of duties violation: Subprocessor registrant or submitter cannot approve their own subprocessor."
            )

        requires_strict_flowdown = (
            sp.criticality
            in (BusinessCriticalityEnum.CRITICAL, BusinessCriticalityEnum.HIGH)
            or sp.data_classification
            in (
                DataClassificationEnum.RESTRICTED,
                DataClassificationEnum.CONFIDENTIAL,
            )
            or sp.pii_access
            in (
                PiiFinancialAccessEnum.DIRECT_PCI_PII_PHI,
                PiiFinancialAccessEnum.METADATA_ONLY,
            )
        )
        if requires_strict_flowdown:
            if sp.evidence_id is None:
                raise UnprocessableEntityError(
                    "Subprocessors with CRITICAL/HIGH criticality, CONFIDENTIAL/RESTRICTED data, or PII access require an ACCEPTED EvidenceItem (evidence_id) before approval."
                )
            if not sp.contractual_flowdown_verified:
                raise UnprocessableEntityError(
                    "Subprocessors with CRITICAL/HIGH criticality, CONFIDENTIAL/RESTRICTED data, or PII access must have contractual_flowdown_verified=True and valid evidence before approval."
                )

        if sp.evidence_id is not None:
            ev = cls._verify_snapshot_digest(
                db,
                sp.evidence_id,
                sp.evidence_sha256_snapshot,
                sp.organization_id,
            )
            sp.evidence_sha256_snapshot = ev.sha256_hash

        now = datetime.now(timezone.utc)
        sp.status = VendorSubprocessorStatusEnum.APPROVED
        sp.approved_by_id = approver_id
        sp.approved_at = now
        sp.reviewed_by_id = approver_id
        sp.reviewed_at = now
        sp.review_notes = payload.review_notes
        sp.updated_at = now
        db.flush()
        cls.recalculate_vendor_telemetry(db, sp.vendor)
        return sp

    @classmethod
    def reject_subprocessor(
        cls,
        db: Session,
        sp: VendorSubprocessor,
        reviewer_id: int,
        payload: VendorSubprocessorReview,
    ) -> VendorSubprocessor:
        if sp.status not in (
            VendorSubprocessorStatusEnum.UNDER_REVIEW,
            VendorSubprocessorStatusEnum.PENDING_REVIEW,
            VendorSubprocessorStatusEnum.REGISTERED,
        ):
            raise ValueError(
                f"Only UNDER_REVIEW or PENDING_REVIEW subprocessors can be rejected (current: {sp.status.value})."
            )
        if sp.registered_by_id == reviewer_id or sp.submitted_by_id == reviewer_id:
            raise PermissionError(
                "Four-eyes separation of duties violation: Subprocessor registrant or submitter cannot reject their own subprocessor."
            )
        reason = payload.rejection_reason or payload.reason or payload.review_notes
        if not reason or len(reason.strip()) < 5:
            raise ValueError("Rejection reason (minimum 5 characters) is required.")

        now = datetime.now(timezone.utc)
        sp.status = VendorSubprocessorStatusEnum.REJECTED
        sp.reviewed_by_id = reviewer_id
        sp.reviewed_at = now
        sp.rejection_reason = reason.strip()
        sp.review_notes = payload.review_notes
        sp.updated_at = now
        db.flush()
        cls.recalculate_vendor_telemetry(db, sp.vendor)
        return sp

    @classmethod
    def suspend_subprocessor(
        cls,
        db: Session,
        sp: VendorSubprocessor,
        actor_id: int,
        payload: VendorSubprocessorReview,
    ) -> VendorSubprocessor:
        if sp.status not in (
            VendorSubprocessorStatusEnum.APPROVED,
            VendorSubprocessorStatusEnum.UNDER_REVIEW,
        ):
            raise ValueError(
                f"Only APPROVED or UNDER_REVIEW subprocessors can be suspended (current: {sp.status.value})."
            )
        reason = payload.suspension_reason or payload.reason or payload.review_notes
        if not reason or len(reason.strip()) < 5:
            raise ValueError("Suspension reason (minimum 5 characters) is required.")

        now = datetime.now(timezone.utc)
        sp.status = VendorSubprocessorStatusEnum.SUSPENDED
        sp.reviewed_by_id = actor_id
        sp.reviewed_at = now
        sp.suspension_reason = reason.strip()
        sp.updated_at = now
        db.flush()
        cls.recalculate_vendor_telemetry(db, sp.vendor)
        return sp

    @classmethod
    def terminate_subprocessor(
        cls,
        db: Session,
        sp: VendorSubprocessor,
        actor_id: int,
        payload: VendorSubprocessorReview,
    ) -> VendorSubprocessor:
        if sp.status == VendorSubprocessorStatusEnum.TERMINATED:
            raise ValueError("Subprocessor is already TERMINATED.")
        reason = (
            payload.termination_reason
            or payload.reason
            or payload.review_notes
            or "Terminated by TPRM governance action."
        )

        now = datetime.now(timezone.utc)
        sp.status = VendorSubprocessorStatusEnum.TERMINATED
        sp.reviewed_by_id = actor_id
        sp.reviewed_at = now
        sp.termination_reason = reason.strip()
        sp.updated_at = now
        db.flush()
        cls.recalculate_vendor_telemetry(db, sp.vendor)
        return sp

    @classmethod
    def compute_concentration_risk(
        cls, db: Session, organization_id: int
    ) -> ConcentrationRiskReportResponse:
        """Computes tenant-wide fourth-party concentration risk and Single Points of Failure (SPOFs)."""
        active_subprocessors = (
            db.query(VendorSubprocessor)
            .filter(
                VendorSubprocessor.organization_id == organization_id,
                VendorSubprocessor.status != VendorSubprocessorStatusEnum.TERMINATED,
            )
            .all()
        )
        vendors = (
            db.query(Vendor)
            .filter(Vendor.organization_id == organization_id)
            .all()
        )
        vendor_map = {v.id: v for v in vendors}

        groups: Dict[str, List[VendorSubprocessor]] = {}
        for sp in active_subprocessors:
            norm_sp_name = " ".join((sp.subprocessor_name or "").lower().strip().split())
            if sp.subprocessor_vendor_id and sp.subprocessor_vendor_id in vendor_map:
                key = f"vid:{sp.subprocessor_vendor_id}"
            else:
                key = f"name:{norm_sp_name}"
            groups.setdefault(key, []).append(sp)

        crit_rank = {
            BusinessCriticalityEnum.LOW: 1,
            BusinessCriticalityEnum.MEDIUM: 2,
            BusinessCriticalityEnum.HIGH: 3,
            BusinessCriticalityEnum.CRITICAL: 4,
        }
        rank_to_crit = {v: k for k, v in crit_rank.items()}

        nodes: List[ConcentrationRiskNodeRead] = []
        spof_candidates: List[ConcentrationRiskNodeRead] = []
        spof_count = 0
        shared_count = 0

        for key, sp_list in groups.items():
            dep_vendor_ids = sorted({sp.vendor_id for sp in sp_list})
            if len(dep_vendor_ids) >= 2:
                shared_count += 1

            dep_vendor_codes = [
                vendor_map[vid].vendor_code
                for vid in dep_vendor_ids
                if vid in vendor_map
            ]
            tier12_count = 0
            for vid in dep_vendor_ids:
                v = vendor_map.get(vid)
                if v and v.effective_tier in (
                    VendorTierEnum.TIER_1_CRITICAL,
                    VendorTierEnum.TIER_2_SIGNIFICANT,
                ):
                    tier12_count += 1

            max_rank = max(crit_rank.get(sp.criticality, 2) for sp in sp_list)
            max_crit = rank_to_crit[max_rank]

            max_data_score = max(
                cls.DATA_CLASSIFICATION_SCORES.get(sp.data_classification, 50.0)
                for sp in sp_list
            )
            max_crit_score = cls.CRITICALITY_SCORES.get(max_crit, 50.0)

            base_score = 0.60 * max_crit_score + 0.40 * max_data_score
            concentration_multiplier = min(
                len(dep_vendor_ids) * 12.0 + tier12_count * 10.0, 40.0
            )
            score = round(min(base_score * 0.60 + concentration_multiplier, 100.0), 1)

            is_spof = (
                (tier12_count >= 2)
                or (len(dep_vendor_ids) >= 3)
                or (
                    len(dep_vendor_ids) >= 2
                    and (
                        tier12_count >= 1
                        or max_crit
                        in (BusinessCriticalityEnum.CRITICAL, BusinessCriticalityEnum.HIGH)
                    )
                )
            )

            if is_spof:
                spof_count += 1

            first = sp_list[0]
            canonical_name = first.subprocessor_name
            if (
                first.subprocessor_vendor_id
                and first.subprocessor_vendor_id in vendor_map
            ):
                canonical_name = vendor_map[first.subprocessor_vendor_id].legal_name
            norm_fourth_name = " ".join((canonical_name or "").lower().strip().split())

            node = ConcentrationRiskNodeRead(
                canonical_name=canonical_name,
                normalized_fourth_party_name=norm_fourth_name,
                subprocessor_domain=first.subprocessor_domain,
                subprocessor_vendor_id=first.subprocessor_vendor_id,
                dependent_vendor_ids=dep_vendor_ids,
                dependent_vendor_codes=dep_vendor_codes,
                dependent_vendors_count=len(dep_vendor_ids),
                tier1_or_tier2_dependents_count=tier12_count,
                max_criticality=max_crit,
                hosting_regions=sorted({sp.hosting_region for sp in sp_list}),
                jurisdictions=sorted({sp.jurisdiction for sp in sp_list}),
                concentration_risk_score=score,
                is_single_point_of_failure=is_spof,
            )
            nodes.append(node)
            if is_spof:
                spof_candidates.append(node)

        nodes.sort(
            key=lambda n: (n.is_single_point_of_failure, n.concentration_risk_score),
            reverse=True,
        )
        spof_candidates.sort(
            key=lambda n: n.concentration_risk_score,
            reverse=True,
        )

        return ConcentrationRiskReportResponse(
            organization_id=organization_id,
            total_subprocessors=len(active_subprocessors),
            unique_fourth_parties=len(nodes),
            shared_fourth_party_count=shared_count,
            spof_count=spof_count,
            nodes=nodes,
            single_point_of_failure_candidates=spof_candidates,
        )

    # ─── 11. BATCH 6: SLA OBLIGATIONS & BREACH ESCALATION ───────────────────

    @classmethod
    def create_sla_obligation(
        cls,
        db: Session,
        vendor: Vendor,
        payload: VendorSlaObligationCreate,
        creator_id: int,
    ) -> VendorSlaObligation:
        organization_id = vendor.organization_id
        if vendor.vendor_status in (
            VendorStatusEnum.OFFBOARDED,
            VendorStatusEnum.TERMINATED,
        ):
            raise ValueError(
                f"Cannot create SLA obligation for vendor in '{vendor.vendor_status.value}' status."
            )

        existing = (
            db.query(VendorSlaObligation)
            .filter(
                VendorSlaObligation.organization_id == organization_id,
                VendorSlaObligation.vendor_id == vendor.id,
                VendorSlaObligation.obligation_code == payload.obligation_code.strip(),
            )
            .first()
        )
        if existing:
            raise ConflictError(
                f"SLA obligation code '{payload.obligation_code}' already exists for this vendor."
            )

        if payload.metric_type in (
            VendorSlaMetricTypeEnum.AVAILABILITY_PCT,
            VendorSlaMetricTypeEnum.AVAILABILITY_UPTIME,
        ) and payload.target_value > 100.0:
            raise UnprocessableEntityError(
                f"{payload.metric_type.value} target_value cannot exceed 100.0."
            )

        if payload.contract_id is not None:
            contract = (
                db.query(VendorContract)
                .filter(
                    VendorContract.id == payload.contract_id,
                    VendorContract.organization_id == organization_id,
                    VendorContract.vendor_id == vendor.id,
                )
                .first()
            )
            if not contract:
                raise LookupError("Linked contract not found for this vendor.")

        if payload.engagement_id is not None:
            eng = (
                db.query(VendorEngagement)
                .filter(
                    VendorEngagement.id == payload.engagement_id,
                    VendorEngagement.organization_id == organization_id,
                    VendorEngagement.vendor_id == vendor.id,
                )
                .first()
            )
            if not eng:
                raise LookupError("Linked engagement not found for this vendor.")

        if payload.linked_organization_control_id is not None:
            ctrl = (
                db.query(OrganizationControl)
                .filter(
                    OrganizationControl.id == payload.linked_organization_control_id,
                    OrganizationControl.organization_id == organization_id,
                )
                .first()
            )
            if not ctrl:
                raise LookupError(
                    "Linked organization control not found in your organization."
                )

        obligation = VendorSlaObligation(
            organization_id=organization_id,
            vendor_id=vendor.id,
            contract_id=payload.contract_id,
            engagement_id=payload.engagement_id,
            linked_organization_control_id=payload.linked_organization_control_id,
            obligation_code=payload.obligation_code.strip(),
            title=payload.title.strip(),
            description=payload.description,
            metric_type=payload.metric_type,
            comparison_operator=payload.comparison_operator,
            target_value=payload.target_value,
            tolerance_value=payload.tolerance_value,
            unit=payload.unit.strip(),
            measurement_window=payload.measurement_window.strip(),
            measurement_frequency_days=payload.measurement_frequency_days,
            breach_severity_on_miss=payload.breach_severity_on_miss,
            contract_clause_ref=payload.contract_clause_ref,
            penalty_clause_summary=payload.penalty_clause_summary,
            effective_from=payload.effective_from,
            expiry_date=payload.expiry_date,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            created_by_id=creator_id,
        )
        db.add(obligation)
        db.flush()
        return obligation

    @classmethod
    def update_sla_obligation(
        cls,
        db: Session,
        obligation: VendorSlaObligation,
        payload: VendorSlaObligationUpdate,
    ) -> VendorSlaObligation:
        update_data = payload.model_dump(exclude_unset=True)
        new_metric = update_data.get("metric_type", obligation.metric_type)
        new_target = update_data.get("target_value", obligation.target_value)
        if new_metric in (
            VendorSlaMetricTypeEnum.AVAILABILITY_PCT,
            VendorSlaMetricTypeEnum.AVAILABILITY_UPTIME,
        ) and new_target > 100.0:
            raise UnprocessableEntityError(
                f"{new_metric.value} target_value cannot exceed 100.0."
            )

        if "contract_id" in update_data and update_data["contract_id"] is not None:
            contract = (
                db.query(VendorContract)
                .filter(
                    VendorContract.id == update_data["contract_id"],
                    VendorContract.organization_id == obligation.organization_id,
                    VendorContract.vendor_id == obligation.vendor_id,
                )
                .first()
            )
            if not contract:
                raise LookupError("Linked contract not found for this vendor.")

        if "engagement_id" in update_data and update_data["engagement_id"] is not None:
            eng = (
                db.query(VendorEngagement)
                .filter(
                    VendorEngagement.id == update_data["engagement_id"],
                    VendorEngagement.organization_id == obligation.organization_id,
                    VendorEngagement.vendor_id == obligation.vendor_id,
                )
                .first()
            )
            if not eng:
                raise LookupError("Linked engagement not found for this vendor.")

        if (
            "linked_organization_control_id" in update_data
            and update_data["linked_organization_control_id"] is not None
        ):
            ctrl = (
                db.query(OrganizationControl)
                .filter(
                    OrganizationControl.id
                    == update_data["linked_organization_control_id"],
                    OrganizationControl.organization_id == obligation.organization_id,
                )
                .first()
            )
            if not ctrl:
                raise LookupError(
                    "Linked organization control not found in your organization."
                )

        for k, v in update_data.items():
            setattr(obligation, k, v)

        obligation.updated_at = datetime.now(timezone.utc)
        db.flush()
        return obligation

    @classmethod
    def _is_threshold_violated(
        cls,
        operator: VendorSlaComparisonOperatorEnum,
        target: float,
        observed: float,
    ) -> bool:
        if operator == VendorSlaComparisonOperatorEnum.GTE:
            return observed < target
        elif operator == VendorSlaComparisonOperatorEnum.LTE:
            return observed > target
        elif operator == VendorSlaComparisonOperatorEnum.EQ:
            return abs(observed - target) > 1e-9
        return False

    @classmethod
    def _compute_breach_severity(
        cls,
        obligation: VendorSlaObligation,
        observed_value: float,
        variance_magnitude: float,
    ) -> VendorSlaBreachSeverityEnum:
        if obligation.metric_type in (
            VendorSlaMetricTypeEnum.AVAILABILITY_PCT,
            VendorSlaMetricTypeEnum.AVAILABILITY_UPTIME,
        ):
            if observed_value < obligation.target_value - 2.0:
                return VendorSlaBreachSeverityEnum.CRITICAL
        return obligation.breach_severity_on_miss

    @classmethod
    def record_sla_breach(
        cls,
        db: Session,
        vendor: Vendor,
        payload: VendorSlaBreachCreate,
        reporter_id: int,
    ) -> VendorSlaBreach:
        organization_id = vendor.organization_id
        obligation = (
            db.query(VendorSlaObligation)
            .filter(
                VendorSlaObligation.id == payload.obligation_id,
                VendorSlaObligation.organization_id == organization_id,
                VendorSlaObligation.vendor_id == vendor.id,
            )
            .first()
        )
        if not obligation:
            raise LookupError("SLA obligation not found for this vendor.")
        if obligation.status != VendorSlaObligationStatusEnum.ACTIVE:
            raise ValueError(
                "Cannot record a breach against a non-ACTIVE SLA obligation."
            )

        now_utc = datetime.now(timezone.utc)
        max_allowed_future = now_utc + timedelta(minutes=5)

        p_start = payload.period_start
        p_end = payload.period_end
        occ_at = payload.occurred_at or p_end or now_utc

        if p_start and p_start.tzinfo is None:
            p_start = p_start.replace(tzinfo=timezone.utc)
        if p_end and p_end.tzinfo is None:
            p_end = p_end.replace(tzinfo=timezone.utc)
        if occ_at and occ_at.tzinfo is None:
            occ_at = occ_at.replace(tzinfo=timezone.utc)

        if p_start and p_end and p_end < p_start:
            raise UnprocessableEntityError(
                "SLA breach period_end cannot precede period_start."
            )
        if p_end and p_end > max_allowed_future:
            raise UnprocessableEntityError(
                "SLA breach period_end cannot be in the future beyond 5-minute clock-skew tolerance."
            )
        if occ_at > max_allowed_future:
            raise UnprocessableEntityError(
                "SLA breach occurred_at cannot be in the future beyond 5-minute clock-skew tolerance."
            )

        if (
            obligation.metric_type != VendorSlaMetricTypeEnum.CUSTOM_METRIC
            and payload.observed_value < 0.0
        ):
            raise UnprocessableEntityError(
                "Observed value cannot be negative for non-custom SLA metrics."
            )
        if obligation.metric_type in (
            VendorSlaMetricTypeEnum.AVAILABILITY_PCT,
            VendorSlaMetricTypeEnum.AVAILABILITY_UPTIME,
        ) and payload.observed_value > 100.0:
            raise UnprocessableEntityError(
                f"{obligation.metric_type.value} observed_value cannot exceed 100.0."
            )

        threshold = (
            obligation.tolerance_value
            if obligation.tolerance_value is not None
            else obligation.target_value
        )
        if not cls._is_threshold_violated(
            obligation.comparison_operator,
            threshold,
            payload.observed_value,
        ):
            raise UnprocessableEntityError(
                f"Observed value ({payload.observed_value}) does not violate SLA threshold ({obligation.comparison_operator.value} {threshold}) and does not constitute a breach."
            )

        breach_code = (
            payload.breach_code.strip()
            if payload.breach_code
            else f"SLAB-{vendor.id}-{int(now_utc.timestamp() * 1000)}"
        )
        existing = (
            db.query(VendorSlaBreach)
            .filter(
                VendorSlaBreach.organization_id == organization_id,
                VendorSlaBreach.vendor_id == vendor.id,
                VendorSlaBreach.breach_code == breach_code,
            )
            .first()
        )
        if existing:
            raise ConflictError(
                f"SLA breach code '{breach_code}' already exists for this vendor."
            )

        sha256_snapshot = None
        if payload.evidence_id is not None:
            ev = cls._verify_evidence_integrity(
                db, payload.evidence_id, organization_id, require_accepted=True
            )
            sha256_snapshot = ev.sha256_hash

        variance_magnitude = round(
            abs(payload.observed_value - threshold), 4
        )
        severity = cls._compute_breach_severity(
            obligation, payload.observed_value, variance_magnitude
        )

        breach = VendorSlaBreach(
            organization_id=organization_id,
            vendor_id=vendor.id,
            obligation_id=obligation.id,
            breach_code=breach_code,
            period_start=p_start,
            period_end=p_end,
            occurred_at=occ_at,
            reported_at=now_utc,
            target_value_snapshot=obligation.target_value,
            tolerance_value_snapshot=obligation.tolerance_value,
            observed_value=payload.observed_value,
            variance_magnitude=variance_magnitude,
            service_credit_amount=payload.service_credit_amount,
            comparison_operator_snapshot=obligation.comparison_operator,
            severity=severity,
            status=VendorSlaBreachStatusEnum.OPEN,
            root_cause_summary=payload.root_cause_summary,
            evidence_id=payload.evidence_id,
            evidence_sha256_snapshot=sha256_snapshot,
            reported_by_id=reporter_id,
        )
        db.add(breach)
        db.flush()

        if payload.auto_escalate_to_finding:
            cls.escalate_sla_breach(
                db=db,
                breach=breach,
                payload=VendorSlaBreachEscalateRequest(
                    create_finding=True,
                    create_remediation_plan=False,
                    create_risk=False,
                    finding_owner_id=payload.finding_owner_id,
                ),
                actor_id=reporter_id,
            )
        else:
            cls.recalculate_vendor_telemetry(db, vendor)

        return breach

    @classmethod
    def escalate_sla_breach(
        cls,
        db: Session,
        breach: VendorSlaBreach,
        payload: VendorSlaBreachEscalateRequest,
        actor_id: int,
    ) -> VendorSlaBreach:
        organization_id = breach.organization_id
        vendor = breach.vendor

        if breach.linked_finding_id is not None or breach.status in (
            VendorSlaBreachStatusEnum.ESCALATED,
            VendorSlaBreachStatusEnum.ESCALATED_TO_FINDING,
        ):
            raise ConflictError("SLA breach has already been escalated to a Finding.")

        if breach.status in (
            VendorSlaBreachStatusEnum.RESOLVED,
            VendorSlaBreachStatusEnum.VERIFIED_CLOSED,
            VendorSlaBreachStatusEnum.WAIVED,
            VendorSlaBreachStatusEnum.WAIVED_BY_EXCEPTION,
        ):
            raise ValueError(
                f"Cannot escalate an SLA breach in '{breach.status.value}' status."
            )

        owner_id = payload.finding_owner_id or vendor.business_owner_id or actor_id
        owner = (
            db.query(User)
            .filter(
                User.id == owner_id,
                User.organization_id == organization_id,
                User.is_active.is_(True),
            )
            .first()
        )
        if not owner:
            raise LookupError(
                "Designated finding owner not found or inactive in your organization."
            )

        sev_map = {
            VendorSlaBreachSeverityEnum.CRITICAL: FindingSeverityEnum.CRITICAL,
            VendorSlaBreachSeverityEnum.HIGH: FindingSeverityEnum.HIGH,
            VendorSlaBreachSeverityEnum.MAJOR: FindingSeverityEnum.HIGH,
            VendorSlaBreachSeverityEnum.MEDIUM: FindingSeverityEnum.MEDIUM,
            VendorSlaBreachSeverityEnum.MINOR: FindingSeverityEnum.LOW,
            VendorSlaBreachSeverityEnum.LOW: FindingSeverityEnum.LOW,
        }
        f_sev = sev_map.get(breach.severity, FindingSeverityEnum.HIGH)
        impact_map = {
            FindingSeverityEnum.CRITICAL: 5,
            FindingSeverityEnum.HIGH: 4,
            FindingSeverityEnum.MEDIUM: 3,
            FindingSeverityEnum.LOW: 2,
        }
        impact = impact_map[f_sev]
        likelihood = (
            4 if f_sev in (FindingSeverityEnum.CRITICAL, FindingSeverityEnum.HIGH) else 3
        )
        score = impact * likelihood
        band = "CRITICAL" if score >= 20 else ("HIGH" if score >= 12 else "MODERATE")

        if payload.create_finding or payload.create_remediation_plan:
            ctrl = cls._resolve_organization_control(
                db=db,
                organization_id=organization_id,
                explicit_control_id=payload.organization_control_id,
                fallback_control_id=breach.obligation.linked_organization_control_id,
            )
            due_dt = (
                payload.remediation_due_date.date()
                if payload.remediation_due_date
                else (datetime.now(timezone.utc) + timedelta(days=30)).date()
            )
            finding = Finding(
                organization_id=organization_id,
                organization_control_id=ctrl.id,
                title=payload.finding_title
                or f"[TPRM SLA Breach] {vendor.legal_name}: {breach.breach_code}",
                description=payload.finding_description
                or (
                    f"Contractual SLA breach '{breach.breach_code}' on obligation ID {breach.obligation_id}. "
                    f"Target: {breach.comparison_operator_snapshot.value} {breach.target_value_snapshot}, "
                    f"Observed: {breach.observed_value}. Root cause: {breach.root_cause_summary or 'N/A'}"
                ),
                finding_type=FindingTypeEnum.PROCESS_GAP,
                severity=f_sev,
                impact=impact,
                likelihood=likelihood,
                risk_score=score,
                risk_band=band,
                recommendation="Enforce contractual SLA remediation plan and obtain vendor root-cause corrective attestation.",
                root_cause=breach.root_cause_summary,
                owner_id=owner.id,
                due_date=due_dt,
                status=FindingStatusEnum.OPEN,
                created_by_id=actor_id,
            )
            db.add(finding)
            db.flush()
            breach.linked_finding_id = finding.id

            if payload.create_remediation_plan:
                rem_sev_map = {
                    FindingSeverityEnum.CRITICAL: RemediationSeverityEnum.CRITICAL,
                    FindingSeverityEnum.HIGH: RemediationSeverityEnum.HIGH,
                    FindingSeverityEnum.MEDIUM: RemediationSeverityEnum.MEDIUM,
                    FindingSeverityEnum.LOW: RemediationSeverityEnum.LOW,
                }
                plan_code = f"CAPA-SLA-{breach.id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
                plan = RemediationPlan(
                    organization_id=organization_id,
                    plan_code=plan_code,
                    title=f"SLA Breach Remediation: {vendor.legal_name} ({breach.breach_code})",
                    problem_statement=finding.description,
                    root_cause_classification=RemediationRootCauseClassificationEnum.VENDOR_DEFAULT,
                    source_type=RemediationSourceTypeEnum.FINDING,
                    finding_id=finding.id,
                    severity=rem_sev_map[f_sev],
                    status=RemediationStatusEnum.DRAFT,
                    plan_owner_id=owner.id,
                    target_completion_at=payload.remediation_due_date
                    or (datetime.now(timezone.utc) + timedelta(days=30)),
                )
                db.add(plan)
                db.flush()
                breach.linked_remediation_plan_id = plan.id

        if payload.create_risk:
            r_impact = payload.inherent_impact or impact
            r_likelihood = payload.inherent_likelihood or likelihood
            r_score = r_impact * r_likelihood
            r_band = (
                "CRITICAL"
                if r_score >= 20
                else ("HIGH" if r_score >= 12 else ("MODERATE" if r_score >= 6 else "LOW"))
            )
            risk = Risk(
                organization_id=organization_id,
                title=f"Third-Party SLA Performance Risk: {vendor.legal_name} ({breach.breach_code})",
                description=payload.risk_statement
                or f"Risk arising from contractual SLA breach {breach.breach_code} (observed {breach.observed_value} vs target {breach.target_value_snapshot}).",
                risk_category=RiskCategoryEnum.THIRD_PARTY,
                risk_source=RiskSourceEnum.VENDOR_ASSESSMENT,
                owner_id=owner.id,
                inherent_impact=r_impact,
                inherent_likelihood=r_likelihood,
                inherent_score=r_score,
                inherent_band=r_band,
                status=RiskStatusEnum.IDENTIFIED,
                treatment_strategy=RiskTreatmentStrategyEnum.MITIGATE,
                created_by_id=actor_id,
            )
            db.add(risk)
            db.flush()
            breach.linked_risk_id = risk.id

        breach.status = VendorSlaBreachStatusEnum.ESCALATED_TO_FINDING
        breach.updated_at = datetime.now(timezone.utc)
        db.flush()
        cls.recalculate_vendor_telemetry(db, vendor)
        return breach

    @classmethod
    def waive_sla_breach(
        cls,
        db: Session,
        breach: VendorSlaBreach,
        payload: VendorSlaBreachWaiveRequest,
        actor_id: int,
    ) -> VendorSlaBreach:
        organization_id = breach.organization_id
        if breach.reported_by_id == actor_id:
            raise PermissionError(
                "Four-eyes separation of duties violation: Breach recorder cannot waive their own SLA breach."
            )
        if breach.status in (
            VendorSlaBreachStatusEnum.RESOLVED,
            VendorSlaBreachStatusEnum.VERIFIED_CLOSED,
            VendorSlaBreachStatusEnum.WAIVED,
            VendorSlaBreachStatusEnum.WAIVED_BY_EXCEPTION,
        ):
            raise ValueError(
                f"Cannot waive SLA breach in '{breach.status.value}' status."
            )

        if payload.linked_exception_id is None:
            raise UnprocessableEntityError(
                "Waiving an SLA breach requires a valid linked_exception_id."
            )

        exc = (
            db.query(SecurityException)
            .filter(
                SecurityException.id == payload.linked_exception_id,
                SecurityException.organization_id == organization_id,
            )
            .first()
        )
        if not exc:
            raise UnprocessableEntityError(
                "Linked security exception not found in your organization."
            )
        if exc.linked_vendor_id != breach.vendor_id:
            raise UnprocessableEntityError(
                "Security exception must be explicitly linked to this vendor."
            )
        if exc.status not in (
            ExceptionStatusEnum.APPROVED,
            ExceptionStatusEnum.ACTIVE,
        ):
            raise UnprocessableEntityError(
                f"Security exception must be APPROVED or ACTIVE to waive an SLA breach (current: {exc.status.value})."
            )
        now = datetime.now(timezone.utc)
        if exc.expiry_date is not None and exc.expiry_date < now.date():
            raise UnprocessableEntityError(
                "Cannot waive SLA breach with an expired security exception."
            )

        breach.linked_exception_id = exc.id
        breach.status = VendorSlaBreachStatusEnum.WAIVED_BY_EXCEPTION
        breach.waived_by_id = actor_id
        breach.waived_at = now
        breach.waiver_reason = payload.waiver_reason.strip()
        breach.updated_at = now
        db.flush()
        cls.recalculate_vendor_telemetry(db, breach.vendor)
        return breach

    @classmethod
    def resolve_sla_breach(
        cls,
        db: Session,
        breach: VendorSlaBreach,
        payload: VendorSlaBreachResolveRequest,
        resolver_id: int,
    ) -> VendorSlaBreach:
        organization_id = breach.organization_id
        if breach.status in (
            VendorSlaBreachStatusEnum.RESOLVED,
            VendorSlaBreachStatusEnum.VERIFIED_CLOSED,
            VendorSlaBreachStatusEnum.WAIVED,
            VendorSlaBreachStatusEnum.WAIVED_BY_EXCEPTION,
        ):
            raise ValueError(f"SLA breach is already in '{breach.status.value}' status.")

        if payload.linked_exception_id is not None:
            return cls.waive_sla_breach(
                db=db,
                breach=breach,
                payload=VendorSlaBreachWaiveRequest(
                    linked_exception_id=payload.linked_exception_id,
                    waiver_reason=payload.resolution_notes,
                ),
                actor_id=resolver_id,
            )

        now = datetime.now(timezone.utc)
        if breach.linked_finding_id is not None:
            finding = (
                db.query(Finding)
                .filter(
                    Finding.id == breach.linked_finding_id,
                    Finding.organization_id == organization_id,
                )
                .first()
            )
            if finding and finding.status not in (
                FindingStatusEnum.RESOLVED,
                FindingStatusEnum.CLOSED,
                FindingStatusEnum.ACCEPTED_RISK,
            ):
                raise ValueError(
                    f"Cannot resolve SLA breach while linked Finding #{finding.id} is still in '{finding.status.value}' status."
                )

        if breach.severity in (
            VendorSlaBreachSeverityEnum.CRITICAL,
            VendorSlaBreachSeverityEnum.HIGH,
            VendorSlaBreachSeverityEnum.MAJOR,
        ):
            ev_id = payload.evidence_id or breach.evidence_id
            if not ev_id:
                raise ValueError(
                    f"Resolving a {breach.severity.value} SLA breach requires an ACCEPTED EvidenceItem."
                )
            ev = cls._verify_evidence_integrity(
                db, ev_id, organization_id, require_accepted=True
            )
            breach.evidence_id = ev.id
            breach.evidence_sha256_snapshot = ev.sha256_hash
        elif payload.evidence_id is not None:
            ev = cls._verify_evidence_integrity(
                db, payload.evidence_id, organization_id, require_accepted=True
            )
            breach.evidence_id = ev.id
            breach.evidence_sha256_snapshot = ev.sha256_hash

        breach.status = VendorSlaBreachStatusEnum.RESOLVED
        breach.resolution_notes = payload.resolution_notes.strip()
        breach.resolved_by_id = resolver_id
        breach.resolved_at = now
        breach.updated_at = now
        db.flush()
        cls.recalculate_vendor_telemetry(db, breach.vendor)
        return breach

    @classmethod
    def reopen_sla_breach(
        cls,
        db: Session,
        breach: VendorSlaBreach,
        payload: VendorSlaBreachReopenRequest,
        actor_id: int,
    ) -> VendorSlaBreach:
        if breach.status not in (
            VendorSlaBreachStatusEnum.WAIVED,
            VendorSlaBreachStatusEnum.WAIVED_BY_EXCEPTION,
            VendorSlaBreachStatusEnum.RESOLVED,
            VendorSlaBreachStatusEnum.VERIFIED_CLOSED,
        ):
            raise ValueError(
                f"Cannot reopen SLA breach in '{breach.status.value}' status."
            )
        now = datetime.now(timezone.utc)
        breach.status = (
            VendorSlaBreachStatusEnum.ESCALATED_TO_FINDING
            if breach.linked_finding_id
            else VendorSlaBreachStatusEnum.OPEN
        )
        breach.updated_at = now
        db.flush()
        cls.recalculate_vendor_telemetry(db, breach.vendor)
        return breach

    @classmethod
    def verify_close_sla_breach(
        cls,
        db: Session,
        breach: VendorSlaBreach,
        payload: VendorSlaBreachVerifyCloseRequest,
        actor_id: int,
    ) -> VendorSlaBreach:
        organization_id = breach.organization_id
        if breach.reported_by_id == actor_id or breach.resolved_by_id == actor_id:
            raise PermissionError(
                "Four-eyes separation of duties violation: Breach recorder or resolver cannot verify-close their own SLA breach."
            )

        if breach.linked_finding_id is not None:
            finding = (
                db.query(Finding)
                .filter(
                    Finding.id == breach.linked_finding_id,
                    Finding.organization_id == organization_id,
                )
                .first()
            )
            if finding and finding.status not in (
                FindingStatusEnum.RESOLVED,
                FindingStatusEnum.CLOSED,
                FindingStatusEnum.ACCEPTED_RISK,
            ):
                raise ValueError(
                    f"Cannot verify-close SLA breach while linked Finding #{finding.id} is still in '{finding.status.value}' status."
                )

        ev_id = payload.evidence_id or breach.evidence_id
        if ev_id is not None:
            ev = cls._verify_snapshot_digest(
                db,
                ev_id,
                breach.evidence_sha256_snapshot if ev_id == breach.evidence_id else None,
                organization_id,
            )
            breach.evidence_id = ev.id
            breach.evidence_sha256_snapshot = ev.sha256_hash

        now = datetime.now(timezone.utc)
        breach.status = VendorSlaBreachStatusEnum.VERIFIED_CLOSED
        breach.closed_by_id = actor_id
        breach.closed_at = now
        breach.closure_notes = payload.closure_notes
        breach.updated_at = now
        db.flush()
        cls.recalculate_vendor_telemetry(db, breach.vendor)
        return breach

    # ─── 12. BATCH 6: CLOSED-LOOP ASSESSMENT ITEM ESCALATION ────────────────

    @classmethod
    def escalate_assessment_item(
        cls,
        db: Session,
        assessment: VendorAssessment,
        item: VendorAssessmentItem,
        payload: VendorAssessmentItemEscalateRequest,
        actor_id: int,
    ) -> VendorAssessmentItem:
        organization_id = assessment.organization_id
        vendor = assessment.vendor

        if assessment.status in (
            VendorAssessmentStatusEnum.SUPERSEDED,
            VendorAssessmentStatusEnum.REJECTED,
        ):
            raise ValueError(
                f"Cannot escalate assessment item on a {assessment.status.value} assessment."
            )

        if item.response_status not in (
            VendorResponseStatusEnum.NON_COMPLIANT,
            VendorResponseStatusEnum.PARTIALLY_COMPLIANT,
        ):
            raise ValueError(
                f"Only NON_COMPLIANT or PARTIALLY_COMPLIANT items can be escalated to a Finding (current: {item.response_status.value})."
            )
        if item.linked_finding_id is not None:
            raise ConflictError(
                f"Assessment item '{item.question_key}' has already been escalated to Finding #{item.linked_finding_id}."
            )

        owner_id = (
            payload.owner_id
            or getattr(payload, "finding_owner_id", None)
            or vendor.business_owner_id
            or actor_id
        )
        owner = (
            db.query(User)
            .filter(
                User.id == owner_id,
                User.organization_id == organization_id,
                User.is_active.is_(True),
            )
            .first()
        )
        if not owner:
            raise LookupError(
                "Designated finding owner not found or inactive in your organization."
            )

        ctrl = cls._resolve_organization_control(
            db=db,
            organization_id=organization_id,
            explicit_control_id=payload.organization_control_id,
            common_control_id=item.rationalized_common_control_id,
        )

        impact_map = {
            FindingSeverityEnum.CRITICAL: 5,
            FindingSeverityEnum.HIGH: 4,
            FindingSeverityEnum.MEDIUM: 3,
            FindingSeverityEnum.LOW: 2,
            FindingSeverityEnum.INFORMATIONAL: 1,
        }
        impact = impact_map.get(payload.severity, 4)
        likelihood = 4 if impact >= 4 else 3
        score = impact * likelihood
        band = (
            "CRITICAL"
            if score >= 20
            else ("HIGH" if score >= 12 else ("MODERATE" if score >= 6 else "LOW"))
        )

        target_dt = payload.due_date or payload.remediation_due_date
        due_dt = (
            target_dt.date()
            if target_dt
            else (datetime.now(timezone.utc) + timedelta(days=30)).date()
        )
        finding = Finding(
            organization_id=organization_id,
            organization_control_id=ctrl.id,
            title=payload.finding_title
            or f"[TPRM Assessment {assessment.assessment_code}] {vendor.legal_name} - {item.question_key}",
            description=(
                f"Vendor assessment item '{item.question_key}' ({item.question_text}) evaluated as "
                f"{item.response_status.value}. Vendor response: {item.vendor_response_text or 'None'}. "
                f"Assessor notes: {item.assessor_notes or 'None'}."
            ),
            finding_type=FindingTypeEnum.CONTROL_GAP,
            severity=payload.severity,
            impact=impact,
            likelihood=likelihood,
            risk_score=score,
            risk_band=band,
            recommendation=payload.remediation_strategy
            or "Remediate third-party control deficiency and provide verified attestation evidence.",
            root_cause=item.assessor_notes,
            owner_id=owner.id,
            due_date=due_dt,
            status=FindingStatusEnum.OPEN,
            created_by_id=actor_id,
        )
        db.add(finding)
        db.flush()

        item.linked_finding_id = finding.id
        item.findings_count = (item.findings_count or 0) + 1
        item.escalated_by_id = actor_id
        item.escalated_at = datetime.now(timezone.utc)

        if payload.create_remediation_plan:
            rem_sev_map = {
                FindingSeverityEnum.CRITICAL: RemediationSeverityEnum.CRITICAL,
                FindingSeverityEnum.HIGH: RemediationSeverityEnum.HIGH,
                FindingSeverityEnum.MEDIUM: RemediationSeverityEnum.MEDIUM,
                FindingSeverityEnum.LOW: RemediationSeverityEnum.LOW,
                FindingSeverityEnum.INFORMATIONAL: RemediationSeverityEnum.LOW,
            }
            plan_code = f"CAPA-TPRM-{assessment.id}-{item.id}"
            plan = RemediationPlan(
                organization_id=organization_id,
                plan_code=plan_code,
                title=payload.remediation_plan_title
                or f"TPRM Remediation: {vendor.legal_name} ({item.question_key})",
                problem_statement=finding.description,
                root_cause_classification=RemediationRootCauseClassificationEnum.VENDOR_DEFAULT,
                source_type=RemediationSourceTypeEnum.FINDING,
                finding_id=finding.id,
                severity=rem_sev_map.get(
                    payload.severity, RemediationSeverityEnum.HIGH
                ),
                status=RemediationStatusEnum.DRAFT,
                plan_owner_id=owner.id,
                target_completion_at=target_dt
                or (datetime.now(timezone.utc) + timedelta(days=30)),
            )
            db.add(plan)
            db.flush()
            item.linked_remediation_plan_id = plan.id

        if payload.create_risk:
            r_impact = payload.inherent_impact or impact
            r_likelihood = payload.inherent_likelihood or likelihood
            r_score = r_impact * r_likelihood
            r_band = (
                "CRITICAL"
                if r_score >= 20
                else ("HIGH" if r_score >= 12 else ("MODERATE" if r_score >= 6 else "LOW"))
            )
            risk = Risk(
                organization_id=organization_id,
                title=f"Third-Party Control Deficiency Risk: {vendor.legal_name} ({item.question_key})",
                description=payload.risk_statement or finding.description,
                risk_category=RiskCategoryEnum.THIRD_PARTY,
                risk_source=RiskSourceEnum.VENDOR_ASSESSMENT,
                owner_id=owner.id,
                inherent_impact=r_impact,
                inherent_likelihood=r_likelihood,
                inherent_score=r_score,
                inherent_band=r_band,
                status=RiskStatusEnum.IDENTIFIED,
                treatment_strategy=RiskTreatmentStrategyEnum.MITIGATE,
                created_by_id=actor_id,
            )
            db.add(risk)
            db.flush()
            item.linked_risk_id = risk.id

        item.updated_at = datetime.now(timezone.utc)
        db.flush()
        cls.recalculate_vendor_telemetry(db, vendor)
        return item

    # ─── 13. BATCH 6: GOVERNED VENDOR OFFBOARDING WORKFLOW ──────────────────

    CANONICAL_OFFBOARDING_CHECKLIST = [
        (
            1,
            "STEP_01_ACCESS_REVOCATION",
            VendorOffboardingStepTypeEnum.ACCESS_REVOCATION,
            "Revoke SSO, IAM, VPN, and API Credentials",
            "Revoke all third-party user accounts, service principals, OAuth tokens, and network tunnels.",
            True,
        ),
        (
            2,
            "STEP_02_DATA_DESTRUCTION_OR_RETURN",
            VendorOffboardingStepTypeEnum.DATA_DESTRUCTION_OR_RETURN,
            "Data Return & Cryptographic Destruction Certificate",
            "Obtain signed certificate of data return and NIST SP 800-88 compliant media/storage sanitization.",
            True,
        ),
        (
            3,
            "STEP_03_SUBPROCESSOR_DISCONNECT",
            VendorOffboardingStepTypeEnum.SUBPROCESSOR_DISCONNECT,
            "Terminate Downstream Subprocessor Data Flows",
            "Verify that all fourth-party subprocessors have ceased processing organizational data.",
            False,
        ),
        (
            4,
            "STEP_04_ENGAGEMENT_TERMINATION",
            VendorOffboardingStepTypeEnum.ENGAGEMENT_TERMINATION,
            "Terminate Active Vendor Engagements",
            "Close and terminate all active vendor engagements and service scopes.",
            False,
        ),
        (
            5,
            "STEP_05_CONTRACT_TERMINATION_NOTICE",
            VendorOffboardingStepTypeEnum.CONTRACT_TERMINATION_NOTICE,
            "Execute Formal Legal Termination Notice",
            "Confirm delivery and acknowledgment of formal MSA/DPA termination notice.",
            False,
        ),
        (
            6,
            "STEP_06_FINAL_RISK_ARCHIVE",
            VendorOffboardingStepTypeEnum.FINAL_RISK_ARCHIVE,
            "Archive Final TPRM Posture & Audit Dossier",
            "Preserve final risk posture, evidence hashes, and closed-loop findings for regulatory retention.",
            False,
        ),
    ]

    @classmethod
    def _vendor_handles_sensitive_data(cls, vendor: Vendor) -> bool:
        for eng in vendor.engagements:
            if eng.pii_access != PiiFinancialAccessEnum.NONE or eng.data_classification in (
                DataClassificationEnum.RESTRICTED,
                DataClassificationEnum.CONFIDENTIAL,
            ):
                return True
        return False

    @classmethod
    def initiate_offboarding(
        cls,
        db: Session,
        vendor: Vendor,
        payload: Any,
        initiator_id: int,
    ) -> VendorOffboardingRecord:
        organization_id = vendor.organization_id
        if vendor.vendor_status in (
            VendorStatusEnum.OFFBOARDED,
            VendorStatusEnum.TERMINATED,
        ):
            raise ValueError(
                f"Cannot initiate offboarding for vendor already in '{vendor.vendor_status.value}' status."
            )

        active_offboarding = (
            db.query(VendorOffboardingRecord)
            .filter(
                VendorOffboardingRecord.organization_id == organization_id,
                VendorOffboardingRecord.vendor_id == vendor.id,
                VendorOffboardingRecord.status.in_(
                    [
                        VendorOffboardingStatusEnum.INITIATED,
                        VendorOffboardingStatusEnum.IN_PROGRESS,
                        VendorOffboardingStatusEnum.PENDING_SIGNOFF,
                        VendorOffboardingStatusEnum.PENDING_VERIFICATION,
                    ]
                ),
            )
            .first()
        )
        if active_offboarding:
            raise ConflictError(
                f"Vendor already has an active offboarding workflow ('{active_offboarding.offboarding_code}')."
            )

        now = datetime.now(timezone.utc)
        raw_code = getattr(payload, "offboarding_code", None)
        offboarding_code = (
            raw_code.strip()
            if raw_code
            else f"OFFB-{vendor.id}-{int(now.timestamp() * 1000)}"
        )

        existing_code = (
            db.query(VendorOffboardingRecord)
            .filter(
                VendorOffboardingRecord.organization_id == organization_id,
                VendorOffboardingRecord.vendor_id == vendor.id,
                VendorOffboardingRecord.offboarding_code == offboarding_code,
            )
            .first()
        )
        if existing_code:
            raise ConflictError(
                f"Offboarding code '{offboarding_code}' already exists for this vendor."
            )

        sensitive = cls._vendor_handles_sensitive_data(vendor)
        requires_destruction = (
            bool(getattr(payload, "requires_data_destruction_proof", False))
            or sensitive
        )

        raw_target_status = getattr(
            payload,
            "target_vendor_status",
            VendorOffboardingTargetStatusEnum.OFFBOARDED,
        )
        target_status_val = (
            raw_target_status.value
            if hasattr(raw_target_status, "value")
            else str(raw_target_status)
        )
        target_vendor_status = VendorOffboardingTargetStatusEnum(target_status_val)

        init_reason_raw = (
            getattr(payload, "initiation_reason", None)
            or getattr(payload, "rationale", None)
            or getattr(payload, "reason", "Offboarding")
        )
        init_reason = (
            init_reason_raw.value
            if hasattr(init_reason_raw, "value")
            else str(init_reason_raw)
        ).strip()

        record = VendorOffboardingRecord(
            organization_id=organization_id,
            vendor_id=vendor.id,
            offboarding_code=offboarding_code,
            target_vendor_status=target_vendor_status,
            status=VendorOffboardingStatusEnum.IN_PROGRESS,
            initiation_reason=init_reason,
            target_completion_date=getattr(payload, "target_completion_date", None),
            requires_data_destruction_proof=requires_destruction,
            initiated_by_id=initiator_id,
            initiated_at=now,
        )
        db.add(record)
        db.flush()

        for (
            step_num,
            step_key,
            step_type,
            title,
            desc_text,
            req_ev,
        ) in cls.CANONICAL_OFFBOARDING_CHECKLIST:
            item = VendorOffboardingItem(
                organization_id=organization_id,
                offboarding_record_id=record.id,
                step_number=step_num,
                step_key=step_key,
                step_type=step_type,
                title=title,
                description=desc_text,
                is_mandatory=True,
                requires_evidence=req_ev,
                status=VendorOffboardingItemStatusEnum.PENDING,
            )
            db.add(item)

        if vendor.vendor_status == VendorStatusEnum.ACTIVE:
            vendor.vendor_status = VendorStatusEnum.UNDER_REVIEW
            vendor.updated_at = now

        db.flush()
        db.refresh(record)
        return record

    @classmethod
    def attest_offboarding_item(
        cls,
        db: Session,
        record: VendorOffboardingRecord,
        item: VendorOffboardingItem,
        payload: Any,
        actor_id: int,
    ) -> VendorOffboardingItem:
        if record.status in (
            VendorOffboardingStatusEnum.APPROVED,
            VendorOffboardingStatusEnum.COMPLETED,
            VendorOffboardingStatusEnum.CANCELLED,
        ):
            raise ValueError(
                f"Cannot modify checklist items on a '{record.status.value}' offboarding record."
            )

        payload_status = getattr(payload, "status", None)
        if payload_status in (
            VendorOffboardingItemStatusEnum.WAIVED,
            VendorOffboardingItemStatusEnum.WAIVED_BY_EXCEPTION,
        ):
            return cls.waive_offboarding_item(
                db=db,
                record=record,
                item=item,
                payload=VendorOffboardingItemWaiveRequest(
                    waiver_reason=getattr(payload, "waiver_reason", None)
                    or getattr(payload, "attestation_notes", None)
                    or "Waived via item update",
                    linked_exception_id=getattr(payload, "linked_exception_id", None),
                ),
                actor_id=actor_id,
            )

        needs_evidence = (
            item.requires_evidence
            or item.step_type
            in (
                VendorOffboardingStepTypeEnum.ACCESS_REVOCATION,
                VendorOffboardingStepTypeEnum.DATA_DESTRUCTION_OR_RETURN,
                VendorOffboardingStepTypeEnum.DATA_RETURN_OR_DESTRUCTION,
            )
        )
        ev_id = getattr(payload, "evidence_id", None)
        ev = None
        if needs_evidence or ev_id is not None:
            if ev_id is None:
                raise UnprocessableEntityError(
                    f"Completing offboarding step '{item.step_key}' requires an ACCEPTED EvidenceItem."
                )
            ev = cls._verify_evidence_integrity(
                db, ev_id, record.organization_id, require_accepted=True
            )

        now = datetime.now(timezone.utc)
        item.status = VendorOffboardingItemStatusEnum.COMPLETED
        if ev is not None:
            item.evidence_id = ev.id
            item.evidence_sha256_snapshot = ev.sha256_hash
            if item.step_type in (
                VendorOffboardingStepTypeEnum.DATA_DESTRUCTION_OR_RETURN,
                VendorOffboardingStepTypeEnum.DATA_RETURN_OR_DESTRUCTION,
            ):
                record.data_destruction_evidence_id = ev.id
        att_notes = getattr(payload, "attestation_notes", None)
        item.attestation_notes = (
            att_notes.strip() if att_notes else "Verified and attested."
        )
        item.completed_by_id = actor_id
        item.completed_at = now
        item.updated_at = now
        db.flush()
        return item

    @classmethod
    def waive_offboarding_item(
        cls,
        db: Session,
        record: VendorOffboardingRecord,
        item: VendorOffboardingItem,
        payload: Any,
        actor_id: int,
    ) -> VendorOffboardingItem:
        if record.status in (
            VendorOffboardingStatusEnum.APPROVED,
            VendorOffboardingStatusEnum.COMPLETED,
            VendorOffboardingStatusEnum.CANCELLED,
        ):
            raise ValueError(
                f"Cannot modify checklist items on a '{record.status.value}' offboarding record."
            )

        # SEC-B6-50: ACCESS_REVOCATION is never waivable
        if item.step_type == VendorOffboardingStepTypeEnum.ACCESS_REVOCATION:
            raise UnprocessableEntityError(
                "ACCESS_REVOCATION is a non-waivable security control and cannot be waived."
            )

        vendor = record.vendor
        # SEC-B6-49: DATA_DESTRUCTION_OR_RETURN is never waivable when vendor handles PII or Confidential/Restricted data
        if item.step_type in (
            VendorOffboardingStepTypeEnum.DATA_DESTRUCTION_OR_RETURN,
            VendorOffboardingStepTypeEnum.DATA_RETURN_OR_DESTRUCTION,
        ):
            if record.requires_data_destruction_proof or cls._vendor_handles_sensitive_data(
                vendor
            ):
                raise UnprocessableEntityError(
                    "DATA_DESTRUCTION_OR_RETURN cannot be waived for vendors handling PII/Financial or Confidential/Restricted data."
                )

        now = datetime.now(timezone.utc)
        linked_exc_id = getattr(payload, "linked_exception_id", None)
        if linked_exc_id is None:
            raise UnprocessableEntityError(
                "Waiving a mandatory offboarding step requires an APPROVED or ACTIVE SecurityException."
            )

        exc = (
            db.query(SecurityException)
            .filter(
                SecurityException.id == linked_exc_id,
                SecurityException.organization_id == record.organization_id,
            )
            .first()
        )
        if not exc:
            raise UnprocessableEntityError(
                "Linked security exception not found in your organization."
            )
        if exc.linked_vendor_id != vendor.id:
            raise UnprocessableEntityError(
                "Security exception must be explicitly linked to this vendor."
            )
        if exc.status not in (
            ExceptionStatusEnum.APPROVED,
            ExceptionStatusEnum.ACTIVE,
        ):
            raise UnprocessableEntityError(
                f"Security exception must be APPROVED or ACTIVE (current: {exc.status.value})."
            )
        if exc.expiry_date is not None and exc.expiry_date < now.date():
            raise UnprocessableEntityError(
                "Cannot waive offboarding step with an expired security exception."
            )

        item.linked_exception_id = exc.id
        item.status = VendorOffboardingItemStatusEnum.WAIVED_BY_EXCEPTION
        w_reason = (
            getattr(payload, "waiver_reason", None)
            or getattr(payload, "waiver_justification", None)
            or "Waived by exception"
        )
        item.waiver_reason = w_reason.strip()
        item.waived_by_id = actor_id
        item.waived_at = now
        item.updated_at = now
        db.flush()
        return item

    @classmethod
    def submit_offboarding(
        cls,
        db: Session,
        record: VendorOffboardingRecord,
        actor_id: Optional[int] = None,
        submitter_id: Optional[int] = None,
    ) -> VendorOffboardingRecord:
        effective_actor_id = actor_id if actor_id is not None else submitter_id
        if record.status in (
            VendorOffboardingStatusEnum.APPROVED,
            VendorOffboardingStatusEnum.COMPLETED,
            VendorOffboardingStatusEnum.CANCELLED,
        ):
            raise ValueError(
                f"Cannot submit offboarding record in '{record.status.value}' status."
            )

        incomplete = [
            i.step_key
            for i in record.items
            if i.is_mandatory
            and i.status
            not in (
                VendorOffboardingItemStatusEnum.COMPLETED,
                VendorOffboardingItemStatusEnum.WAIVED,
                VendorOffboardingItemStatusEnum.WAIVED_BY_EXCEPTION,
            )
        ]
        if incomplete:
            raise ValueError(
                f"Cannot submit offboarding with incomplete mandatory checklist steps remaining PENDING: {incomplete}"
            )

        for i in record.items:
            if i.evidence_id is not None:
                cls._verify_snapshot_digest(
                    db,
                    i.evidence_id,
                    i.evidence_sha256_snapshot,
                    record.organization_id,
                )

        now = datetime.now(timezone.utc)
        record.status = VendorOffboardingStatusEnum.PENDING_SIGNOFF
        record.submitted_by_id = effective_actor_id
        record.submitted_at = now
        record.updated_at = now
        db.flush()
        return record

    @classmethod
    def verify_and_complete_offboarding(
        cls,
        db: Session,
        record: VendorOffboardingRecord,
        payload: VendorOffboardingCompleteRequest,
        verifier_id: int,
    ) -> VendorOffboardingRecord:
        if record.status in (
            VendorOffboardingStatusEnum.APPROVED,
            VendorOffboardingStatusEnum.COMPLETED,
        ):
            raise ConflictError(
                f"Offboarding record is already in '{record.status.value}' status."
            )
        if record.status == VendorOffboardingStatusEnum.CANCELLED:
            raise ValueError("Cannot approve or complete a CANCELLED offboarding record.")

        if record.status not in (
            VendorOffboardingStatusEnum.PENDING_SIGNOFF,
            VendorOffboardingStatusEnum.PENDING_VERIFICATION,
        ):
            raise ValueError(
                f"Offboarding record must be in PENDING_SIGNOFF status before approval (current: {record.status.value})."
            )

        if (
            record.initiated_by_id == verifier_id
            or record.submitted_by_id == verifier_id
            or any(
                i.completed_by_id == verifier_id or i.waived_by_id == verifier_id
                for i in record.items
            )
        ):
            raise PermissionError(
                "Four-eyes separation of duties violation: Offboarding initiator, submitter, or checklist attester cannot verify and close their own offboarding workflow."
            )

        incomplete = [
            i.step_key
            for i in record.items
            if i.is_mandatory
            and i.status
            not in (
                VendorOffboardingItemStatusEnum.COMPLETED,
                VendorOffboardingItemStatusEnum.WAIVED,
                VendorOffboardingItemStatusEnum.WAIVED_BY_EXCEPTION,
            )
        ]
        if incomplete:
            raise ValueError(
                f"Cannot complete offboarding while mandatory checklist steps remain PENDING: {incomplete}"
            )

        # Re-verify evidence SHA-256 integrity on all items with evidence (SEC-B6-53)
        digest_parts = [f"record:{record.id}:{record.vendor_id}:{verifier_id}"]
        for i in record.items:
            if i.status == VendorOffboardingItemStatusEnum.COMPLETED:
                if i.requires_evidence and not i.evidence_id:
                    raise UnprocessableEntityError(
                        f"Completed offboarding step '{i.step_key}' is missing required evidence."
                    )
                if i.evidence_id is not None:
                    ev = cls._verify_snapshot_digest(
                        db,
                        i.evidence_id,
                        i.evidence_sha256_snapshot,
                        record.organization_id,
                    )
                    digest_parts.append(f"{i.step_key}:{ev.sha256_hash}")

        now = datetime.now(timezone.utc)
        notes = (
            payload.closure_notes
            or payload.review_notes
            or "Verified and closed under Four-Eyes governance."
        )
        record.status = VendorOffboardingStatusEnum.COMPLETED
        record.verified_by_id = verifier_id
        record.verified_at = now
        record.approved_by_id = verifier_id
        record.approved_at = now
        record.closure_notes = notes.strip()
        record.review_notes = (payload.review_notes or notes).strip()
        record.signoff_hash_sha256 = hashlib.sha256(
            "|".join(digest_parts).encode("utf-8")
        ).hexdigest()
        record.updated_at = now

        vendor = record.vendor
        if record.target_vendor_status == VendorOffboardingTargetStatusEnum.TERMINATED:
            vendor.vendor_status = VendorStatusEnum.TERMINATED
        else:
            vendor.vendor_status = VendorStatusEnum.OFFBOARDED
        vendor.offboarding_completed_at = now
        vendor.updated_at = now

        # Cascade termination to active engagements, contracts, subprocessors, and SLA obligations (SEC-B6-57)
        for eng in vendor.engagements:
            if eng.status in (
                EngagementStatusEnum.ACTIVE,
                EngagementStatusEnum.PROPOSED,
                EngagementStatusEnum.SCOPING,
            ):
                eng.status = EngagementStatusEnum.TERMINATED
                eng.updated_at = now

        for c in vendor.contracts:
            if c.status in (
                VendorContractStatusEnum.APPROVED,
                VendorContractStatusEnum.ACTIVE,
            ):
                c.status = VendorContractStatusEnum.TERMINATED
                c.updated_at = now

        for sp in vendor.subprocessors:
            if sp.status != VendorSubprocessorStatusEnum.TERMINATED:
                sp.status = VendorSubprocessorStatusEnum.TERMINATED
                sp.termination_reason = (
                    sp.termination_reason
                    or f"Automatically terminated upon vendor offboarding ({record.offboarding_code})."
                )
                sp.updated_at = now

        for ob in vendor.sla_obligations:
            if ob.status not in (
                VendorSlaObligationStatusEnum.TERMINATED,
                VendorSlaObligationStatusEnum.RETIRED,
                VendorSlaObligationStatusEnum.EXPIRED,
            ):
                ob.status = VendorSlaObligationStatusEnum.TERMINATED
                ob.updated_at = now

        db.flush()
        cls.recalculate_vendor_telemetry(db, vendor)
        return record

    @classmethod
    def reject_offboarding(
        cls,
        db: Session,
        record: VendorOffboardingRecord,
        payload: VendorOffboardingCompleteRequest,
        reviewer_id: int,
    ) -> VendorOffboardingRecord:
        if record.status not in (
            VendorOffboardingStatusEnum.PENDING_SIGNOFF,
            VendorOffboardingStatusEnum.PENDING_VERIFICATION,
            VendorOffboardingStatusEnum.IN_PROGRESS,
        ):
            raise ValueError(
                f"Cannot reject offboarding record in '{record.status.value}' status."
            )
        if record.initiated_by_id == reviewer_id or record.submitted_by_id == reviewer_id:
            raise PermissionError(
                "Four-eyes separation of duties violation: Offboarding initiator or submitter cannot reject their own offboarding workflow."
            )
        reason = (
            payload.rejection_reason
            or payload.reason
            or payload.review_notes
            or payload.closure_notes
        )
        if not reason or len(reason.strip()) < 5:
            raise ValueError("Rejection reason (minimum 5 characters) is required.")

        now = datetime.now(timezone.utc)
        record.status = VendorOffboardingStatusEnum.IN_PROGRESS
        record.rejection_reason = reason.strip()
        record.updated_at = now
        db.flush()
        return record

    @classmethod
    def cancel_offboarding(
        cls,
        db: Session,
        record: VendorOffboardingRecord,
        payload: VendorOffboardingCancelRequest,
        actor_id: int,
    ) -> VendorOffboardingRecord:
        if record.status in (
            VendorOffboardingStatusEnum.APPROVED,
            VendorOffboardingStatusEnum.COMPLETED,
        ):
            raise ValueError("Cannot cancel a COMPLETED offboarding record.")
        if record.status == VendorOffboardingStatusEnum.CANCELLED:
            raise ValueError("Offboarding record is already CANCELLED.")

        now = datetime.now(timezone.utc)
        record.status = VendorOffboardingStatusEnum.CANCELLED
        record.cancelled_by_id = actor_id
        record.cancelled_at = now
        record.cancellation_reason = payload.cancellation_reason.strip()
        record.updated_at = now
        db.flush()
        return record
