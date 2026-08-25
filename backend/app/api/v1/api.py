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