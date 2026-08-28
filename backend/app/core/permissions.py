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
    REMEDIATION_APPROVE = "remediation:approve"
    REMEDIATION_EXECUTE = "remediation:execute"
    REMEDIATION_VERIFY = "remediation:verify"
    EXCEPTION_READ = "exception:read"
    EXCEPTION_MANAGE = "exception:manage"
    EXCEPTION_APPROVE = "exception:approve"
    POLICY_READ = "policy:read"
    POLICY_MANAGE = "policy:manage"

    # Phase 6: Audit Management Permissions
    AUDIT_READ = "audit:read"
    AUDIT_MANAGE = "audit:manage"
    AUDIT_EXECUTE = "audit:execute"
    AUDIT_REVIEW = "audit:review"
    AUDIT_APPROVE = "audit:approve"
    AUDIT_CLOSE = "audit:close"

    # Phase 7: Continuous Control Monitoring Permissions
    MONITORING_READ = "monitoring:read"
    MONITORING_EXECUTE = "monitoring:execute"
    MONITORING_MANAGE = "monitoring:manage"
    MONITORING_ALERT_ACTION = "monitoring:alert_action"

    # Phase 8: Multi-Framework Harmonization & Control Rationalization Permissions
    HARMONIZATION_READ = "harmonization:read"
    HARMONIZATION_MANAGE = "harmonization:manage"
    HARMONIZATION_EXECUTE = "harmonization:execute"
    CROSSWALK_ADMIN = "crosswalk:admin"

    # Phase 9: Third-Party & Vendor Risk Management (TPRM) Permissions
    VENDOR_READ = "vendor:read"
    VENDOR_MANAGE = "vendor:manage"
    VENDOR_ASSESS = "vendor:assess"
    VENDOR_APPROVE = "vendor:approve"
    VENDOR_RISK_MANAGE = "vendor:risk_manage"

    # Phase 10: Security Incident Management & Regulatory Disclosure Permissions
    INCIDENT_READ = "incident:read"
    INCIDENT_MANAGE = "incident:manage"
    INCIDENT_DISCLOSE = "incident:disclose"
    INCIDENT_CLOSE = "incident:close"

    # Phase 12: QUANTUM-GRC Cyber Risk Quantification & ROSI Permissions
    QUANTRISK_READ = "quantrisk:read"
    QUANTRISK_MANAGE = "quantrisk:manage"
    QUANTRISK_EXECUTE = "quantrisk:execute"
    QUANTRISK_APPROVE = "quantrisk:approve"

    # Phase 13: Operational Resilience & Business Impact Analysis Permissions
    RESILIENCE_READ = "resilience:read"
    RESILIENCE_MANAGE = "resilience:manage"
    RESILIENCE_APPROVE = "resilience:approve"


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
        Permission.REMEDIATION_EXECUTE,
        Permission.EXCEPTION_READ,
        Permission.EXCEPTION_MANAGE,
        Permission.EXCEPTION_APPROVE,
        Permission.AUDIT_READ,
        Permission.AUDIT_MANAGE,
        Permission.AUDIT_EXECUTE,
        Permission.AUDIT_REVIEW,
        Permission.POLICY_READ,
        Permission.POLICY_MANAGE,
        Permission.MONITORING_READ,
        Permission.MONITORING_EXECUTE,
        Permission.MONITORING_ALERT_ACTION,
        Permission.HARMONIZATION_READ,
        Permission.HARMONIZATION_MANAGE,
        Permission.HARMONIZATION_EXECUTE,
        Permission.VENDOR_READ,
        Permission.VENDOR_MANAGE,
        Permission.VENDOR_ASSESS,
        Permission.VENDOR_RISK_MANAGE,
        Permission.INCIDENT_READ,
        Permission.INCIDENT_MANAGE,
        Permission.INCIDENT_DISCLOSE,
        Permission.QUANTRISK_READ,
        Permission.QUANTRISK_MANAGE,
        Permission.QUANTRISK_EXECUTE,
        Permission.RESILIENCE_READ,
        Permission.RESILIENCE_MANAGE,
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
        Permission.REMEDIATION_EXECUTE,
        Permission.EXCEPTION_READ,
        Permission.EXCEPTION_MANAGE,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXECUTE,
        Permission.MONITORING_READ,
        Permission.MONITORING_EXECUTE,
        Permission.MONITORING_ALERT_ACTION,
        Permission.HARMONIZATION_READ,
        Permission.HARMONIZATION_MANAGE,
        Permission.HARMONIZATION_EXECUTE,
        Permission.VENDOR_READ,
        Permission.VENDOR_MANAGE,
        Permission.VENDOR_ASSESS,
        Permission.VENDOR_RISK_MANAGE,
        Permission.INCIDENT_READ,
        Permission.INCIDENT_MANAGE,
        Permission.INCIDENT_DISCLOSE,
        Permission.QUANTRISK_READ,
        Permission.QUANTRISK_MANAGE,
        Permission.QUANTRISK_EXECUTE,
        Permission.RESILIENCE_READ,
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
        Permission.REMEDIATION_VERIFY,
        Permission.EXCEPTION_READ,
        Permission.AUDIT_READ,
        Permission.AUDIT_MANAGE,
        Permission.AUDIT_EXECUTE,
        Permission.AUDIT_REVIEW,
        Permission.AUDIT_APPROVE,
        Permission.POLICY_READ,
        Permission.MONITORING_READ,
        Permission.HARMONIZATION_READ,
        Permission.VENDOR_READ,
        Permission.INCIDENT_READ,
        Permission.QUANTRISK_READ,
        Permission.RESILIENCE_READ,
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
        Permission.REMEDIATION_MANAGE,
        Permission.REMEDIATION_APPROVE,
        Permission.REMEDIATION_EXECUTE,
        Permission.REMEDIATION_VERIFY,
        Permission.EXCEPTION_READ,
        Permission.EXCEPTION_APPROVE,
        Permission.AUDIT_READ,
        Permission.AUDIT_REVIEW,
        Permission.AUDIT_APPROVE,
        Permission.AUDIT_CLOSE,
        Permission.POLICY_READ,
        Permission.MONITORING_READ,
        Permission.MONITORING_MANAGE,
        Permission.MONITORING_ALERT_ACTION,
        Permission.HARMONIZATION_READ,
        Permission.HARMONIZATION_MANAGE,
        Permission.HARMONIZATION_EXECUTE,
        Permission.VENDOR_READ,
        Permission.VENDOR_MANAGE,
        Permission.VENDOR_APPROVE,
        Permission.VENDOR_RISK_MANAGE,
        Permission.INCIDENT_READ,
        Permission.INCIDENT_MANAGE,
        Permission.INCIDENT_DISCLOSE,
        Permission.INCIDENT_CLOSE,
        Permission.QUANTRISK_READ,
        Permission.QUANTRISK_MANAGE,
        Permission.QUANTRISK_EXECUTE,
        Permission.QUANTRISK_APPROVE,
        Permission.RESILIENCE_READ,
        Permission.RESILIENCE_MANAGE,
        Permission.RESILIENCE_APPROVE,
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
        Permission.MONITORING_READ,
        Permission.HARMONIZATION_READ,
        Permission.VENDOR_READ,
        Permission.INCIDENT_READ,
        Permission.QUANTRISK_READ,
        Permission.RESILIENCE_READ,
    },
}


def has_permission(role: RoleEnum, permission: Permission) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms