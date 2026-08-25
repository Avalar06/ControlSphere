from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple
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


def calculate_appetite_status(score: int, target_band: str = "MODERATE") -> str:
    """Calculate whether risk score falls within or exceeds organization risk appetite.
    
    Target Bands:
      - LOW (Max acceptable score = 4)
      - MODERATE (Max acceptable score = 9)
      - HIGH (Max acceptable score = 16)
    
    Returns:
      - 'WITHIN_APPETITE': score <= target limit
      - 'NEAR_LIMIT': score is in the adjacent higher band
      - 'ABOVE_APPETITE': score significantly exceeds acceptable threshold
    """
    target = (target_band or "MODERATE").upper()
    if target == "LOW":
        if score <= 4:
            return "WITHIN_APPETITE"
        elif score <= 9:
            return "NEAR_LIMIT"
        else:
            return "ABOVE_APPETITE"
    elif target == "HIGH":
        if score <= 16:
            return "WITHIN_APPETITE"
        else:
            return "NEAR_LIMIT"
    else:  # MODERATE
        if score <= 9:
            return "WITHIN_APPETITE"
        elif score <= 16:
            return "NEAR_LIMIT"
        else:
            return "ABOVE_APPETITE"


def calculate_overdue_status(
    status: FindingStatusEnum,
    due_date: Optional[date],
    reference_date: Optional[date] = None,
) -> str:
    """Calculate deterministic overdue status from target due date for findings."""
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


def calculate_treatment_overdue_status(
    status: str,
    due_date: Optional[date],
    reference_date: Optional[date] = None,
) -> str:
    """Calculate deterministic overdue status for risk treatments."""
    if status in ["ACCEPTED", "CLOSED"]:
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


def calculate_exception_effective_status(
    status: str,
    expiry_date: date,
    effective_date: Optional[date] = None,
    reference_date: Optional[date] = None,
) -> str:
    """Calculate live status of an exception accounting for approval and calendar validity."""
    if status in ["REJECTED", "CLOSED"]:
        return status

    today = reference_date or date.today()
    if expiry_date < today:
        return "EXPIRED"

    if effective_date and effective_date > today:
        return "PENDING_EFFECTIVE"

    if status in ["APPROVED", "ACTIVE"]:
        return "ACTIVE"

    return status


def generate_risk_heatmap_matrix(risks: List[Any]) -> List[Dict[str, Any]]:
    """Generate 5x5 matrix heatmap data of inherent risk distribution."""
    # Initialize 5x5 grid (Likelihood: 1..5, Impact: 1..5)
    cells = []
    # Count mapping: (likelihood, impact) -> count
    counts: Dict[Tuple[int, int], int] = {}
    for r in risks:
        lik = getattr(r, "inherent_likelihood", 3)
        imp = getattr(r, "inherent_impact", 3)
        bounded_lik = max(1, min(5, lik))
        bounded_imp = max(1, min(5, imp))
        counts[(bounded_lik, bounded_imp)] = counts.get((bounded_lik, bounded_imp), 0) + 1

    for lik in range(5, 0, -1):  # 5 to 1 for visual matrix Y-axis (top is High)
        for imp in range(1, 6):  # 1 to 5 for visual matrix X-axis (left is Low)
            score, band = calculate_risk_score(imp, lik)
            cells.append({
                "likelihood": lik,
                "impact": imp,
                "score": score,
                "band": band,
                "count": counts.get((lik, imp), 0),
            })
    return cells
