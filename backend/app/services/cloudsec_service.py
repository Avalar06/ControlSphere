from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cloudsec import (
    BenchmarkFrameworkEnum,
    BlastRadiusBandEnum,
    CloudAsset,
    CloudAssetTypeEnum,
    CloudBenchmarkRule,
    CloudConfigurationDrift,
    CloudCriticalityEnum,
    CloudEnvironmentEnum,
    CloudIAMBlastRadius,
    CloudLifecycleStateEnum,
    CloudPostureStatusEnum,
    CloudProviderEnum,
    CloudSecurityBenchmark,
    CloudSecurityFinding,
    DataAccessScopeEnum,
    DriftSeverityEnum,
    DriftStatusEnum,
    EvaluationStatusEnum,
    RuleSeverityEnum,
)
from app.models.control import OrganizationControl
from app.models.remediation import RemediationPlan
from app.models.supply_chain import SoftwareProduct
from app.models.user import User
from app.schemas.cloudsec import (
    CloudAssetCreate,
    CloudAssetStatusUpdate,
    CloudAssetUpdate,
    CloudBenchmarkRuleCreate,
    CloudConfigurationDriftCreate,
    CloudIAMBlastRadiusCreate,
    CloudIAMBlastRadiusPreviewRequest,
    CloudIAMBlastRadiusPreviewResponse,
    CloudPostureSummaryResponse,
    CloudSecurityBenchmarkCreate,
    CloudSecurityFindingCreate,
)
from app.services.audit_service import AuditService


class CloudSecService:
    """Authoritative service for Phase 18: CLOUDSEC-GRC."""

    @staticmethod
    def _audit_log(
        db: Session,
        organization_id: int,
        action: str,
        resource_type: str,
        actor_id: Optional[int] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict] = None,
        user_id: Optional[int] = None,
    ) -> None:
        effective_user_id = actor_id if actor_id is not None else user_id
        user = db.query(User).filter(User.id == effective_user_id).first() if effective_user_id else None
        actor_email = user.email if user else "system@control-sphere.internal"
        AuditService.log(
            db=db,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            actor_email=actor_email,
            actor_id=effective_user_id,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details or {},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Mathematical Formulas
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_asset_posture_score(
        findings: List[CloudSecurityFinding], is_internet_facing: bool
    ) -> float:
        """
        Calculates authoritative Cloud Posture Score (0.00 to 100.00).
        CPS = 100 - min(100, sum(w(finding.severity) * internet_multiplier))
        """
        severity_weights = {
            RuleSeverityEnum.CRITICAL: 25.0,
            RuleSeverityEnum.HIGH: 15.0,
            RuleSeverityEnum.MEDIUM: 8.0,
            RuleSeverityEnum.LOW: 3.0,
        }
        internet_multiplier = 1.3 if is_internet_facing else 1.0

        total_penalty = 0.0
        for f in findings:
            if f.evaluation_status == EvaluationStatusEnum.FAILED:
                weight = severity_weights.get(f.severity, 10.0)
                total_penalty += weight * internet_multiplier

        score = max(0.00, min(100.00, 100.00 - total_penalty))
        return round(float(score), 2)

    @staticmethod
    def calculate_iam_blast_radius(
        effective_permissions_count: int,
        admin_privilege_granted: bool,
        cross_account_access: bool,
        data_access_scope: DataAccessScopeEnum,
    ) -> Tuple[float, BlastRadiusBandEnum, Dict[str, float]]:
        """
        Calculates authoritative IAM Blast Radius Index (0.00 to 100.00).
        BRI = clamp((P * 1.5) + (Admin ? 50 : 0) + (CrossAccount ? 20 : 0) + DataScopePenalty, 0, 100)
        """
        perm_score = min(30.0, float(effective_permissions_count) * 1.5)
        admin_penalty = 50.0 if admin_privilege_granted else 0.0
        cross_account_penalty = 20.0 if cross_account_access else 0.0

        scope_penalties = {
            DataAccessScopeEnum.FULL_DATASTORE: 30.0,
            DataAccessScopeEnum.RESTRICTED_READ: 10.0,
            DataAccessScopeEnum.METADATA_ONLY: 0.0,
        }
        scope_penalty = scope_penalties.get(data_access_scope, 10.0)

        raw_index = perm_score + admin_penalty + cross_account_penalty + scope_penalty
        blast_radius_index = max(0.00, min(100.00, float(raw_index)))
        blast_radius_index = round(blast_radius_index, 2)

        if blast_radius_index >= 80.0:
            band = BlastRadiusBandEnum.CRITICAL
        elif blast_radius_index >= 50.0:
            band = BlastRadiusBandEnum.HIGH
        elif blast_radius_index >= 25.0:
            band = BlastRadiusBandEnum.MODERATE
        else:
            band = BlastRadiusBandEnum.LOW

        breakdown = {
            "permissions_component": perm_score,
            "admin_privilege_penalty": admin_penalty,
            "cross_account_penalty": cross_account_penalty,
            "data_scope_penalty": scope_penalty,
        }

        return blast_radius_index, band, breakdown

    @staticmethod
    def calculate_drift_score(severity: DriftSeverityEnum) -> float:
        """Determines deterministic drift risk score based on severity."""
        scores = {
            DriftSeverityEnum.CRITICAL: 90.00,
            DriftSeverityEnum.HIGH: 70.00,
            DriftSeverityEnum.MEDIUM: 40.00,
            DriftSeverityEnum.LOW: 15.00,
        }
        return scores.get(severity, 50.00)

    # ─────────────────────────────────────────────────────────────────────────
    # Cloud Assets
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create_asset(
        cls, db: Session, org_id: int, user_id: int, data: CloudAssetCreate
    ) -> CloudAsset:
        # Check duplicate code or ARN within tenant
        existing = (
            db.query(CloudAsset)
            .filter(
                CloudAsset.organization_id == org_id,
                (CloudAsset.asset_code == data.asset_code)
                | (CloudAsset.resource_arn == data.resource_arn),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cloud Asset with code '{data.asset_code}' or ARN already exists in tenant.",
            )

        # Validate cross-module references if supplied
        if data.software_product_id:
            prod = (
                db.query(SoftwareProduct)
                .filter(
                    SoftwareProduct.id == data.software_product_id,
                    SoftwareProduct.organization_id == org_id,
                )
                .first()
            )
            if not prod:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Software Product #{data.software_product_id} not found in tenant.",
                )

        if data.remediation_plan_id:
            plan = (
                db.query(RemediationPlan)
                .filter(
                    RemediationPlan.id == data.remediation_plan_id,
                    RemediationPlan.organization_id == org_id,
                )
                .first()
            )
            if not plan:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Remediation Plan #{data.remediation_plan_id} not found in tenant.",
                )

        asset = CloudAsset(
            organization_id=org_id,
            asset_code=data.asset_code,
            provider=data.provider,
            account_id=data.account_id,
            region=data.region,
            resource_type=data.resource_type,
            resource_arn=data.resource_arn,
            resource_name=data.resource_name,
            environment=data.environment,
            criticality=data.criticality,
            posture_status=CloudPostureStatusEnum.COMPLIANT,
            posture_score=100.00,
            blast_radius_score=0.00,
            lifecycle_state=CloudLifecycleStateEnum.ACTIVE,
            is_internet_facing=data.is_internet_facing,
            encryption_enabled=data.encryption_enabled,
            owner_id=user_id,
            software_product_id=data.software_product_id,
            remediation_plan_id=data.remediation_plan_id,
            tags=data.tags,
            configuration_metadata=data.configuration_metadata,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="cloudsec.asset.create",
            resource_type="CloudAsset",
            resource_id=asset.id,
            details={"asset_code": asset.asset_code, "provider": asset.provider.value},
        )
        return asset

    @classmethod
    def get_asset(cls, db: Session, org_id: int, asset_id: int) -> CloudAsset:
        asset = (
            db.query(CloudAsset)
            .filter(
                CloudAsset.id == asset_id,
                CloudAsset.organization_id == org_id,
            )
            .first()
        )
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cloud Asset #{asset_id} not found.",
            )
        return asset

    @classmethod
    def list_assets(
        cls,
        db: Session,
        org_id: int,
        provider: Optional[CloudProviderEnum] = None,
        environment: Optional[CloudEnvironmentEnum] = None,
        posture_status: Optional[CloudPostureStatusEnum] = None,
        lifecycle_state: Optional[CloudLifecycleStateEnum] = None,
    ) -> List[CloudAsset]:
        q = db.query(CloudAsset).filter(CloudAsset.organization_id == org_id)
        if provider:
            q = q.filter(CloudAsset.provider == provider)
        if environment:
            q = q.filter(CloudAsset.environment == environment)
        if posture_status:
            q = q.filter(CloudAsset.posture_status == posture_status)
        if lifecycle_state:
            q = q.filter(CloudAsset.lifecycle_state == lifecycle_state)
        return q.order_by(CloudAsset.created_at.desc()).all()

    @classmethod
    def update_asset(
        cls, db: Session, org_id: int, user_id: int, asset_id: int, data: CloudAssetUpdate
    ) -> CloudAsset:
        asset = cls.get_asset(db, org_id, asset_id)
        if asset.lifecycle_state == CloudLifecycleStateEnum.DECOMMISSIONED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decommissioned cloud assets are immutable and cannot be updated.",
            )

        if data.software_product_id is not None:
            if data.software_product_id > 0:
                prod = (
                    db.query(SoftwareProduct)
                    .filter(
                        SoftwareProduct.id == data.software_product_id,
                        SoftwareProduct.organization_id == org_id,
                    )
                    .first()
                )
                if not prod:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Software Product #{data.software_product_id} not found in tenant.",
                    )
                asset.software_product_id = data.software_product_id
            else:
                asset.software_product_id = None

        if data.remediation_plan_id is not None:
            if data.remediation_plan_id > 0:
                plan = (
                    db.query(RemediationPlan)
                    .filter(
                        RemediationPlan.id == data.remediation_plan_id,
                        RemediationPlan.organization_id == org_id,
                    )
                    .first()
                )
                if not plan:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Remediation Plan #{data.remediation_plan_id} not found in tenant.",
                    )
                asset.remediation_plan_id = data.remediation_plan_id
            else:
                asset.remediation_plan_id = None

        if data.resource_name is not None:
            asset.resource_name = data.resource_name
        if data.environment is not None:
            asset.environment = data.environment
        if data.criticality is not None:
            asset.criticality = data.criticality
        if data.is_internet_facing is not None:
            asset.is_internet_facing = data.is_internet_facing
        if data.encryption_enabled is not None:
            asset.encryption_enabled = data.encryption_enabled
        if data.tags is not None:
            asset.tags = data.tags
        if data.configuration_metadata is not None:
            asset.configuration_metadata = data.configuration_metadata

        # Recalculate posture score with new properties
        findings = (
            db.query(CloudSecurityFinding)
            .filter(
                CloudSecurityFinding.cloud_asset_id == asset.id,
                CloudSecurityFinding.organization_id == org_id,
            )
            .all()
        )
        asset.posture_score = cls.calculate_asset_posture_score(findings, asset.is_internet_facing)

        db.commit()
        db.refresh(asset)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="cloudsec.asset.update",
            resource_type="CloudAsset",
            resource_id=asset.id,
            details={"asset_code": asset.asset_code},
        )
        return asset

    @classmethod
    def update_asset_status(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        asset_id: int,
        status_update: CloudAssetStatusUpdate,
    ) -> CloudAsset:
        asset = cls.get_asset(db, org_id, asset_id)

        valid_transitions = {
            CloudLifecycleStateEnum.PROVISIONING: [
                CloudLifecycleStateEnum.ACTIVE,
                CloudLifecycleStateEnum.DECOMMISSIONED,
            ],
            CloudLifecycleStateEnum.ACTIVE: [
                CloudLifecycleStateEnum.MAINTENANCE,
                CloudLifecycleStateEnum.DECOMMISSIONED,
            ],
            CloudLifecycleStateEnum.MAINTENANCE: [
                CloudLifecycleStateEnum.ACTIVE,
                CloudLifecycleStateEnum.DECOMMISSIONED,
            ],
            CloudLifecycleStateEnum.DECOMMISSIONED: [],
        }

        current = asset.lifecycle_state
        target = status_update.lifecycle_state

        if target != current and target not in valid_transitions.get(current, []):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Illegal lifecycle transition from '{current.value}' to '{target.value}'.",
            )

        asset.lifecycle_state = target
        db.commit()
        db.refresh(asset)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="cloudsec.asset.status_change",
            resource_type="CloudAsset",
            resource_id=asset.id,
            details={"from": current.value, "to": target.value, "notes": status_update.notes},
        )
        return asset

    @classmethod
    def delete_asset(cls, db: Session, org_id: int, user_id: int, asset_id: int) -> bool:
        asset = cls.get_asset(db, org_id, asset_id)
        if asset.lifecycle_state == CloudLifecycleStateEnum.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active cloud assets cannot be directly deleted. Decommission the asset first.",
            )

        db.delete(asset)
        db.commit()

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="cloudsec.asset.delete",
            resource_type="CloudAsset",
            resource_id=asset_id,
            details={"asset_code": asset.asset_code},
        )
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Benchmarks & Rules
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create_benchmark(
        cls, db: Session, data: CloudSecurityBenchmarkCreate
    ) -> CloudSecurityBenchmark:
        existing = (
            db.query(CloudSecurityBenchmark)
            .filter(CloudSecurityBenchmark.benchmark_code == data.benchmark_code)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Benchmark code '{data.benchmark_code}' already exists.",
            )

        benchmark = CloudSecurityBenchmark(
            benchmark_code=data.benchmark_code,
            name=data.name,
            version=data.version,
            framework=data.framework,
            provider=data.provider,
            description=data.description,
            is_active=data.is_active,
            total_rules_count=0,
        )
        db.add(benchmark)
        db.commit()
        db.refresh(benchmark)
        return benchmark

    @classmethod
    def list_benchmarks(
        cls, db: Session, provider: Optional[CloudProviderEnum] = None
    ) -> List[CloudSecurityBenchmark]:
        q = db.query(CloudSecurityBenchmark)
        if provider:
            q = q.filter(CloudSecurityBenchmark.provider == provider)
        return q.order_by(CloudSecurityBenchmark.benchmark_code.asc()).all()

    @classmethod
    def create_rule(
        cls, db: Session, data: CloudBenchmarkRuleCreate
    ) -> CloudBenchmarkRule:
        benchmark = (
            db.query(CloudSecurityBenchmark)
            .filter(CloudSecurityBenchmark.id == data.benchmark_id)
            .first()
        )
        if not benchmark:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cloud Benchmark #{data.benchmark_id} not found.",
            )

        existing = (
            db.query(CloudBenchmarkRule)
            .filter(CloudBenchmarkRule.rule_code == data.rule_code)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Benchmark rule code '{data.rule_code}' already exists.",
            )

        rule = CloudBenchmarkRule(
            benchmark_id=data.benchmark_id,
            rule_code=data.rule_code,
            title=data.title,
            description=data.description,
            section=data.section,
            severity=data.severity,
            rationale=data.rationale,
            remediation_guidance=data.remediation_guidance,
            control_id=data.control_id,
        )
        db.add(rule)
        benchmark.total_rules_count += 1
        db.commit()
        db.refresh(rule)
        return rule

    @classmethod
    def list_rules(
        cls, db: Session, benchmark_id: Optional[int] = None
    ) -> List[CloudBenchmarkRule]:
        q = db.query(CloudBenchmarkRule)
        if benchmark_id:
            q = q.filter(CloudBenchmarkRule.benchmark_id == benchmark_id)
        return q.order_by(CloudBenchmarkRule.rule_code.asc()).all()

    # ─────────────────────────────────────────────────────────────────────────
    # Findings & Evaluations
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def record_finding(
        cls, db: Session, org_id: int, user_id: int, data: CloudSecurityFindingCreate
    ) -> CloudSecurityFinding:
        asset = cls.get_asset(db, org_id, data.cloud_asset_id)

        rule = (
            db.query(CloudBenchmarkRule)
            .filter(CloudBenchmarkRule.id == data.rule_id)
            .first()
        )
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Benchmark Rule #{data.rule_id} not found.",
            )

        if data.remediation_plan_id:
            plan = (
                db.query(RemediationPlan)
                .filter(
                    RemediationPlan.id == data.remediation_plan_id,
                    RemediationPlan.organization_id == org_id,
                )
                .first()
            )
            if not plan:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Remediation Plan #{data.remediation_plan_id} not found in tenant.",
                )

        existing = (
            db.query(CloudSecurityFinding)
            .filter(
                CloudSecurityFinding.organization_id == org_id,
                CloudSecurityFinding.finding_code == data.finding_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Finding code '{data.finding_code}' already exists in tenant.",
            )

        # Server-side risk score computation
        risk_weight = {
            RuleSeverityEnum.CRITICAL: 90.00,
            RuleSeverityEnum.HIGH: 70.00,
            RuleSeverityEnum.MEDIUM: 40.00,
            RuleSeverityEnum.LOW: 15.00,
        }.get(data.severity, 50.00)

        finding = CloudSecurityFinding(
            organization_id=org_id,
            finding_code=data.finding_code,
            cloud_asset_id=data.cloud_asset_id,
            rule_id=data.rule_id,
            evaluation_status=data.evaluation_status,
            severity=data.severity,
            risk_score=risk_weight,
            actual_value=data.actual_value,
            expected_value=data.expected_value,
            remediation_plan_id=data.remediation_plan_id,
        )
        db.add(finding)

        # Recalculate parent asset posture score
        all_findings = (
            db.query(CloudSecurityFinding)
            .filter(
                CloudSecurityFinding.cloud_asset_id == asset.id,
                CloudSecurityFinding.organization_id == org_id,
            )
            .all()
        )
        all_findings.append(finding)
        asset.posture_score = cls.calculate_asset_posture_score(all_findings, asset.is_internet_facing)
        if asset.posture_score < 70.00:
            asset.posture_status = CloudPostureStatusEnum.NON_COMPLIANT
        elif asset.posture_score < 100.00:
            asset.posture_status = CloudPostureStatusEnum.DEVIATED
        else:
            asset.posture_status = CloudPostureStatusEnum.COMPLIANT

        db.commit()
        db.refresh(finding)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="cloudsec.finding.record",
            resource_type="CloudSecurityFinding",
            resource_id=finding.id,
            details={"finding_code": finding.finding_code, "asset_id": asset.id},
        )
        return finding

    @classmethod
    def list_findings(
        cls,
        db: Session,
        org_id: int,
        asset_id: Optional[int] = None,
        evaluation_status: Optional[EvaluationStatusEnum] = None,
        severity: Optional[RuleSeverityEnum] = None,
    ) -> List[CloudSecurityFinding]:
        q = db.query(CloudSecurityFinding).filter(CloudSecurityFinding.organization_id == org_id)
        if asset_id:
            q = q.filter(CloudSecurityFinding.cloud_asset_id == asset_id)
        if evaluation_status:
            q = q.filter(CloudSecurityFinding.evaluation_status == evaluation_status)
        if severity:
            q = q.filter(CloudSecurityFinding.severity == severity)
        return q.order_by(CloudSecurityFinding.evaluated_at.desc()).all()

    # ─────────────────────────────────────────────────────────────────────────
    # Configuration Drift
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def record_drift(
        cls, db: Session, org_id: int, user_id: int, data: CloudConfigurationDriftCreate
    ) -> CloudConfigurationDrift:
        asset = cls.get_asset(db, org_id, data.cloud_asset_id)

        existing = (
            db.query(CloudConfigurationDrift)
            .filter(
                CloudConfigurationDrift.organization_id == org_id,
                CloudConfigurationDrift.drift_code == data.drift_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Drift event code '{data.drift_code}' already exists in tenant.",
            )

        drift_score = cls.calculate_drift_score(data.drift_severity)

        drift = CloudConfigurationDrift(
            organization_id=org_id,
            drift_code=data.drift_code,
            cloud_asset_id=data.cloud_asset_id,
            attribute_path=data.attribute_path,
            baseline_value=data.baseline_value,
            drifted_value=data.drifted_value,
            drift_severity=data.drift_severity,
            drift_score=drift_score,
            status=DriftStatusEnum.DETECTED,
        )
        db.add(drift)
        asset.posture_status = CloudPostureStatusEnum.DEVIATED

        db.commit()
        db.refresh(drift)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="cloudsec.drift.record",
            resource_type="CloudConfigurationDrift",
            resource_id=drift.id,
            details={"drift_code": drift.drift_code, "asset_id": asset.id},
        )
        return drift

    @classmethod
    def list_drifts(
        cls,
        db: Session,
        org_id: int,
        asset_id: Optional[int] = None,
        drift_status: Optional[DriftStatusEnum] = None,
    ) -> List[CloudConfigurationDrift]:
        q = db.query(CloudConfigurationDrift).filter(CloudConfigurationDrift.organization_id == org_id)
        if asset_id:
            q = q.filter(CloudConfigurationDrift.cloud_asset_id == asset_id)
        if drift_status:
            q = q.filter(CloudConfigurationDrift.status == drift_status)
        return q.order_by(CloudConfigurationDrift.detected_at.desc()).all()

    # ─────────────────────────────────────────────────────────────────────────
    # IAM Blast Radius
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def analyze_iam_blast_radius(
        cls, db: Session, org_id: int, user_id: int, data: CloudIAMBlastRadiusCreate
    ) -> CloudIAMBlastRadius:
        asset = cls.get_asset(db, org_id, data.cloud_asset_id)

        existing = (
            db.query(CloudIAMBlastRadius)
            .filter(
                CloudIAMBlastRadius.organization_id == org_id,
                CloudIAMBlastRadius.analysis_code == data.analysis_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Blast radius analysis code '{data.analysis_code}' already exists in tenant.",
            )

        blast_index, band, _ = cls.calculate_iam_blast_radius(
            data.effective_permissions_count,
            data.admin_privilege_granted,
            data.cross_account_access,
            data.data_access_scope,
        )

        analysis = CloudIAMBlastRadius(
            organization_id=org_id,
            analysis_code=data.analysis_code,
            cloud_asset_id=data.cloud_asset_id,
            iam_principal_arn=data.iam_principal_arn,
            effective_permissions_count=data.effective_permissions_count,
            admin_privilege_granted=data.admin_privilege_granted,
            cross_account_access=data.cross_account_access,
            data_access_scope=data.data_access_scope,
            blast_radius_index=blast_index,
            risk_band=band,
        )
        db.add(analysis)

        # Update parent asset blast radius score (max across active analyses)
        asset.blast_radius_score = max(float(asset.blast_radius_score), float(blast_index))

        db.commit()
        db.refresh(analysis)

        cls._audit_log(
            db=db,
            organization_id=org_id,
            actor_id=user_id,
            action="cloudsec.blast_radius.analyze",
            resource_type="CloudIAMBlastRadius",
            resource_id=analysis.id,
            details={"analysis_code": analysis.analysis_code, "score": float(blast_index)},
        )
        return analysis

    @classmethod
    def preview_iam_blast_radius(
        cls, data: CloudIAMBlastRadiusPreviewRequest
    ) -> CloudIAMBlastRadiusPreviewResponse:
        blast_index, band, breakdown = cls.calculate_iam_blast_radius(
            data.effective_permissions_count,
            data.admin_privilege_granted,
            data.cross_account_access,
            data.data_access_scope,
        )
        return CloudIAMBlastRadiusPreviewResponse(
            blast_radius_index=blast_index,
            risk_band=band,
            breakdown=breakdown,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Posture Summary
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def get_posture_summary(cls, db: Session, org_id: int) -> CloudPostureSummaryResponse:
        assets = db.query(CloudAsset).filter(CloudAsset.organization_id == org_id).all()
        findings = db.query(CloudSecurityFinding).filter(CloudSecurityFinding.organization_id == org_id).all()
        drifts = db.query(CloudConfigurationDrift).filter(CloudConfigurationDrift.organization_id == org_id).all()

        total_assets = len(assets)
        compliant = sum(1 for a in assets if a.posture_status == CloudPostureStatusEnum.COMPLIANT)
        non_compliant = sum(1 for a in assets if a.posture_status == CloudPostureStatusEnum.NON_COMPLIANT)
        deviated = sum(1 for a in assets if a.posture_status == CloudPostureStatusEnum.DEVIATED)

        open_findings = [f for f in findings if f.evaluation_status == EvaluationStatusEnum.FAILED]
        critical_findings = sum(1 for f in open_findings if f.severity == RuleSeverityEnum.CRITICAL)

        active_drifts = sum(1 for d in drifts if d.status in [DriftStatusEnum.DETECTED, DriftStatusEnum.REMEDIATING])

        avg_posture = (
            sum(float(a.posture_score) for a in assets) / total_assets
            if total_assets > 0
            else 100.00
        )
        avg_blast = (
            sum(float(a.blast_radius_score) for a in assets) / total_assets
            if total_assets > 0
            else 0.00
        )

        providers: Dict[str, int] = {}
        envs: Dict[str, int] = {}
        for a in assets:
            providers[a.provider.value] = providers.get(a.provider.value, 0) + 1
            envs[a.environment.value] = envs.get(a.environment.value, 0) + 1

        return CloudPostureSummaryResponse(
            total_cloud_assets=total_assets,
            compliant_assets_count=compliant,
            non_compliant_assets_count=non_compliant,
            deviated_assets_count=deviated,
            total_open_findings=len(open_findings),
            critical_findings_count=critical_findings,
            active_drifts_count=active_drifts,
            average_posture_score=round(avg_posture, 2),
            average_blast_radius_score=round(avg_blast, 2),
            provider_distribution=providers,
            environment_distribution=envs,
        )
