from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    users,
    organizations,
    audit_logs,
    health,
    frameworks,
    controls,
    policies,
    evidence,
    assessments,
    findings,
    risks,
    exceptions,
    audits,
    monitoring,
    harmonization,
    tprm,
    incidents,
    remediations,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(frameworks.router, prefix="/frameworks", tags=["Frameworks"])
api_router.include_router(controls.router, prefix="/controls", tags=["Controls"])
api_router.include_router(policies.router, prefix="/policies", tags=["Policies"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["Evidence"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])
api_router.include_router(findings.router, prefix="/findings", tags=["Findings"])
api_router.include_router(risks.router, prefix="/risks", tags=["Risks"])
api_router.include_router(exceptions.router, prefix="/exceptions", tags=["Exceptions"])
api_router.include_router(audits.router, prefix="/audits", tags=["Audits"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Continuous Monitoring"])
api_router.include_router(harmonization.router, prefix="/harmonization", tags=["Multi-Framework Harmonization"])
api_router.include_router(tprm.router, prefix="/vendors", tags=["Third-Party & Vendor Risk Management"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["Security Incident Management & Breach Governance"])
api_router.include_router(remediations.router, prefix="/remediations", tags=["Governed Remediation & Corrective Actions"])