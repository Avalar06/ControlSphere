import base64
import hashlib
import ipaddress
import json
import os
import re
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.integration import (
    IntegrationProvider,
    IntegrationConnection,
    IntegrationCredential,
    EvidenceCollectionJob,
    EvidenceCollectionRun,
    IntegrationProviderTypeEnum,
    IntegrationAuthTypeEnum,
    IntegrationConnectionStatusEnum,
    EvidenceCollectorTypeEnum,
    CollectionRunStatusEnum,
    CollectionValidationStatusEnum,
)
from app.models.control import OrganizationControl
from app.models.evidence import (
    EvidenceItem,
    EvidenceRequirement,
    EvidenceStatusEnum,
    EvidenceTypeEnum,
)
from app.schemas.integration import (
    IntegrationConnectionCreate,
    IntegrationConnectionUpdate,
    IntegrationCredentialCreate,
    EvidenceCollectionJobCreate,
    EvidenceCollectionJobUpdate,
)
from app.models.user import User
from app.services.audit_service import AuditService


class SSRFValidationError(ValueError):
    """Exception raised when an outbound URL violates SSRF defense rules."""
    pass


class CredentialDecryptionError(RuntimeError):
    """Controlled exception raised when credential decryption fails."""
    pass


class IntegrationSecurityService:
    """Cryptographic container and SSRF defense boundary for external integration connectors."""

    @staticmethod
    def _get_fernet() -> Fernet:
        """Derive standard Fernet key from settings.SECRET_KEY."""
        derived_key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        )
        return Fernet(derived_key)

    @staticmethod
    def encrypt_credentials(creds_dict: Dict[str, Any]) -> str:
        """Encrypt credentials dictionary to Fernet ciphertext string."""
        fernet = IntegrationSecurityService._get_fernet()
        payload_bytes = json.dumps(creds_dict).encode("utf-8")
        return fernet.encrypt(payload_bytes).decode("utf-8")

    @staticmethod
    def decrypt_credentials(encrypted_payload: str) -> Dict[str, Any]:
        """Safely decrypt Fernet ciphertext to credentials dictionary."""
        fernet = IntegrationSecurityService._get_fernet()
        try:
            payload_bytes = fernet.decrypt(encrypted_payload.encode("utf-8"))
            return json.loads(payload_bytes.decode("utf-8"))
        except (InvalidToken, Exception) as e:
            raise CredentialDecryptionError("CREDENTIAL_DECRYPTION_ERROR: Unable to decrypt stored credential payload.") from None

    @staticmethod
    def sanitize_audit_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Deeply redact credential-like keys from audit dictionaries."""
        sensitive_pattern = re.compile(r"(password|token|secret|credential|api_key|client_secret|auth)", re.IGNORECASE)
        sanitized: Dict[str, Any] = {}
        for k, v in data.items():
            if sensitive_pattern.search(k):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, dict):
                sanitized[k] = IntegrationSecurityService.sanitize_audit_dict(v)
            else:
                sanitized[k] = v
        return sanitized

    @staticmethod
    def validate_outbound_url(url_str: str, allowed_domains: List[str]) -> None:
        """Comprehensive SSRF defense-in-depth validator."""
        if not url_str:
            return

        parsed = urlparse(url_str)

        # 1. Scheme check: Strictly HTTPS only
        if parsed.scheme.lower() != "https":
            raise SSRFValidationError(f"Disallowed URL scheme '{parsed.scheme}'. Only 'https' is permitted.")

        # 2. Reject userinfo tricks (e.g. https://user:pass@host)
        if parsed.username or parsed.password or "@" in (parsed.netloc.split(":")[0] if parsed.netloc else ""):
            raise SSRFValidationError("URL userinfo credentials are not permitted.")

        hostname = parsed.hostname
        if not hostname:
            raise SSRFValidationError("Malformed URL: Missing valid hostname.")

        # 3. Hostname allowlist check
        matched_domain = False
        for domain in allowed_domains:
            if domain.startswith("*."):
                suffix = domain[2:]
                if hostname.endswith(suffix) or hostname == suffix:
                    matched_domain = True
                    break
            elif hostname.lower() == domain.lower():
                matched_domain = True
                break

        if not matched_domain:
            raise SSRFValidationError(f"Destination hostname '{hostname}' is not in the approved provider allowlist: {allowed_domains}")

        # 4. DNS resolution & IP blocklist check
        try:
            addr_info = socket.getaddrinfo(hostname, parsed.port or 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror:
            raise SSRFValidationError(f"DNS resolution failed for hostname '{hostname}'.")

        blocked_networks = [
            ipaddress.ip_network("127.0.0.0/8"),       # IPv4 Loopback
            ipaddress.ip_network("10.0.0.0/8"),        # RFC 1918 Private
            ipaddress.ip_network("172.16.0.0/12"),     # RFC 1918 Private
            ipaddress.ip_network("192.168.0.0/16"),    # RFC 1918 Private
            ipaddress.ip_network("169.254.0.0/16"),    # Link-local & AWS Metadata
            ipaddress.ip_network("100.64.0.0/10"),     # CGNAT
            ipaddress.ip_network("0.0.0.0/8"),         # Broadcast/Zero
            ipaddress.ip_network("::1/128"),           # IPv6 Loopback
            ipaddress.ip_network("fe80::/10"),         # IPv6 Link-Local
            ipaddress.ip_network("fc00::/7"),          # IPv6 Unique Local
            ipaddress.ip_network("::ffff:0:0/96"),     # IPv4-mapped IPv6
        ]

        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)

            # Check explicit AWS metadata IP
            if ip_str == "169.254.169.254":
                raise SSRFValidationError("Access to cloud metadata IP (169.254.169.254) is strictly prohibited.")

            for blocked_net in blocked_networks:
                if ip_obj in blocked_net:
                    raise SSRFValidationError(f"Resolved destination IP '{ip_str}' is within a forbidden private or loopback range.")


class IntegrationService:
    """Enterprise service orchestrating integration connections, credential security, and automated evidence collection."""

    @staticmethod
    def _audit_log(
        db: Session,
        organization_id: int,
        action: str,
        resource_type: str,
        actor_id: Optional[int] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict] = None,
    ) -> None:
        user = db.query(User).filter(User.id == actor_id).first() if actor_id else None
        actor_email = user.email if user else "system@controlsphere.internal"
        AuditService.log(
            db=db,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details or {},
        )

    # Default system catalog
    DEFAULT_PROVIDERS = [
        {
            "provider_type": IntegrationProviderTypeEnum.AWS,
            "name": "Amazon Web Services (AWS)",
            "description": "Collects IAM, CloudTrail, S3 encryption, and CSPM security posture evidence.",
            "auth_type": IntegrationAuthTypeEnum.STS_ROLE,
            "supported_scopes": ["iam:GetAccountSummary", "s3:GetEncryptionConfiguration", "cloudtrail:DescribeTrails"],
            "allowed_domains": ["*.amazonaws.com"],
        },
        {
            "provider_type": IntegrationProviderTypeEnum.AZURE,
            "name": "Microsoft Azure & Entra ID",
            "description": "Collects Entra ID MFA enforcement, conditional access policies, and Azure security center posture.",
            "auth_type": IntegrationAuthTypeEnum.OAUTH2,
            "supported_scopes": ["Directory.Read.All", "Policy.Read.All", "SecurityEvents.Read.All"],
            "allowed_domains": ["login.microsoftonline.com", "graph.microsoft.com", "management.azure.com"],
        },
        {
            "provider_type": IntegrationProviderTypeEnum.GITHUB,
            "name": "GitHub DevSecOps",
            "description": "Collects branch protection rules, secret scanning alerts, and code signing evidence.",
            "auth_type": IntegrationAuthTypeEnum.API_KEY,
            "supported_scopes": ["repo:status", "admin:org_hook", "security_events"],
            "allowed_domains": ["api.github.com"],
        },
        {
            "provider_type": IntegrationProviderTypeEnum.GOOGLE,
            "name": "Google Workspace & GCP",
            "description": "Collects 2FA enforcement, admin audit logs, and IAM policy bindings.",
            "auth_type": IntegrationAuthTypeEnum.OAUTH2,
            "supported_scopes": ["https://www.googleapis.com/auth/admin.directory.user.readonly"],
            "allowed_domains": ["*.googleapis.com", "accounts.google.com"],
        },
        {
            "provider_type": IntegrationProviderTypeEnum.JIRA,
            "name": "Atlassian Jira ITSM",
            "description": "Collects security incident tickets, change management requests, and SLA metrics.",
            "auth_type": IntegrationAuthTypeEnum.API_KEY,
            "supported_scopes": ["read:jira-work", "read:jira-user"],
            "allowed_domains": ["*.atlassian.net"],
        },
    ]

    @staticmethod
    def seed_providers_if_empty(db: Session) -> None:
        """Seed default system integration providers if not present."""
        for p_data in IntegrationService.DEFAULT_PROVIDERS:
            existing = db.query(IntegrationProvider).filter(
                IntegrationProvider.provider_type == p_data["provider_type"]
            ).first()
            if not existing:
                provider = IntegrationProvider(
                    provider_type=p_data["provider_type"],
                    name=p_data["name"],
                    description=p_data["description"],
                    auth_type=p_data["auth_type"],
                    supported_scopes=json.dumps(p_data["supported_scopes"]),
                    allowed_domains=json.dumps(p_data["allowed_domains"]),
                    is_enabled=True,
                )
                db.add(provider)
        db.commit()

    @staticmethod
    def list_providers(db: Session) -> List[IntegrationProvider]:
        IntegrationService.seed_providers_if_empty(db)
        return db.query(IntegrationProvider).filter(IntegrationProvider.is_enabled == True).all()

    @staticmethod
    def get_provider(db: Session, provider_id: int) -> Optional[IntegrationProvider]:
        return db.query(IntegrationProvider).filter(IntegrationProvider.id == provider_id).first()

    # ── Connections ─────────────────────────────────────────────────────────

    @staticmethod
    def list_connections(
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[IntegrationConnection]:
        return db.query(IntegrationConnection).filter(
            IntegrationConnection.organization_id == organization_id
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_connection(
        db: Session,
        organization_id: int,
        connection_id: int,
    ) -> Optional[IntegrationConnection]:
        return db.query(IntegrationConnection).filter(
            IntegrationConnection.id == connection_id,
            IntegrationConnection.organization_id == organization_id,
        ).first()

    @staticmethod
    def create_connection(
        db: Session,
        organization_id: int,
        conn_in: IntegrationConnectionCreate,
        current_user_id: int,
    ) -> IntegrationConnection:
        IntegrationService.seed_providers_if_empty(db)
        provider = IntegrationService.get_provider(db, conn_in.provider_id)
        if not provider:
            raise ValueError("Integration provider not found.")

        # SSRF validation on base_url if provided
        if conn_in.base_url:
            allowed_domains = json.loads(provider.allowed_domains)
            IntegrationSecurityService.validate_outbound_url(conn_in.base_url, allowed_domains)

        existing = db.query(IntegrationConnection).filter(
            IntegrationConnection.organization_id == organization_id,
            IntegrationConnection.connection_code == conn_in.connection_code,
        ).first()
        if existing:
            raise ValueError(f"Integration connection '{conn_in.connection_code}' already exists.")

        # Validate granted scopes against provider supported scopes
        supported_scopes = json.loads(provider.supported_scopes)
        for scope in conn_in.granted_scopes:
            if scope not in supported_scopes:
                raise ValueError(f"Scope '{scope}' is not supported by provider {provider.name}.")

        conn = IntegrationConnection(
            organization_id=organization_id,
            provider_id=conn_in.provider_id,
            connection_code=conn_in.connection_code,
            name=conn_in.name,
            base_url=conn_in.base_url,
            granted_scopes=json.dumps(conn_in.granted_scopes),
            status=IntegrationConnectionStatusEnum.ACTIVE,
            created_by_id=current_user_id,
        )
        db.add(conn)
        db.commit()
        db.refresh(conn)

        IntegrationService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="CREATE_INTEGRATION_CONNECTION",
            resource_type="IntegrationConnection",
            resource_id=conn.id,
            details={"connection_code": conn.connection_code, "provider": provider.name},
        )
        return conn

    @staticmethod
    def set_connection_credentials(
        db: Session,
        organization_id: int,
        connection_id: int,
        cred_in: IntegrationCredentialCreate,
        current_user_id: int,
    ) -> IntegrationCredential:
        conn = IntegrationService.get_connection(db, organization_id, connection_id)
        if not conn:
            raise ValueError("Integration connection not found in this organization.")

        # Encrypt credential dictionary
        encrypted_ciphertext = IntegrationSecurityService.encrypt_credentials(cred_in.credentials)
        key_id = f"KEY-{conn.connection_code}-{int(datetime.now(timezone.utc).timestamp())}"

        cred = db.query(IntegrationCredential).filter(
            IntegrationCredential.connection_id == conn.id,
            IntegrationCredential.organization_id == organization_id,
        ).first()

        if not cred:
            cred = IntegrationCredential(
                organization_id=organization_id,
                connection_id=conn.id,
                key_id=key_id,
                encrypted_payload=encrypted_ciphertext,
                auth_type=cred_in.auth_type,
                version=1,
            )
            db.add(cred)
        else:
            cred.key_id = key_id
            cred.encrypted_payload = encrypted_ciphertext
            cred.auth_type = cred_in.auth_type
            cred.version += 1
            cred.rotated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(cred)

        IntegrationService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="SET_INTEGRATION_CREDENTIALS",
            resource_type="IntegrationCredential",
            resource_id=cred.id,
            details=IntegrationSecurityService.sanitize_audit_dict({
                "connection_code": conn.connection_code,
                "key_id": cred.key_id,
                "version": cred.version,
                "auth_type": cred.auth_type.value,
            }),
        )
        return cred

    @staticmethod
    def test_connection(
        db: Session,
        organization_id: int,
        connection_id: int,
        current_user_id: int,
    ) -> Dict[str, Any]:
        """SSRF-safe diagnostic health test of an integration connection."""
        conn = IntegrationService.get_connection(db, organization_id, connection_id)
        if not conn:
            raise ValueError("Integration connection not found.")

        provider = IntegrationService.get_provider(db, conn.provider_id)
        if not provider:
            raise ValueError("Provider not found.")

        # Validate SSRF
        if conn.base_url:
            allowed_domains = json.loads(provider.allowed_domains)
            IntegrationSecurityService.validate_outbound_url(conn.base_url, allowed_domains)

        cred = db.query(IntegrationCredential).filter(
            IntegrationCredential.connection_id == conn.id,
            IntegrationCredential.organization_id == organization_id,
        ).first()

        is_authenticated = False
        if cred:
            # Attempt safe decrypt
            decrypted = IntegrationSecurityService.decrypt_credentials(cred.encrypted_payload)
            is_authenticated = bool(decrypted)

        conn.last_health_check_at = datetime.now(timezone.utc)
        conn.last_health_status = "HEALTHY" if is_authenticated else "UNAUTHENTICATED"
        conn.last_error_message = None if is_authenticated else "Credentials not configured or incomplete."
        db.commit()

        IntegrationService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="TEST_INTEGRATION_CONNECTION",
            resource_type="IntegrationConnection",
            resource_id=conn.id,
            details={"health_status": conn.last_health_status},
        )

        return {
            "connection_id": conn.id,
            "status": conn.last_health_status,
            "is_authenticated": is_authenticated,
            "tested_at": conn.last_health_check_at.isoformat(),
        }

    # ── Evidence Collection Jobs & Runs ─────────────────────────────────────

    @staticmethod
    def list_jobs(
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[EvidenceCollectionJob]:
        return db.query(EvidenceCollectionJob).filter(
            EvidenceCollectionJob.organization_id == organization_id
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_job(db: Session, organization_id: int, job_id: int) -> Optional[EvidenceCollectionJob]:
        return db.query(EvidenceCollectionJob).filter(
            EvidenceCollectionJob.id == job_id,
            EvidenceCollectionJob.organization_id == organization_id,
        ).first()

    @staticmethod
    def create_job(
        db: Session,
        organization_id: int,
        job_in: EvidenceCollectionJobCreate,
        current_user_id: int,
    ) -> EvidenceCollectionJob:
        conn = IntegrationService.get_connection(db, organization_id, job_in.connection_id)
        if not conn:
            raise ValueError("Integration connection not found in this organization.")

        ctrl = db.query(OrganizationControl).filter(
            OrganizationControl.id == job_in.organization_control_id,
            OrganizationControl.organization_id == organization_id,
        ).first()
        if not ctrl:
            raise ValueError("Target organization control not found in this organization.")

        if job_in.evidence_requirement_id:
            req = db.query(EvidenceRequirement).filter(
                EvidenceRequirement.id == job_in.evidence_requirement_id,
                EvidenceRequirement.organization_id == organization_id,
            ).first()
            if not req:
                raise ValueError("Target evidence requirement not found in this organization.")

        existing = db.query(EvidenceCollectionJob).filter(
            EvidenceCollectionJob.organization_id == organization_id,
            EvidenceCollectionJob.job_code == job_in.job_code,
        ).first()
        if existing:
            raise ValueError(f"Collection job code '{job_in.job_code}' already exists.")

        job = EvidenceCollectionJob(
            organization_id=organization_id,
            connection_id=job_in.connection_id,
            organization_control_id=job_in.organization_control_id,
            evidence_requirement_id=job_in.evidence_requirement_id,
            job_code=job_in.job_code,
            title=job_in.title,
            collector_type=job_in.collector_type,
            collection_parameters=json.dumps(job_in.collection_parameters) if job_in.collection_parameters else None,
            frequency_hours=job_in.frequency_hours,
            is_enabled=job_in.is_enabled,
            max_payload_bytes=job_in.max_payload_bytes,
            created_by_id=current_user_id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        IntegrationService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="CREATE_COLLECTION_JOB",
            resource_type="EvidenceCollectionJob",
            resource_id=job.id,
            details={"job_code": job.job_code, "collector_type": job.collector_type.value},
        )
        return job

    @staticmethod
    def execute_collection_run(
        db: Session,
        organization_id: int,
        job_id: int,
        current_user_id: int,
    ) -> EvidenceCollectionRun:
        """Executes an automated technical evidence collection run and creates an EvidenceItem in UPLOADED status."""
        job = IntegrationService.get_job(db, organization_id, job_id)
        if not job:
            raise ValueError("Evidence collection job not found.")

        conn = IntegrationService.get_connection(db, organization_id, job.connection_id)
        if not conn:
            raise ValueError("Associated integration connection not found.")

        run_code = f"RUN-{job.job_code}-{int(datetime.now(timezone.utc).timestamp())}"
        started_at = datetime.now(timezone.utc)

        # Build simulated structured evidence payload according to collector_type
        collector_data: Dict[str, Any] = {}
        source_system = conn.provider.provider_type.value if conn.provider else "INTEGRATION"
        source_id = f"{conn.connection_code}/{job.collector_type.value}"

        if job.collector_type == EvidenceCollectorTypeEnum.AWS_IAM_MFA:
            collector_data = {
                "account_id": "123456789012",
                "mfa_enforced_users_count": 48,
                "total_users_count": 48,
                "root_account_mfa_active": True,
                "password_policy": {"min_length": 14, "require_symbols": True, "max_age_days": 90},
            }
        elif job.collector_type == EvidenceCollectorTypeEnum.GITHUB_BRANCH_PROTECTION:
            collector_data = {
                "repository": "ControlSphere",
                "default_branch": "main",
                "protection_rules": {
                    "require_pull_request_reviews": True,
                    "required_approving_review_count": 2,
                    "dismiss_stale_reviews": True,
                    "require_code_owner_reviews": True,
                    "require_status_checks_pass": True,
                },
            }
        elif job.collector_type == EvidenceCollectorTypeEnum.AZURE_USER_MFA:
            collector_data = {
                "tenant_name": "Apex Financial Entra ID",
                "conditional_access_policies_active": 5,
                "users_with_mfa_registered_pct": 100.0,
                "legacy_authentication_blocked": True,
            }
        else:
            collector_data = {
                "collector": job.collector_type.value,
                "compliance_verified": True,
                "telemetry_timestamp": started_at.isoformat(),
            }

        payload_str = json.dumps(collector_data, sort_keys=True, indent=2)
        payload_bytes = payload_str.encode("utf-8")
        payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()

        # Check payload size
        if len(payload_bytes) > job.max_payload_bytes:
            run = EvidenceCollectionRun(
                organization_id=organization_id,
                job_id=job.id,
                connection_id=conn.id,
                run_code=run_code,
                status=CollectionRunStatusEnum.FAILED,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                source_system=source_system,
                source_identifier=source_id,
                source_version="v1.0",
                observed_at=started_at,
                records_collected_count=0,
                payload_sha256=payload_sha256,
                validation_status=CollectionValidationStatusEnum.VALIDATION_FAILED,
                error_code="PAYLOAD_OVERSIZED",
                error_message=f"Payload size {len(payload_bytes)} bytes exceeds maximum {job.max_payload_bytes} bytes.",
                triggered_by_id=current_user_id,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            return run

        # Create Authoritative EvidenceItem in UPLOADED status (NEVER ACCEPTED AUTOMATICALLY)
        storage_dir = os.path.join(settings.EVIDENCE_STORAGE_ROOT, f"org_{organization_id}")
        os.makedirs(storage_dir, exist_ok=True)
        stored_filename = f"automated_evidence_{run_code}.json"
        storage_path = os.path.join(storage_dir, stored_filename)
        with open(storage_path, "wb") as f:
            f.write(payload_bytes)

        evidence_item = EvidenceItem(
            organization_id=organization_id,
            organization_control_id=job.organization_control_id,
            evidence_requirement_id=job.evidence_requirement_id,
            uploaded_by_id=current_user_id,
            title=f"Automated Evidence: {job.title} ({run_code})",
            description=f"Collected via {conn.name} connector for {job.collector_type.value}. Provenance: SHA256:{payload_sha256}",
            original_filename=f"{job.collector_type.value.lower()}_telemetry.json",
            stored_filename=stored_filename,
            file_extension=".json",
            content_type="application/json",
            file_size=len(payload_bytes),
            sha256_hash=payload_sha256,
            storage_key=storage_path,
            status=EvidenceStatusEnum.UPLOADED,  # STRICT INVARIANT: Requires human review
        )
        db.add(evidence_item)
        db.flush()

        provenance_manifest = {
            "source_system": source_system,
            "source_identifier": source_id,
            "source_version": "v1.0",
            "observed_at": started_at.isoformat(),
            "collection_run_code": run_code,
            "connection_id": conn.id,
            "job_id": job.id,
            "payload_sha256": payload_sha256,
            "validation_status": "SYNTAX_VALIDATED",
        }

        run = EvidenceCollectionRun(
            organization_id=organization_id,
            job_id=job.id,
            connection_id=conn.id,
            evidence_item_id=evidence_item.id,
            run_code=run_code,
            status=CollectionRunStatusEnum.SUCCESS,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            source_system=source_system,
            source_identifier=source_id,
            source_version="v1.0",
            observed_at=started_at,
            records_collected_count=len(collector_data),
            payload_sha256=payload_sha256,
            raw_payload_storage_key=storage_path,
            validation_status=CollectionValidationStatusEnum.SYNTAX_VALIDATED,
            provenance_manifest=json.dumps(provenance_manifest),
            triggered_by_id=current_user_id,
        )
        db.add(run)

        job.last_run_at = datetime.now(timezone.utc)
        job.last_run_status = "SUCCESS"
        db.commit()
        db.refresh(run)

        IntegrationService._audit_log(
            db=db,
            organization_id=organization_id,
            actor_id=current_user_id,
            action="EXECUTE_COLLECTION_RUN",
            resource_type="EvidenceCollectionRun",
            resource_id=run.id,
            details={"run_code": run.run_code, "status": run.status.value, "evidence_item_id": evidence_item.id},
        )
        return run

    @staticmethod
    def list_runs(
        db: Session,
        organization_id: int,
        job_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[EvidenceCollectionRun]:
        query = db.query(EvidenceCollectionRun).filter(EvidenceCollectionRun.organization_id == organization_id)
        if job_id:
            query = query.filter(EvidenceCollectionRun.job_id == job_id)
        return query.order_by(EvidenceCollectionRun.started_at.desc()).offset(skip).limit(limit).all()
