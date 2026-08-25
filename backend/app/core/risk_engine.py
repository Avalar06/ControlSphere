from datetime import date, timedelta
from typing import Optional, Tuple
from app.models.finding import FindingStatusEnum


def calculate_risk_score(impact: int, likelihood: int) -> Tuple[int, str]:
    """Deterministically calculate risk score and risk band based on 5x5 matrix.
    
    Formula: Risk Score = Impact * Likelihood (Range: 1 to 25)
    Bands:
      1-4:   LOW
      5-9:   MODERATE
      10-16: HIGH
      17-25: CRITICAL
    """
    # Enforce bounding
    bounded_impact = max(1, min(5, impact))
    bounded_likelihood = max(1, min(5, likelihood))
    score = bounded_impact * bounded_likelihood

    if score <= 4:
        band = "LOW"
    elif score <= 9:
        band = "MODERATE"
    elif score <= 16:
        band = "HIGH"
    else:
        band = "CRITICAL"

    return score, band


def calculate_overdue_status(
    status: FindingStatusEnum,
    due_date: Optional[date],
    reference_date: Optional[date] = None,
) -> str:
    """Calculate deterministic overdue status from target due date.
    
    Returns:
      - 'COMPLETED': if status is RESOLVED, ACCEPTED_RISK, or CLOSED
      - 'NO_DUE_DATE': if no due date specified
      - 'OVERDUE': if due_date < reference_date
      - 'DUE_SOON': if reference_date <= due_date <= reference_date + 7 days
      - 'ON_TRACK': if due_date > reference_date + 7 days
    """
    if status in [
        FindingStatusEnum.RESOLVED,
        FindingStatusEnum.ACCEPTED_RISK,
        FindingStatusEnum.CLOSED,
    ]:
        return "COMPLETED"

    if not due_date:
        return "NO_DUE_DATE"

    today = reference_date or date.today()
    if due_date < today:
        return "OVERDUE"
    elif due_date <= today + timedelta(days=7):
        return "DUE_SOON"
    else:
        return "ON_TRACK"
