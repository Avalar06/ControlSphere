import enum
from typing import Set


class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    GRC_ANALYST = "GRC_ANALYST"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    AUDITOR = "AUDITOR"
    MANAGER = "MANAGER"
    VIEWER = "VIEWER"


class Permission(str, enum.Enum):
    # Organization & Users
    ORG_READ = "org:read"
    ORG_UPDATE = "org:update"
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Audit Logs
    AUDIT_LOG_READ = "audit_log:read"

    # GRC Domain Permissions
    FRAMEWORK_READ = "framework:read"
    FRAMEWORK_MANAGE = "framework:manage"
    CONTROL_READ = "control:read"
    CONTROL_ASSESS = "control:assess"
    EVIDENCE_READ = "evidence:read"
    EVIDENCE_UPLOAD = "evidence:upload"
    EVIDENCE_REVIEW = "evidence:review"
    EVIDENCE_MANAGE = "evidence:manage"
    FINDING_READ = "finding:read"
    FINDING_MANAGE = "finding:manage"
    RISK_READ = "risk:read"
    RISK_MANAGE = "risk:manage"
    RISK_ACCEPT = "risk:accept"
    REMEDIATION_READ = "remediation:read"
    REMEDIATION_MANAGE = "remediation:manage"
    EXCEPTION_READ = "exception:read"
    EXCEPTION_MANAGE = "exception:manage"
    EXCEPTION_APPROVE = "exception:approve"
    AUDIT_READ = "audit:read"
    AUDIT_MANAGE = "audit:manage"
    POLICY_READ = "policy:read"
    POLICY_MANAGE = "policy:manage"


ROLE_PERMISSIONS: dict[RoleEnum, Set[Permission]] = {
    RoleEnum.ADMIN: set(Permission),  # All permissions
    RoleEnum.GRC_ANALYST: {
        Permission.ORG_READ,
        Permission.USER_READ,
        Permission.FRAMEWORK_READ,
        Permission.FRAMEWORK_MANAGE,
        Permission.CONTROL_READ,
        Permission.CONTROL_ASSESS,
        Permission.EVIDENCE_READ,
        Permission.EVIDENCE_UPLOAD,
        Permission.EVIDENCE_REVIEW,
        Permission.EVIDENCE_MANAGE,
        Permission.FINDING_READ,
        Permission.FINDING_MANAGE,
        Permission.RISK_READ,
        Permission.RISK_MANAGE,
        Permission.RISK_ACCEPT,
        Permission.REMEDIATION_READ,
        Permission.REMEDIATION_MANAGE,
        Permission.EXCEPTION_READ,
        Permission.EXCEPTION_MANAGE,
        Permission.EXCEPTION_APPROVE,
        Permission.AUDIT_READ,
        Permission.POLICY_READ,
        Permission.POLICY_MANAGE,
    },
    RoleEnum.SECURITY_ANALYST: {
        Permission.ORG_READ,
        Permission.USER_READ,
        Permission.CONTROL_READ,
        Permission.CONTROL_ASSESS,
        Permission.EVIDENCE_READ,
        Permission.EVIDENCE_UPLOAD,
        Permission.FINDING_READ,
        Permission.FINDING_MANAGE,
        Permission.RISK_READ,
        Permission.RISK_MANAGE,
        Permission.RISK_ACCEPT,
        Permission.REMEDIATION_READ,
        Permission.REMEDIATION_MANAGE,
        Permission.EXCEPTION_READ,
        Permission.EXCEPTION_MANAGE,
    },
    RoleEnum.AUDITOR: {
        Permission.ORG_READ,
        Permission.USER_READ,
        Permission.AUDIT_LOG_READ,
        Permission.FRAMEWORK_READ,
        Permission.CONTROL_READ,
        Permission.EVIDENCE_READ,
        Permission.EVIDENCE_REVIEW,
        Permission.FINDING_READ,
        Permission.RISK_READ,
        Permission.REMEDIATION_READ,
        Permission.EXCEPTION_READ,
        Permission.AUDIT_READ,
        Permission.AUDIT_MANAGE,
        Permission.POLICY_READ,
    },
    RoleEnum.MANAGER: {
        Permission.ORG_READ,
        Permission.USER_READ,
        Permission.FRAMEWORK_READ,
        Permission.CONTROL_READ,
        Permission.EVIDENCE_READ,
        Permission.FINDING_READ,
        Permission.RISK_READ,
        Permission.REMEDIATION_READ,
        Permission.EXCEPTION_READ,
        Permission.EXCEPTION_APPROVE,
        Permission.AUDIT_READ,
        Permission.POLICY_READ,
    },
    RoleEnum.VIEWER: {
        Permission.ORG_READ,
        Permission.FRAMEWORK_READ,
        Permission.CONTROL_READ,
        Permission.EVIDENCE_READ,
        Permission.FINDING_READ,
        Permission.RISK_READ,
        Permission.REMEDIATION_READ,
        Permission.EXCEPTION_READ,
        Permission.AUDIT_READ,
        Permission.POLICY_READ,
    },
}


def has_permission(role: RoleEnum, permission: Permission) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms