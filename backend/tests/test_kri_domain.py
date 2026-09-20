from datetime import datetime, timezone, timedelta, date
import pytest
from sqlalchemy.orm import Session

from app.models.kri import (
    AppetiteStatementStatusEnum,
    BreachStatusEnum,
    KeyRiskIndicator,
    KriBreachRecord,
    KriDirectionEnum,
    KriEvaluationStatusEnum,
    KriFrequencyEnum,
    KriObservation,
    KriRiskLink,
    KriSourceTypeEnum,
    KriStatusEnum,
    KriThreshold,
    RiskAppetiteStatement,
)
from app.models.organization import Organization
from app.models.risk import Risk, RiskCategoryEnum
from app.models.user import User
from app.schemas.kri import (
    KeyRiskIndicatorCreate,
    KriBreachAcknowledgeRequest,
    KriBreachCloseRequest,
    KriBreachEscalateFindingRequest,
    KriObservationCreate,
    KriRiskLinkCreate,
    KriThresholdCreate,
    RiskAppetiteStatementCreate,
)
from app.services.kri_evaluation_service import KriEvaluationService
from app.services.kri_service import KriService


@pytest.fixture
def test_setup(db: Session):
    org = Organization(name="KRI Corp", slug="kri-corp")
    db.add(org)
    db.flush()

    user_analyst = User(
        organization_id=org.id,
        email="analyst@kri.example.com",
        full_name="GRC Analyst",
        hashed_password="hash",
        role="GRC_ANALYST",
    )
    user_manager = User(
        organization_id=org.id,
        email="manager@kri.example.com",
        full_name="GRC Manager",
        hashed_password="hash",
        role="MANAGER",
    )
    user_admin = User(
        organization_id=org.id,
        email="admin@kri.example.com",
        full_name="Tenant Admin",
        hashed_password="hash",
        role="ADMIN",
    )
    db.add_all([user_analyst, user_manager, user_admin])
    db.flush()

    risk = Risk(
        organization_id=org.id,
        title="Unauthorized Cloud Ingress Exposure",
        description="Public bucket or open security group exposure",
        risk_category=RiskCategoryEnum.CYBERSECURITY,
        inherent_impact=4,
        inherent_likelihood=4,
        inherent_score=16,
        inherent_band="HIGH",
        target_risk_band="MODERATE",
        appetite_status="ABOVE_APPETITE",
    )
    db.add(risk)
    db.commit()

    return {
        "org": org,
        "analyst": user_analyst,
        "manager": user_manager,
        "admin": user_admin,
        "risk": risk,
    }


def test_directional_evaluation_lower_is_better():
    thresh = KriThreshold(
        organization_id=1,
        kri_id=1,
        warning_threshold=5.0,
        critical_threshold=10.0,
    )

    # Normal: v <= 5.0
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.LOWER_IS_BETTER, thresh, 3.0
        )
        == KriEvaluationStatusEnum.NORMAL
    )
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.LOWER_IS_BETTER, thresh, 5.0
        )
        == KriEvaluationStatusEnum.NORMAL
    )

    # Warning: 5.0 < v <= 10.0
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.LOWER_IS_BETTER, thresh, 5.0001
        )
        == KriEvaluationStatusEnum.WARNING
    )
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.LOWER_IS_BETTER, thresh, 10.0
        )
        == KriEvaluationStatusEnum.WARNING
    )

    # Critical: v > 10.0
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.LOWER_IS_BETTER, thresh, 10.001
        )
        == KriEvaluationStatusEnum.CRITICAL
    )
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.LOWER_IS_BETTER, thresh, 25.0
        )
        == KriEvaluationStatusEnum.CRITICAL
    )


def test_directional_evaluation_higher_is_better():
    thresh = KriThreshold(
        organization_id=1,
        kri_id=1,
        warning_threshold=95.0,
        critical_threshold=80.0,
    )

    # Normal: v >= 95.0
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.HIGHER_IS_BETTER, thresh, 98.0
        )
        == KriEvaluationStatusEnum.NORMAL
    )
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.HIGHER_IS_BETTER, thresh, 95.0
        )
        == KriEvaluationStatusEnum.NORMAL
    )

    # Warning: 80.0 <= v < 95.0
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.HIGHER_IS_BETTER, thresh, 94.99
        )
        == KriEvaluationStatusEnum.WARNING
    )
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.HIGHER_IS_BETTER, thresh, 80.0
        )
        == KriEvaluationStatusEnum.WARNING
    )

    # Critical: v < 80.0
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.HIGHER_IS_BETTER, thresh, 79.99
        )
        == KriEvaluationStatusEnum.CRITICAL
    )
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.HIGHER_IS_BETTER, thresh, 50.0
        )
        == KriEvaluationStatusEnum.CRITICAL
    )


def test_directional_evaluation_within_range():
    thresh = KriThreshold(
        organization_id=1,
        kri_id=1,
        warning_threshold=40.0,
        critical_threshold=80.0,
        range_min_warning=40.0,
        range_max_warning=70.0,
        range_min_critical=20.0,
        range_max_critical=85.0,
    )

    # Normal: 40.0 <= v <= 70.0
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.WITHIN_RANGE, thresh, 55.0
        )
        == KriEvaluationStatusEnum.NORMAL
    )
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.WITHIN_RANGE, thresh, 40.0
        )
        == KriEvaluationStatusEnum.NORMAL
    )
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.WITHIN_RANGE, thresh, 70.0
        )
        == KriEvaluationStatusEnum.NORMAL
    )

    # Warning: [20.0 <= v < 40.0] or [70.0 < v <= 85.0]
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.WITHIN_RANGE, thresh, 25.0
        )
        == KriEvaluationStatusEnum.WARNING
    )
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.WITHIN_RANGE, thresh, 75.0
        )
        == KriEvaluationStatusEnum.WARNING
    )

    # Critical: v < 20.0 or v > 85.0
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.WITHIN_RANGE, thresh, 15.0
        )
        == KriEvaluationStatusEnum.CRITICAL
    )
    assert (
        KriEvaluationService.evaluate_observation(
            KriDirectionEnum.WITHIN_RANGE, thresh, 90.0
        )
        == KriEvaluationStatusEnum.CRITICAL
    )


def test_observation_sha256_digest_determinism():
    now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
    d1 = KriEvaluationService.compute_observation_digest(
        kri_id=42,
        value=12.3456,
        unit="PERCENTAGE",
        observed_at=now,
        source_type="MANUAL_ENTRY",
        source_identifier="EXT-1",
    )
    d2 = KriEvaluationService.compute_observation_digest(
        kri_id=42,
        value=12.3456,
        unit="percentage",  # normalized uppercase
        observed_at=now,
        source_type="MANUAL_ENTRY",
        source_identifier="EXT-1",
    )
    assert d1 == d2
    assert len(d1) == 64

    # Different value yields different hash
    d3 = KriEvaluationService.compute_observation_digest(
        kri_id=42,
        value=12.3457,
        unit="PERCENTAGE",
        observed_at=now,
        source_type="MANUAL_ENTRY",
        source_identifier="EXT-1",
    )
    assert d1 != d3


def test_stale_data_cadence_calculation():
    now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)

    # DAILY cadence (24h) -> stale after 1.5 * 24 = 36 hours
    fresh_time = now - timedelta(hours=30)
    assert (
        KriEvaluationService.check_is_stale(
            KriFrequencyEnum.DAILY, fresh_time, current_time=now
        )
        is False
    )

    stale_time = now - timedelta(hours=37)
    assert (
        KriEvaluationService.check_is_stale(
            KriFrequencyEnum.DAILY, stale_time, current_time=now
        )
        is True
    )

    # Missing observation is always stale
    assert (
        KriEvaluationService.check_is_stale(
            KriFrequencyEnum.DAILY, None, current_time=now
        )
        is True
    )


def test_risk_appetite_statement_four_eyes_and_superseding(db: Session, test_setup):
    org = test_setup["org"]
    analyst = test_setup["analyst"]
    manager = test_setup["manager"]

    # 1. Create statement as analyst
    stmt_data = RiskAppetiteStatementCreate(
        statement_code="APP-2026-001",
        title="FY2026 Corporate Cyber & Operational Risk Appetite",
        executive_summary="Board-approved maximum tolerance levels across operational risk categories.",
        category_appetites={
            "CYBERSECURITY": "LOW",
            "OPERATIONAL": "MODERATE",
            "COMPLIANCE": "LOW",
        },
        effective_from=date(2026, 1, 1),
        review_cadence_months=12,
    )
    stmt = KriService.create_appetite_statement(
        db, org.id, stmt_data, actor_id=analyst.id
    )
    assert stmt.status == AppetiteStatementStatusEnum.DRAFT

    # 2. Self-approval must be rejected
    with pytest.raises(Exception) as exc_info:
        KriService.approve_appetite_statement(db, org.id, stmt.id, actor_id=analyst.id)
    assert "Four-Eyes Violation" in str(exc_info.value.detail)

    # 3. Manager approves statement
    approved_stmt = KriService.approve_appetite_statement(
        db, org.id, stmt.id, actor_id=manager.id
    )
    assert approved_stmt.status == AppetiteStatementStatusEnum.APPROVED
    assert approved_stmt.approved_by_id == manager.id

    # 4. Approving a new version supersedes the previous one
    stmt_data_v2 = RiskAppetiteStatementCreate(
        statement_code="APP-2027-001",
        title="FY2027 Risk Appetite",
        executive_summary="Updated risk posture for 2027.",
        category_appetites={"CYBERSECURITY": "LOW"},
        effective_from=date(2027, 1, 1),
    )
    stmt_v2 = KriService.create_appetite_statement(
        db, org.id, stmt_data_v2, actor_id=analyst.id
    )
    approved_v2 = KriService.approve_appetite_statement(
        db, org.id, stmt_v2.id, actor_id=manager.id
    )
    assert approved_v2.status == AppetiteStatementStatusEnum.APPROVED

    db.refresh(approved_stmt)
    assert approved_stmt.status == AppetiteStatementStatusEnum.SUPERSEDED


def test_kri_breach_hysteresis_and_recovery_flow(db: Session, test_setup):
    org = test_setup["org"]
    analyst = test_setup["analyst"]
    manager = test_setup["manager"]

    # 1. Register KRI with threshold
    kri_data = KeyRiskIndicatorCreate(
        kri_code="KRI-SEC-PHISH",
        title="Simulated Phishing Click Rate",
        description="Percentage of employees failing quarterly phishing simulations",
        risk_category=RiskCategoryEnum.CYBERSECURITY,
        unit_of_measure="PERCENTAGE",
        frequency=KriFrequencyEnum.WEEKLY,
        direction=KriDirectionEnum.LOWER_IS_BETTER,
        initial_threshold=KriThresholdCreate(
            warning_threshold=5.0,
            critical_threshold=10.0,
        ),
    )
    kri = KriService.create_kri(db, org.id, kri_data, actor_id=analyst.id)

    # 2. Ingest normal observation (3.2%)
    obs_normal = KriService.ingest_observation(
        db,
        org.id,
        kri.id,
        KriObservationCreate(
            observed_value=3.2,
            unit="PERCENTAGE",
            observed_at=datetime.now(timezone.utc),
            source_type=KriSourceTypeEnum.MANUAL_ENTRY,
        ),
        actor_id=analyst.id,
    )
    assert obs_normal.evaluation_status == KriEvaluationStatusEnum.NORMAL
    assert obs_normal.breach_id is None

    # 3. Ingest breach observation (14.5%)
    obs_breach1 = KriService.ingest_observation(
        db,
        org.id,
        kri.id,
        KriObservationCreate(
            observed_value=14.5,
            unit="PERCENTAGE",
            observed_at=datetime.now(timezone.utc),
            source_type=KriSourceTypeEnum.MANUAL_ENTRY,
        ),
        actor_id=analyst.id,
    )
    assert obs_breach1.evaluation_status == KriEvaluationStatusEnum.CRITICAL
    assert obs_breach1.breach_id is not None

    breach1 = KriService.get_breach(db, org.id, obs_breach1.breach_id)
    assert breach1.status == BreachStatusEnum.DETECTED
    assert breach1.breach_value == 14.5
    assert breach1.peak_value == 14.5

    # 4. Hysteresis check: Subsequent worse observation (18.2%) attaches to existing active breach
    obs_breach2 = KriService.ingest_observation(
        db,
        org.id,
        kri.id,
        KriObservationCreate(
            observed_value=18.2,
            unit="PERCENTAGE",
            observed_at=datetime.now(timezone.utc),
            source_type=KriSourceTypeEnum.MANUAL_ENTRY,
        ),
        actor_id=analyst.id,
    )
    assert obs_breach2.breach_id == breach1.id
    db.refresh(breach1)
    assert breach1.peak_value == 18.2
    assert breach1.latest_observation_id == obs_breach2.id

    # Total breaches count must remain 1 (no duplicate breach record)
    all_breaches = KriService.list_breaches(db, org.id, kri_id=kri.id)
    assert len(all_breaches) == 1

    # 5. Numerical recovery observation (4.0%)
    obs_recovered = KriService.ingest_observation(
        db,
        org.id,
        kri.id,
        KriObservationCreate(
            observed_value=4.0,
            unit="PERCENTAGE",
            observed_at=datetime.now(timezone.utc),
            source_type=KriSourceTypeEnum.MANUAL_ENTRY,
        ),
        actor_id=analyst.id,
    )
    assert obs_recovered.evaluation_status == KriEvaluationStatusEnum.NORMAL
    db.refresh(breach1)
    assert breach1.status == BreachStatusEnum.RECOVERED
    assert breach1.recovered_at is not None

    # 6. Four-Eyes closure sign-off
    # Analyst acknowledges or manager closes
    closed_breach = KriService.close_breach(
        db,
        org.id,
        breach1.id,
        KriBreachCloseRequest(
            closure_notes="Staff completed targeted anti-phishing training. Failure rate dropped below warning threshold."
        ),
        actor_id=manager.id,
    )
    assert closed_breach.status == BreachStatusEnum.CLOSED
    assert closed_breach.closed_by_id == manager.id


def test_kri_risk_linkage_correlation(db: Session, test_setup):
    org = test_setup["org"]
    analyst = test_setup["analyst"]
    risk = test_setup["risk"]

    kri_data = KeyRiskIndicatorCreate(
        kri_code="KRI-CLOUD-01",
        title="Unrestricted Ingress Rules Count",
        description="Active 0.0.0.0/0 ingress security group rules",
        risk_category=RiskCategoryEnum.CYBERSECURITY,
        unit_of_measure="COUNT",
        frequency=KriFrequencyEnum.DAILY,
        direction=KriDirectionEnum.LOWER_IS_BETTER,
    )
    kri = KriService.create_kri(db, org.id, kri_data, actor_id=analyst.id)

    # Link risk with correlation weight +0.85
    link = KriService.link_risk(
        db,
        org.id,
        kri.id,
        KriRiskLinkCreate(
            risk_id=risk.id,
            correlation_weight=0.85,
            notes="Strong positive correlation with cloud exposure risk",
        ),
        actor_id=analyst.id,
    )
    assert link.correlation_weight == 0.85
    assert link.risk_id == risk.id

    # Duplicate link must be rejected
    with pytest.raises(Exception) as exc_info:
        KriService.link_risk(
            db,
            org.id,
            kri.id,
            KriRiskLinkCreate(risk_id=risk.id, correlation_weight=0.85),
            actor_id=analyst.id,
        )
    assert "already linked" in str(exc_info.value.detail)


def test_telemetry_overview_aggregates(db: Session, test_setup):
    org = test_setup["org"]
    analyst = test_setup["analyst"]

    overview = KriService.get_telemetry_overview(db, org.id)
    assert "total_kris" in overview
    assert "active_breaches" in overview
    assert "appetite_compliance_rate" in overview
