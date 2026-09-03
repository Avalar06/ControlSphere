from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.file_security import sanitize_filename
from app.models.ai_governance import AIDeploymentApproval, AIApprovalStatusEnum, AISystem
from app.models.assessment import Assessment
from app.models.audit_engagement import Audit, AuditOpinionEnum
from app.models.audit_log import AuditLog
from app.models.cloudsec import CloudAsset, CloudPostureStatusEnum, CloudSecurityFinding
from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceRequirement, EvidenceStatusEnum
from app.models.executive import (
    ArtifactTypeEnum,
    BriefingStatusEnum,
    DossierStatusEnum,
    DossierTypeEnum,
    ExecutiveBriefing,
    ExecutiveDossier,
    ExecutiveExportArtifact,
    ExecutiveSnapshot,
    ExportFormatEnum,
)
from app.models.exposure import ExposureStatusEnum, VulnerabilityExposure
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum
from app.models.framework import Framework
from app.models.harmonization import FrameworkComplianceSnapshot
from app.models.identity_governance import (
    GovernedIdentity,
    SoDConflictViolation,
    SoDViolationStatusEnum,
    ZeroTrustAssessment,
)
from app.models.incident import IncidentSeverityEnum, IncidentStatusEnum, SecurityIncident
from app.models.privacy import DPIAAssessment, PrivacyApprovalStatus, ProcessingActivity
from app.models.quant_risk import FinancialRiskAppetite, QuantitativeRiskScenario
from app.models.remediation import RemediationPlan, RemediationStatusEnum, SlaStatusEnum
from app.models.risk import Risk, RiskStatusEnum
from app.models.supply_chain import SBOMDocument, SBOMStatusEnum, SoftwareProduct
from app.models.tprm import Vendor, VendorRiskBandEnum, VendorStatusEnum
from app.models.user import User
from app.schemas.executive import (
    CriticalFindingItem,
    ExecutiveBriefingCreate,
    ExecutiveBriefingReview,
    ExecutiveDossierCreate,
    ExecutiveDossierUpdate,
    ExecutiveSnapshotCreate,
    ExecutiveTelemetryResponse,
    ExecutiveTrendDataPoint,
    ExecutiveTrendsResponse,
    TopRiskItem,
)
from app.services.audit_service import AuditService


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic Canonical JSON Hashing Helper (Key-Sorted Normalized JSON Encoding)
# ─────────────────────────────────────────────────────────────────────────────

def _canonicalize_value(obj: Any) -> Any:
    """Recursively canonicalizes python data structures for deterministic JSON serialization."""
    if isinstance(obj, (datetime, date)):
        if isinstance(obj, datetime):
            # Ensure UTC ISO format with trailing 'Z'
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=timezone.utc)
            else:
                obj = obj.astimezone(timezone.utc)
            return obj.strftime("%Y-%m-%dT%H:%M:%SZ")
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {str(k): _canonicalize_value(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, (list, tuple, set)):
        return [_canonicalize_value(item) for item in obj]
    elif isinstance(obj, float):
        # Format floating numbers deterministically
        return round(obj, 6)
    return obj


def canonical_json_dumps(data: Any) -> str:
    """Produces deterministic canonical JSON string."""
    canonical_data = _canonicalize_value(data)
    return json.dumps(
        canonical_data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def compute_canonical_sha256(data: Any) -> str:
    """Calculates lowercase SHA-256 hexadecimal digest from canonical JSON representation."""
    canonical_str = canonical_json_dumps(data)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest().lower()


# ─────────────────────────────────────────────────────────────────────────────
# ExecutiveService Implementation
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveService:

    @classmethod
    def _log_action(
        cls,
        db: Session,
        organization_id: int,
        action: str,
        resource_type: str,
        actor_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        user = db.query(User).filter(User.id == actor_id).first() if actor_id else None
        actor_email = user.email if user else "system@control-sphere.internal"
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

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Telemetry & Live Aggregation
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def calculate_live_telemetry(
        cls, db: Session, org_id: int
    ) -> Tuple[ExecutiveTelemetryResponse, Dict[str, Any]]:
        """
        Calculates server-authoritative cross-module executive telemetry.
        Returns (ExecutiveTelemetryResponse, source_manifest).
        """
        now_utc = datetime.now(timezone.utc)
        manifest_domains: Dict[str, Any] = {}

        # ── Domain 1: Frameworks & Controls (w = 0.20) ────────────────────────
        ctrls_total = db.query(func.count(OrganizationControl.id)).filter(
            OrganizationControl.organization_id == org_id
        ).scalar() or 0

        ctrls_implemented = db.query(func.count(OrganizationControl.id)).filter(
            OrganizationControl.organization_id == org_id,
            OrganizationControl.status == ImplementationStatusEnum.IMPLEMENTED,
        ).scalar() or 0

        max_ctrl_updated = db.query(func.max(OrganizationControl.updated_at)).filter(
            OrganizationControl.organization_id == org_id
        ).scalar()

        sample_ctrl_ids = [
            c.id for c in db.query(OrganizationControl.id).filter(
                OrganizationControl.organization_id == org_id
            ).limit(10).all()
        ]

        ctrl_score = (ctrls_implemented / ctrls_total * 100.0) if ctrls_total > 0 else 100.0
        ctrl_score = round(max(0.0, min(100.0, ctrl_score)), 2)

        manifest_domains["framework_controls"] = {
            "source_tables": ["organization_controls", "framework_compliance_snapshots"],
            "evaluated_records_count": ctrls_total,
            "max_source_updated_at": max_ctrl_updated.isoformat() if max_ctrl_updated else None,
            "sample_contributing_ids": sample_ctrl_ids,
            "domain_checksum": hashlib.sha256(f"ctrl:{ctrls_total}:{ctrls_implemented}".encode()).hexdigest(),
        }

        # ── Domain 2: Threat Exposure (w = 0.15) ──────────────────────────────
        open_exposures = db.query(VulnerabilityExposure).filter(
            VulnerabilityExposure.organization_id == org_id,
            VulnerabilityExposure.status.in_([
                ExposureStatusEnum.OPEN,
                ExposureStatusEnum.UNDER_INVESTIGATION,
                ExposureStatusEnum.REMEDIATING,
            ]),
        ).all()

        exp_count = len(open_exposures)
        max_exp_updated = db.query(func.max(VulnerabilityExposure.updated_at)).filter(
            VulnerabilityExposure.organization_id == org_id
        ).scalar()

        if exp_count > 0:
            mean_exp_index = sum(e.exposure_index for e in open_exposures) / exp_count
            exp_score = round(max(0.0, min(100.0, 100.0 - mean_exp_index)), 2)
        else:
            exp_score = 100.0

        manifest_domains["threat_exposure"] = {
            "source_tables": ["vulnerability_exposures"],
            "evaluated_records_count": exp_count,
            "max_source_updated_at": max_exp_updated.isoformat() if max_exp_updated else None,
            "sample_contributing_ids": [e.id for e in open_exposures[:10]],
            "domain_checksum": hashlib.sha256(f"exp:{exp_count}:{exp_score}".encode()).hexdigest(),
        }

        # ── Domain 3: Cloud Security (w = 0.15) ───────────────────────────────
        cloud_assets = db.query(CloudAsset).filter(CloudAsset.organization_id == org_id).all()
        cloud_count = len(cloud_assets)
        max_cloud_updated = db.query(func.max(CloudAsset.updated_at)).filter(
            CloudAsset.organization_id == org_id
        ).scalar()

        if cloud_count > 0:
            cloud_score = sum(a.posture_score for a in cloud_assets) / cloud_count
            cloud_score = round(max(0.0, min(100.0, cloud_score)), 2)
        else:
            cloud_score = 100.0

        manifest_domains["cloud_security"] = {
            "source_tables": ["cloud_assets", "cloud_security_findings"],
            "evaluated_records_count": cloud_count,
            "max_source_updated_at": max_cloud_updated.isoformat() if max_cloud_updated else None,
            "sample_contributing_ids": [a.id for a in cloud_assets[:10]],
            "domain_checksum": hashlib.sha256(f"cloud:{cloud_count}:{cloud_score}".encode()).hexdigest(),
        }

        # ── Domain 4: Identity Governance (w = 0.10) ──────────────────────────
        identities = db.query(GovernedIdentity).filter(GovernedIdentity.organization_id == org_id).all()
        id_count = len(identities)
        max_id_updated = db.query(func.max(GovernedIdentity.updated_at)).filter(
            GovernedIdentity.organization_id == org_id
        ).scalar()

        zt_assessments = db.query(ZeroTrustAssessment).filter(
            ZeroTrustAssessment.organization_id == org_id
        ).all()
        mean_zt_score = (
            sum(z.zero_trust_assurance_score for z in zt_assessments) / len(zt_assessments)
            if zt_assessments
            else 75.0
        )

        active_sod_count = db.query(func.count(SoDConflictViolation.id)).filter(
            SoDConflictViolation.organization_id == org_id,
            SoDConflictViolation.status == SoDViolationStatusEnum.ACTIVE_VIOLATION,
        ).scalar() or 0

        sod_penalty_factor = max(0.0, 1.0 - min(1.0, active_sod_count / 10.0))
        identity_score = round(max(0.0, min(100.0, mean_zt_score * sod_penalty_factor)), 2)

        manifest_domains["identity_governance"] = {
            "source_tables": ["governed_identities", "zero_trust_assessments", "sod_conflict_violations"],
            "evaluated_records_count": id_count,
            "max_source_updated_at": max_id_updated.isoformat() if max_id_updated else None,
            "sample_contributing_ids": [i.id for i in identities[:10]],
            "domain_checksum": hashlib.sha256(f"identity:{id_count}:{identity_score}".encode()).hexdigest(),
        }

        # ── Domain 5: Remediation & CAPA Health (w = 0.15) ────────────────────
        plans = db.query(RemediationPlan).filter(RemediationPlan.organization_id == org_id).all()
        plan_count = len(plans)
        max_plan_updated = db.query(func.max(RemediationPlan.updated_at)).filter(
            RemediationPlan.organization_id == org_id
        ).scalar()

        if plan_count > 0:
            healthy_plans = sum(
                1 for p in plans
                if p.sla_status in [SlaStatusEnum.ON_TRACK, SlaStatusEnum.COMPLETED_ON_TIME]
                or p.status == RemediationStatusEnum.VERIFIED_CLOSED
            )
            remediation_score = round(max(0.0, min(100.0, (healthy_plans / plan_count) * 100.0)), 2)
        else:
            remediation_score = 100.0

        manifest_domains["remediation_health"] = {
            "source_tables": ["remediation_plans"],
            "evaluated_records_count": plan_count,
            "max_source_updated_at": max_plan_updated.isoformat() if max_plan_updated else None,
            "sample_contributing_ids": [p.id for p in plans[:10]],
            "domain_checksum": hashlib.sha256(f"rem:{plan_count}:{remediation_score}".encode()).hexdigest(),
        }

        # ── Domain 6: Supply Chain (w = 0.05) ─────────────────────────────────
        products = db.query(SoftwareProduct).filter(SoftwareProduct.organization_id == org_id).all()
        prod_count = len(products)
        max_prod_updated = db.query(func.max(SoftwareProduct.updated_at)).filter(
            SoftwareProduct.organization_id == org_id
        ).scalar()

        if prod_count > 0:
            verified_sboms = db.query(func.count(SBOMDocument.id)).filter(
                SBOMDocument.organization_id == org_id,
                SBOMDocument.status == SBOMStatusEnum.VERIFIED,
            ).scalar() or 0
            supply_score = round(max(0.0, min(100.0, (verified_sboms / prod_count) * 100.0)), 2)
        else:
            supply_score = 100.0

        manifest_domains["supply_chain"] = {
            "source_tables": ["software_products", "sbom_documents"],
            "evaluated_records_count": prod_count,
            "max_source_updated_at": max_prod_updated.isoformat() if max_prod_updated else None,
            "sample_contributing_ids": [pr.id for pr in products[:10]],
            "domain_checksum": hashlib.sha256(f"sc:{prod_count}:{supply_score}".encode()).hexdigest(),
        }

        # ── Domain 7: AI Governance (w = 0.05) ────────────────────────────────
        ai_systems = db.query(AISystem).filter(AISystem.organization_id == org_id).all()
        ai_count = len(ai_systems)
        max_ai_updated = db.query(func.max(AISystem.updated_at)).filter(
            AISystem.organization_id == org_id
        ).scalar()

        if ai_count > 0:
            approved_ai = db.query(func.count(AIDeploymentApproval.id)).filter(
                AIDeploymentApproval.organization_id == org_id,
                AIDeploymentApproval.status == AIApprovalStatusEnum.APPROVED,
            ).scalar() or 0
            ai_score = round(max(0.0, min(100.0, (approved_ai / ai_count) * 100.0)), 2)
        else:
            ai_score = 100.0

        manifest_domains["ai_governance"] = {
            "source_tables": ["ai_systems", "ai_deployment_approvals"],
            "evaluated_records_count": ai_count,
            "max_source_updated_at": max_ai_updated.isoformat() if max_ai_updated else None,
            "sample_contributing_ids": [a.id for a in ai_systems[:10]],
            "domain_checksum": hashlib.sha256(f"ai:{ai_count}:{ai_score}".encode()).hexdigest(),
        }

        # ── Domain 8: Privacy Governance (w = 0.05) ───────────────────────────
        activities = db.query(ProcessingActivity).filter(ProcessingActivity.organization_id == org_id).all()
        act_count = len(activities)
        max_act_updated = db.query(func.max(ProcessingActivity.updated_at)).filter(
            ProcessingActivity.organization_id == org_id
        ).scalar()

        if act_count > 0:
            approved_act = sum(1 for a in activities if a.approval_status == PrivacyApprovalStatus.APPROVED)
            privacy_score = round(max(0.0, min(100.0, (approved_act / act_count) * 100.0)), 2)
        else:
            privacy_score = 100.0

        manifest_domains["privacy"] = {
            "source_tables": ["privacy_processing_activities", "privacy_dpia_assessments"],
            "evaluated_records_count": act_count,
            "max_source_updated_at": max_act_updated.isoformat() if max_act_updated else None,
            "sample_contributing_ids": [a.id for a in activities[:10]],
            "domain_checksum": hashlib.sha256(f"priv:{act_count}:{privacy_score}".encode()).hexdigest(),
        }

        # ── Domain 9: TPRM / Vendors (w = 0.05) ───────────────────────────────
        vendors = db.query(Vendor).filter(
            Vendor.organization_id == org_id,
            Vendor.vendor_status != VendorStatusEnum.OFFBOARDED,
        ).all()
        vendor_count = len(vendors)
        max_vendor_updated = db.query(func.max(Vendor.updated_at)).filter(
            Vendor.organization_id == org_id
        ).scalar()

        if vendor_count > 0:
            low_mod_vendors = sum(
                1 for v in vendors
                if v.risk_band in [VendorRiskBandEnum.LOW, VendorRiskBandEnum.MODERATE]
            )
            tprm_score = round(max(0.0, min(100.0, (low_mod_vendors / vendor_count) * 100.0)), 2)
        else:
            tprm_score = 100.0

        manifest_domains["tprm"] = {
            "source_tables": ["vendors", "vendor_assessments"],
            "evaluated_records_count": vendor_count,
            "max_source_updated_at": max_vendor_updated.isoformat() if max_vendor_updated else None,
            "sample_contributing_ids": [v.id for v in vendors[:10]],
            "domain_checksum": hashlib.sha256(f"tprm:{vendor_count}:{tprm_score}".encode()).hexdigest(),
        }

        # ── Domain 10: Incidents & Resilience (w = 0.05) ──────────────────────
        open_critical_incidents = db.query(func.count(SecurityIncident.id)).filter(
            SecurityIncident.organization_id == org_id,
            SecurityIncident.status.notin_([IncidentStatusEnum.CLOSED, IncidentStatusEnum.CONTAINED]),
            SecurityIncident.severity == IncidentSeverityEnum.CRITICAL,
        ).scalar() or 0

        open_high_incidents = db.query(func.count(SecurityIncident.id)).filter(
            SecurityIncident.organization_id == org_id,
            SecurityIncident.status.notin_([IncidentStatusEnum.CLOSED, IncidentStatusEnum.CONTAINED]),
            SecurityIncident.severity == IncidentSeverityEnum.HIGH,
        ).scalar() or 0

        incidents_penalty = (open_critical_incidents * 25.0) + (open_high_incidents * 10.0)
        resilience_score = round(max(0.0, min(100.0, 100.0 - incidents_penalty)), 2)

        manifest_domains["incidents_resilience"] = {
            "source_tables": ["security_incidents", "business_impact_analyses"],
            "evaluated_records_count": open_critical_incidents + open_high_incidents,
            "max_source_updated_at": now_utc.isoformat(),
            "sample_contributing_ids": [],
            "domain_checksum": hashlib.sha256(f"inc:{open_critical_incidents}:{resilience_score}".encode()).hexdigest(),
        }

        # ── Composite Overall Posture Calculation ─────────────────────────────
        domain_breakdown = {
            "framework_controls": {"name": "Frameworks & Controls", "score": ctrl_score, "weight": 0.20},
            "threat_exposure": {"name": "Threat Exposure", "score": exp_score, "weight": 0.15},
            "cloud_security": {"name": "Cloud Security", "score": cloud_score, "weight": 0.15},
            "identity_governance": {"name": "Identity Governance", "score": identity_score, "weight": 0.10},
            "remediation_health": {"name": "Remediation & CAPA Health", "score": remediation_score, "weight": 0.15},
            "supply_chain": {"name": "Supply Chain & SBOM", "score": supply_score, "weight": 0.05},
            "ai_governance": {"name": "AI Governance", "score": ai_score, "weight": 0.05},
            "privacy": {"name": "Privacy & Data Protection", "score": privacy_score, "weight": 0.05},
            "tprm": {"name": "Third-Party & Vendor Risk", "score": tprm_score, "weight": 0.05},
            "incidents_resilience": {"name": "Incidents & Resilience", "score": resilience_score, "weight": 0.05},
        }

        overall_posture = sum(item["score"] * item["weight"] for item in domain_breakdown.values())
        overall_posture = round(max(0.0, min(100.0, overall_posture)), 2)

        # ── Inherent vs Residual Risk Calculation ─────────────────────────────
        active_risks = db.query(Risk).filter(
            Risk.organization_id == org_id,
            Risk.status != RiskStatusEnum.CLOSED,
        ).all()
        risk_count = len(active_risks)

        if risk_count > 0:
            inherent_mean = sum(r.inherent_score for r in active_risks) / risk_count
            residual_mean = sum(
                (r.residual_score if r.residual_score is not None else r.inherent_score)
                for r in active_risks
            ) / risk_count
            risk_reduction_pct = (
                ((inherent_mean - residual_mean) / inherent_mean * 100.0)
                if inherent_mean > 0 else 0.0
            )
        else:
            inherent_mean = 0.0
            residual_mean = 0.0
            risk_reduction_pct = 0.0

        inherent_mean = round(inherent_mean, 2)
        residual_mean = round(residual_mean, 2)
        risk_reduction_pct = round(max(0.0, min(100.0, risk_reduction_pct)), 2)

        # ── Financial Loss Quantification (FAIR Aggregates) ───────────────────
        quant_scenarios = db.query(QuantitativeRiskScenario).filter(
            QuantitativeRiskScenario.organization_id == org_id
        ).all()
        total_ale = sum(
            q.annualized_loss_expectancy
            for q in quant_scenarios
            if hasattr(q, "annualized_loss_expectancy") and q.annualized_loss_expectancy
        )
        total_var95 = sum(
            (q.var_95_parametric or q.var_95_empirical or 0.0)
            for q in quant_scenarios
        )

        appetite = db.query(FinancialRiskAppetite).filter(
            FinancialRiskAppetite.organization_id == org_id
        ).order_by(FinancialRiskAppetite.version.desc()).first()

        if appetite and appetite.ale_limit > 0.0:
            appetite_utilization = round((total_ale / appetite.ale_limit) * 100.0, 2)
        else:
            appetite_utilization = 0.0

        # ── Audit Readiness Index ─────────────────────────────────────────────
        evid_total = db.query(func.count(EvidenceRequirement.id)).filter(
            EvidenceRequirement.organization_id == org_id
        ).scalar() or 0

        evid_valid = db.query(func.count(EvidenceItem.id)).filter(
            EvidenceItem.organization_id == org_id,
            EvidenceItem.status == EvidenceStatusEnum.ACCEPTED,
        ).scalar() or 0

        evid_freshness_pct = (evid_valid / evid_total * 100.0) if evid_total > 0 else 100.0
        evid_freshness_pct = max(0.0, min(100.0, evid_freshness_pct))

        open_audit_findings_count = db.query(func.count(Finding.id)).filter(
            Finding.organization_id == org_id,
            Finding.status.in_([FindingStatusEnum.OPEN, FindingStatusEnum.IN_REMEDIATION]),
        ).scalar() or 0

        audit_finding_health = max(0.0, 100.0 - (open_audit_findings_count * 10.0))
        audit_readiness = (
            (0.40 * evid_freshness_pct)
            + (0.30 * ctrl_score)
            + (0.30 * audit_finding_health)
        )
        audit_readiness = round(max(0.0, min(100.0, audit_readiness)), 2)

        # ── Top Material Risks & Critical Findings ────────────────────────────
        top_risks_raw = db.query(Risk).filter(
            Risk.organization_id == org_id,
            Risk.status != RiskStatusEnum.CLOSED,
        ).order_by(Risk.inherent_score.desc()).limit(5).all()

        top_risks = [
            TopRiskItem(
                id=r.id,
                title=r.title,
                risk_category=r.risk_category.value if hasattr(r.risk_category, "value") else str(r.risk_category),
                inherent_score=r.inherent_score,
                residual_score=r.residual_score,
                appetite_status=str(r.appetite_status),
            )
            for r in top_risks_raw
        ]

        crit_findings_raw = db.query(Finding).filter(
            Finding.organization_id == org_id,
            Finding.status.in_([FindingStatusEnum.OPEN, FindingStatusEnum.IN_REMEDIATION]),
            Finding.severity.in_([FindingSeverityEnum.CRITICAL, FindingSeverityEnum.HIGH]),
        ).order_by(Finding.risk_score.desc()).limit(5).all()

        critical_findings = [
            CriticalFindingItem(
                id=f.id,
                title=f.title,
                severity=f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                status=f.status.value if hasattr(f.status, "value") else str(f.status),
                due_date=f.due_date,
                owner_name=f.owner.full_name if f.owner else None,
            )
            for f in crit_findings_raw
        ]

        # ── Framework Compliance Posture Summary ──────────────────────────────
        frameworks = db.query(Framework).all()
        framework_summary: Dict[str, Any] = {}
        for fw in frameworks:
            latest_snap = db.query(FrameworkComplianceSnapshot).filter(
                FrameworkComplianceSnapshot.organization_id == org_id,
                FrameworkComplianceSnapshot.framework_id == fw.id,
            ).order_by(FrameworkComplianceSnapshot.created_at.desc()).first()

            if latest_snap:
                framework_summary[fw.identifier] = {
                    "framework_id": fw.id,
                    "name": fw.name,
                    "coverage_percentage": latest_snap.coverage_percentage,
                    "compliance_health_score": latest_snap.compliance_health_score,
                    "total_subcategories": latest_snap.total_subcategories,
                    "covered_subcategories": latest_snap.covered_subcategories,
                }
            else:
                framework_summary[fw.identifier] = {
                    "framework_id": fw.id,
                    "name": fw.name,
                    "coverage_percentage": 0.0,
                    "compliance_health_score": 0.0,
                    "total_subcategories": 0,
                    "covered_subcategories": 0,
                }

        # ── Assemble Canonical Source Manifest ────────────────────────────────
        source_manifest = {
            "calculation_engine_version": "1.0.0",
            "calculated_at": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "organization_id": org_id,
            "domains": manifest_domains,
        }

        telemetry_response = ExecutiveTelemetryResponse(
            overall_posture_score=overall_posture,
            inherent_risk_index=inherent_mean,
            residual_risk_index=residual_mean,
            risk_reduction_percentage=risk_reduction_pct,
            financial_exposure_ale=round(total_ale, 2),
            var_95_exposure=round(total_var95, 2),
            financial_appetite_utilization_pct=appetite_utilization,
            audit_readiness_index=audit_readiness,
            remediation_sla_health_score=remediation_score,
            framework_compliance_summary=framework_summary,
            domain_posture_breakdown=domain_breakdown,
            top_risks=top_risks,
            critical_findings=critical_findings,
            calculated_at=now_utc,
        )

        return telemetry_response, source_manifest

    @classmethod
    def calculate_historical_trends(
        cls, db: Session, org_id: int, window_days: int = 90
    ) -> ExecutiveTrendsResponse:
        """
        Retrieves historical posture trend data points from immutable snapshot records.
        """
        if window_days <= 0 or window_days > 1095:  # Max 3 years
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Window days parameter must be between 1 and 1095 days.",
            )

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=window_days)
        snapshots = db.query(ExecutiveSnapshot).filter(
            ExecutiveSnapshot.organization_id == org_id,
            ExecutiveSnapshot.calculated_at >= cutoff_date,
        ).order_by(ExecutiveSnapshot.calculated_at.asc()).all()

        data_points: List[ExecutiveTrendDataPoint] = []
        for s in snapshots:
            data_points.append(
                ExecutiveTrendDataPoint(
                    timestamp=s.calculated_at,
                    overall_posture_score=s.overall_posture_score,
                    inherent_risk_index=s.inherent_risk_index,
                    residual_risk_index=s.residual_risk_index,
                    financial_exposure_ale=s.financial_exposure_ale,
                    audit_readiness_index=s.audit_readiness_index,
                    remediation_sla_health_score=s.remediation_sla_health_score,
                )
            )

        # If no snapshots exist yet, inject current live telemetry as the baseline point
        if not data_points:
            live_telemetry, _ = cls.calculate_live_telemetry(db, org_id)
            data_points.append(
                ExecutiveTrendDataPoint(
                    timestamp=live_telemetry.calculated_at,
                    overall_posture_score=live_telemetry.overall_posture_score,
                    inherent_risk_index=live_telemetry.inherent_risk_index,
                    residual_risk_index=live_telemetry.residual_risk_index,
                    financial_exposure_ale=live_telemetry.financial_exposure_ale,
                    audit_readiness_index=live_telemetry.audit_readiness_index,
                    remediation_sla_health_score=live_telemetry.remediation_sla_health_score,
                )
            )

        return ExecutiveTrendsResponse(window_days=window_days, data_points=data_points)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Immutable Posture Snapshots
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def capture_snapshot(
        cls, db: Session, org_id: int, user_id: int, data: ExecutiveSnapshotCreate
    ) -> ExecutiveSnapshot:
        """
        Captures a point-in-time immutable executive posture snapshot with deterministic SHA-256 integrity hash.
        """
        # Validate unique snapshot_code within tenant
        existing = db.query(ExecutiveSnapshot).filter(
            ExecutiveSnapshot.organization_id == org_id,
            ExecutiveSnapshot.snapshot_code == data.snapshot_code,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Snapshot code '{data.snapshot_code}' already exists in this organization.",
            )

        telemetry, source_manifest = cls.calculate_live_telemetry(db, org_id)

        # Assemble canonical payload for hashing
        hashable_payload = {
            "metadata": {
                "organization_id": org_id,
                "snapshot_code": data.snapshot_code,
                "created_by_id": user_id,
                "calculated_at": telemetry.calculated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "metrics": {
                "overall_posture_score": telemetry.overall_posture_score,
                "inherent_risk_index": telemetry.inherent_risk_index,
                "residual_risk_index": telemetry.residual_risk_index,
                "risk_reduction_percentage": telemetry.risk_reduction_percentage,
                "financial_exposure_ale": telemetry.financial_exposure_ale,
                "var_95_exposure": telemetry.var_95_exposure,
                "audit_readiness_index": telemetry.audit_readiness_index,
                "remediation_sla_health_score": telemetry.remediation_sla_health_score,
                "domain_posture_breakdown": telemetry.domain_posture_breakdown,
                "framework_compliance_summary": telemetry.framework_compliance_summary,
            },
            "manifest": source_manifest,
        }

        data_hash = compute_canonical_sha256(hashable_payload)

        snapshot = ExecutiveSnapshot(
            organization_id=org_id,
            snapshot_code=data.snapshot_code,
            calculated_at=telemetry.calculated_at,
            overall_posture_score=telemetry.overall_posture_score,
            inherent_risk_index=telemetry.inherent_risk_index,
            residual_risk_index=telemetry.residual_risk_index,
            financial_exposure_ale=telemetry.financial_exposure_ale,
            var_95_exposure=telemetry.var_95_exposure,
            audit_readiness_index=telemetry.audit_readiness_index,
            remediation_sla_health_score=telemetry.remediation_sla_health_score,
            framework_compliance_summary=telemetry.framework_compliance_summary,
            domain_posture_breakdown=telemetry.domain_posture_breakdown,
            top_risks_snapshot=[r.model_dump() for r in telemetry.top_risks],
            critical_findings_snapshot=[f.model_dump() for f in telemetry.critical_findings],
            source_manifest=source_manifest,
            data_hash_sha256=data_hash,
            created_by_id=user_id,
        )

        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        cls._log_action(
            db=db,
            organization_id=org_id,
            action="executive.snapshot.create",
            resource_type="EXECUTIVE_SNAPSHOT",
            actor_id=user_id,
            resource_id=str(snapshot.id),
            details={
                "snapshot_code": snapshot.snapshot_code,
                "overall_posture_score": snapshot.overall_posture_score,
                "data_hash_sha256": snapshot.data_hash_sha256,
            },
        )

        return snapshot

    @classmethod
    def list_snapshots(cls, db: Session, org_id: int) -> List[ExecutiveSnapshot]:
        return db.query(ExecutiveSnapshot).filter(
            ExecutiveSnapshot.organization_id == org_id
        ).order_by(ExecutiveSnapshot.calculated_at.desc()).all()

    @classmethod
    def get_snapshot(cls, db: Session, org_id: int, snapshot_id: int) -> ExecutiveSnapshot:
        snapshot = db.query(ExecutiveSnapshot).filter(
            ExecutiveSnapshot.id == snapshot_id,
            ExecutiveSnapshot.organization_id == org_id,
        ).first()
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Executive snapshot {snapshot_id} not found.",
            )
        return snapshot

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Regulatory Dossiers & Four-Eyes Finalization
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def create_dossier(
        cls, db: Session, org_id: int, user_id: int, data: ExecutiveDossierCreate
    ) -> ExecutiveDossier:
        """Creates a new multi-framework regulatory dossier manifest."""
        # Unique code check
        existing = db.query(ExecutiveDossier).filter(
            ExecutiveDossier.organization_id == org_id,
            ExecutiveDossier.dossier_code == data.dossier_code,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dossier code '{data.dossier_code}' already exists.",
            )

        # Validate framework IDs
        if data.scope_framework_ids:
            fw_count = db.query(func.count(Framework.id)).filter(
                Framework.id.in_(data.scope_framework_ids)
            ).scalar() or 0
            if fw_count != len(data.scope_framework_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more specified framework IDs are invalid.",
                )

        # Validate snapshot_id if provided
        if data.snapshot_id:
            cls.get_snapshot(db, org_id, data.snapshot_id)

        dossier = ExecutiveDossier(
            organization_id=org_id,
            dossier_code=data.dossier_code,
            title=data.title,
            description=data.description,
            dossier_type=data.dossier_type,
            status=DossierStatusEnum.DRAFT,
            scope_framework_ids=data.scope_framework_ids,
            snapshot_id=data.snapshot_id,
            executive_summary=data.executive_summary,
            regulatory_commentary=data.regulatory_commentary,
            created_by_id=user_id,
        )

        db.add(dossier)
        db.commit()
        db.refresh(dossier)

        cls._log_action(
            db=db,
            organization_id=org_id,
            action="executive.dossier.create",
            resource_type="EXECUTIVE_DOSSIER",
            actor_id=user_id,
            resource_id=str(dossier.id),
            details={"dossier_code": dossier.dossier_code, "dossier_type": dossier.dossier_type.value},
        )

        return dossier

    @classmethod
    def list_dossiers(
        cls,
        db: Session,
        org_id: int,
        status_filter: Optional[DossierStatusEnum] = None,
        dossier_type: Optional[DossierTypeEnum] = None,
    ) -> List[ExecutiveDossier]:
        query = db.query(ExecutiveDossier).filter(ExecutiveDossier.organization_id == org_id)
        if status_filter:
            query = query.filter(ExecutiveDossier.status == status_filter)
        if dossier_type:
            query = query.filter(ExecutiveDossier.dossier_type == dossier_type)
        return query.order_by(ExecutiveDossier.created_at.desc()).all()

    @classmethod
    def get_dossier(cls, db: Session, org_id: int, dossier_id: int) -> ExecutiveDossier:
        dossier = db.query(ExecutiveDossier).filter(
            ExecutiveDossier.id == dossier_id,
            ExecutiveDossier.organization_id == org_id,
        ).first()
        if not dossier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Executive dossier {dossier_id} not found.",
            )
        return dossier

    @classmethod
    def update_dossier(
        cls, db: Session, org_id: int, user_id: int, dossier_id: int, data: ExecutiveDossierUpdate
    ) -> ExecutiveDossier:
        dossier = cls.get_dossier(db, org_id, dossier_id)
        if dossier.status == DossierStatusEnum.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Finalized regulatory dossiers are immutable and cannot be modified.",
            )

        if data.title is not None:
            dossier.title = data.title
        if data.description is not None:
            dossier.description = data.description
        if data.executive_summary is not None:
            dossier.executive_summary = data.executive_summary
        if data.regulatory_commentary is not None:
            dossier.regulatory_commentary = data.regulatory_commentary
        if data.snapshot_id is not None:
            cls.get_snapshot(db, org_id, data.snapshot_id)
            dossier.snapshot_id = data.snapshot_id
        if data.scope_framework_ids is not None:
            if data.scope_framework_ids:
                fw_count = db.query(func.count(Framework.id)).filter(
                    Framework.id.in_(data.scope_framework_ids)
                ).scalar() or 0
                if fw_count != len(data.scope_framework_ids):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="One or more specified framework IDs are invalid.",
                    )
            dossier.scope_framework_ids = data.scope_framework_ids

        db.commit()
        db.refresh(dossier)
        return dossier

    @classmethod
    def compile_dossier(
        cls, db: Session, org_id: int, user_id: int, dossier_id: int
    ) -> ExecutiveDossier:
        """Compiles multi-framework evidence, controls, and findings into dossier sections."""
        dossier = cls.get_dossier(db, org_id, dossier_id)
        if dossier.status == DossierStatusEnum.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Finalized dossiers are immutable and cannot be recompiled.",
            )

        # Determine snapshot to bind
        if not dossier.snapshot_id:
            # Auto-create snapshot for this compilation
            snap_code = f"SNAP-DOSSIER-{dossier.dossier_code}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            snap = cls.capture_snapshot(
                db, org_id, user_id, ExecutiveSnapshotCreate(snapshot_code=snap_code)
            )
            dossier.snapshot_id = snap.id
        else:
            snap = cls.get_snapshot(db, org_id, dossier.snapshot_id)

        # Harvest framework specifics
        framework_details: List[Dict[str, Any]] = []
        target_fws = db.query(Framework).filter(
            Framework.id.in_(dossier.scope_framework_ids)
        ).all() if dossier.scope_framework_ids else db.query(Framework).all()

        for fw in target_fws:
            controls = db.query(OrganizationControl).filter(
                OrganizationControl.organization_id == org_id,
            ).all()
            framework_details.append({
                "framework_id": fw.id,
                "framework_name": fw.name,
                "framework_code": fw.identifier,
                "controls_count": len(controls),
            })

        compiled_data = {
            "snapshot_code": snap.snapshot_code,
            "overall_posture_score": snap.overall_posture_score,
            "inherent_risk_index": snap.inherent_risk_index,
            "residual_risk_index": snap.residual_risk_index,
            "financial_exposure_ale": snap.financial_exposure_ale,
            "audit_readiness_index": snap.audit_readiness_index,
            "framework_scope": framework_details,
            "top_material_risks": snap.top_risks_snapshot,
            "critical_open_findings": snap.critical_findings_snapshot,
            "domain_posture": snap.domain_posture_breakdown,
            "compiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        dossier.compiled_sections = compiled_data
        dossier.compiled_at = datetime.now(timezone.utc)
        dossier.compiled_by_id = user_id
        dossier.status = DossierStatusEnum.COMPILED

        db.commit()
        db.refresh(dossier)

        cls._log_action(
            db=db,
            organization_id=org_id,
            action="executive.dossier.compile",
            resource_type="EXECUTIVE_DOSSIER",
            actor_id=user_id,
            resource_id=str(dossier.id),
            details={"dossier_code": dossier.dossier_code, "snapshot_id": dossier.snapshot_id},
        )

        return dossier

    @classmethod
    def finalize_dossier(
        cls, db: Session, org_id: int, user_id: int, dossier_id: int
    ) -> ExecutiveDossier:
        """Executes Four-Eyes finalization of a compiled regulatory dossier."""
        dossier = cls.get_dossier(db, org_id, dossier_id)

        if dossier.status == DossierStatusEnum.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dossier is already finalized.",
            )

        if dossier.status == DossierStatusEnum.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Dossier must be compiled before finalization.",
            )

        # Enforce Four-Eyes Separation of Duties
        if user_id == dossier.created_by_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Four-Eyes violation: Finalizing reviewer cannot be the creator of the dossier.",
            )

        if dossier.compiled_by_id and user_id == dossier.compiled_by_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Four-Eyes violation: Finalizing reviewer cannot be the compiler of the dossier.",
            )

        dossier.status = DossierStatusEnum.FINALIZED
        dossier.finalized_by_id = user_id
        dossier.finalized_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(dossier)

        cls._log_action(
            db=db,
            organization_id=org_id,
            action="executive.dossier.finalize",
            resource_type="EXECUTIVE_DOSSIER",
            actor_id=user_id,
            resource_id=str(dossier.id),
            details={"dossier_code": dossier.dossier_code, "finalized_by_id": user_id},
        )

        return dossier

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Executive Briefings (Four-Eyes SoD Workflow)
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def generate_briefing(
        cls, db: Session, org_id: int, user_id: int, data: ExecutiveBriefingCreate
    ) -> ExecutiveBriefing:
        """Creates a periodic executive/board briefing with period-over-period deltas."""
        if data.reporting_period_end < data.reporting_period_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reporting period end date cannot be earlier than start date.",
            )

        # Unique code check
        existing = db.query(ExecutiveBriefing).filter(
            ExecutiveBriefing.organization_id == org_id,
            ExecutiveBriefing.briefing_code == data.briefing_code,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Briefing code '{data.briefing_code}' already exists.",
            )

        current_snap = cls.get_snapshot(db, org_id, data.snapshot_id)

        # Find previous snapshot to calculate period-over-period deltas
        prev_snap = db.query(ExecutiveSnapshot).filter(
            ExecutiveSnapshot.organization_id == org_id,
            ExecutiveSnapshot.calculated_at < current_snap.calculated_at,
        ).order_by(ExecutiveSnapshot.calculated_at.desc()).first()

        if prev_snap:
            deltas = {
                "posture_score_delta": round(current_snap.overall_posture_score - prev_snap.overall_posture_score, 2),
                "inherent_risk_delta": round(current_snap.inherent_risk_index - prev_snap.inherent_risk_index, 2),
                "residual_risk_delta": round(current_snap.residual_risk_index - prev_snap.residual_risk_index, 2),
                "financial_ale_delta": round(current_snap.financial_exposure_ale - prev_snap.financial_exposure_ale, 2),
                "audit_readiness_delta": round(current_snap.audit_readiness_index - prev_snap.audit_readiness_index, 2),
                "remediation_health_delta": round(current_snap.remediation_sla_health_score - prev_snap.remediation_sla_health_score, 2),
                "previous_snapshot_code": prev_snap.snapshot_code,
            }
        else:
            deltas = {
                "posture_score_delta": 0.0,
                "inherent_risk_delta": 0.0,
                "residual_risk_delta": 0.0,
                "financial_ale_delta": 0.0,
                "audit_readiness_delta": 0.0,
                "remediation_health_delta": 0.0,
                "previous_snapshot_code": None,
            }

        briefing = ExecutiveBriefing(
            organization_id=org_id,
            briefing_code=data.briefing_code,
            title=data.title,
            reporting_period_start=data.reporting_period_start,
            reporting_period_end=data.reporting_period_end,
            status=BriefingStatusEnum.DRAFT,
            snapshot_id=current_snap.id,
            executive_summary=data.executive_summary,
            key_achievements=data.key_achievements,
            emerging_risks=data.emerging_risks,
            strategic_recommendations=data.strategic_recommendations,
            period_over_period_deltas=deltas,
            generated_by_id=user_id,
        )

        db.add(briefing)
        db.commit()
        db.refresh(briefing)

        cls._log_action(
            db=db,
            organization_id=org_id,
            action="executive.briefing.create",
            resource_type="EXECUTIVE_BRIEFING",
            actor_id=user_id,
            resource_id=str(briefing.id),
            details={"briefing_code": briefing.briefing_code, "snapshot_id": briefing.snapshot_id},
        )

        return briefing

    @classmethod
    def list_briefings(
        cls, db: Session, org_id: int, status_filter: Optional[BriefingStatusEnum] = None
    ) -> List[ExecutiveBriefing]:
        query = db.query(ExecutiveBriefing).filter(ExecutiveBriefing.organization_id == org_id)
        if status_filter:
            query = query.filter(ExecutiveBriefing.status == status_filter)
        return query.order_by(ExecutiveBriefing.created_at.desc()).all()

    @classmethod
    def get_briefing(cls, db: Session, org_id: int, briefing_id: int) -> ExecutiveBriefing:
        briefing = db.query(ExecutiveBriefing).filter(
            ExecutiveBriefing.id == briefing_id,
            ExecutiveBriefing.organization_id == org_id,
        ).first()
        if not briefing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Executive briefing {briefing_id} not found.",
            )
        return briefing

    @classmethod
    def submit_briefing(cls, db: Session, org_id: int, user_id: int, briefing_id: int) -> ExecutiveBriefing:
        briefing = cls.get_briefing(db, org_id, briefing_id)
        if briefing.status != BriefingStatusEnum.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit briefing in '{briefing.status.value}' state. Must be in DRAFT.",
            )

        briefing.status = BriefingStatusEnum.SUBMITTED_FOR_REVIEW
        db.commit()
        db.refresh(briefing)

        cls._log_action(
            db=db,
            organization_id=org_id,
            action="executive.briefing.submit",
            resource_type="EXECUTIVE_BRIEFING",
            actor_id=user_id,
            resource_id=str(briefing.id),
            details={"briefing_code": briefing.briefing_code},
        )
        return briefing

    @classmethod
    def review_briefing(
        cls, db: Session, org_id: int, reviewer_id: int, briefing_id: int, review: ExecutiveBriefingReview
    ) -> ExecutiveBriefing:
        briefing = cls.get_briefing(db, org_id, briefing_id)

        if briefing.status in [BriefingStatusEnum.APPROVED, BriefingStatusEnum.SUPERSEDED]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Briefing is already in terminal state '{briefing.status.value}'.",
            )

        # Four-Eyes Check: Creator cannot approve own briefing
        if reviewer_id == briefing.generated_by_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Four-Eyes violation: Author cannot approve their own executive briefing.",
            )

        briefing.status = BriefingStatusEnum.APPROVED if review.approved else BriefingStatusEnum.REJECTED
        briefing.approved_by_id = reviewer_id
        briefing.approved_at = datetime.now(timezone.utc)
        briefing.review_notes = review.review_notes

        db.commit()
        db.refresh(briefing)

        cls._log_action(
            db=db,
            organization_id=org_id,
            action="executive.briefing.approve" if review.approved else "executive.briefing.reject",
            resource_type="EXECUTIVE_BRIEFING",
            actor_id=reviewer_id,
            resource_id=str(briefing.id),
            details={"approved": review.approved, "notes": review.review_notes},
        )

        return briefing

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Forensic Export Generation & Download (PDF & JSON)
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def _ensure_export_dir(cls, org_id: int) -> Path:
        base_dir = Path("storage") / "executive" / f"org_{org_id}"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir

    @classmethod
    def generate_pdf_export(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        artifact_type: ArtifactTypeEnum,
        resource_id: int,
    ) -> ExecutiveExportArtifact:
        """Generates deterministic, audit-grade forensic PDF report via ReportLab."""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.pdfgen import canvas

        # Retrieve underlying resource and tenant
        org_user = db.query(User).filter(User.id == user_id).first()
        org_name = org_user.organization.name if org_user and org_user.organization else f"Organization #{org_id}"

        dossier_obj: Optional[ExecutiveDossier] = None
        briefing_obj: Optional[ExecutiveBriefing] = None
        snapshot_obj: Optional[ExecutiveSnapshot] = None

        if artifact_type == ArtifactTypeEnum.DOSSIER_PACKAGE:
            dossier_obj = cls.get_dossier(db, org_id, resource_id)
            snapshot_obj = dossier_obj.snapshot or cls.get_snapshot(db, org_id, dossier_obj.snapshot_id) if dossier_obj.snapshot_id else None
            report_title = f"Regulatory Compliance Dossier: {dossier_obj.title}"
            code_prefix = f"EXP-DOS-{dossier_obj.dossier_code}"
        elif artifact_type == ArtifactTypeEnum.EXECUTIVE_BRIEFING:
            briefing_obj = cls.get_briefing(db, org_id, resource_id)
            snapshot_obj = briefing_obj.snapshot
            report_title = f"Executive Governance Briefing: {briefing_obj.title}"
            code_prefix = f"EXP-BRF-{briefing_obj.briefing_code}"
        else:
            snapshot_obj = cls.get_snapshot(db, org_id, resource_id)
            report_title = f"Executive Posture Snapshot: {snapshot_obj.snapshot_code}"
            code_prefix = f"EXP-SNP-{snapshot_obj.snapshot_code}"

        export_code = f"{code_prefix}-PDF-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        safe_filename = sanitize_filename(f"{export_code}.pdf")
        export_dir = cls._ensure_export_dir(org_id)
        file_path = export_dir / safe_filename

        # Build PDF Document
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Title"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            alignment=0,
        )
        subtitle_style = ParagraphStyle(
            "DocSub",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#475569"),
        )
        h2_style = ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )

        story = []

        # Header Block
        story.append(Paragraph(f"<b>CONTROLSPHERE EXECUTIVE GOVERNANCE SUITE</b>", subtitle_style))
        story.append(Paragraph(f"<b>{report_title}</b>", title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"Organization: <b>{org_name}</b> | Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Code: {export_code}",
            subtitle_style,
        ))
        story.append(Spacer(1, 12))

        # Executive Metrics Table
        if snapshot_obj:
            story.append(Paragraph("<b>1. Executive Cyber-Risk & Posture Telemetry</b>", h2_style))
            kpi_data = [
                ["Executive Metric", "Score / Index", "Target / Status", "Maturity / Level"],
                ["Overall Governance Posture", f"{snapshot_obj.overall_posture_score:.1f}%", ">= 85.0%", "OPTIMAL" if snapshot_obj.overall_posture_score >= 80 else "MODERATE"],
                ["Inherent Risk Index", f"{snapshot_obj.inherent_risk_index:.2f} / 25", "<= 12.0", "EVALUATED"],
                ["Residual Risk Index", f"{snapshot_obj.residual_risk_index:.2f} / 25", "<= 8.0", "CONTROLLED"],
                ["Financial Exposure (ALE)", f"${snapshot_obj.financial_exposure_ale:,.2f}", "Within Appetite", "QUANTIFIED"],
                ["Tail Risk (VaR 95%)", f"${snapshot_obj.var_95_exposure:,.2f}", "Quantified FAIR", "MODELLED"],
                ["Audit Readiness Index", f"{snapshot_obj.audit_readiness_index:.1f}%", ">= 90.0%", "AUDIT-READY" if snapshot_obj.audit_readiness_index >= 85 else "IN PROGRESS"],
                ["Remediation SLA Compliance", f"{snapshot_obj.remediation_sla_health_score:.1f}%", "100.0%", "GOVERNED"],
            ]
            t = Table(kpi_data, colWidths=[180, 100, 110, 110])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            story.append(t)
            story.append(Spacer(1, 10))

            # Domain Posture Breakdown Table
            story.append(Paragraph("<b>2. Cross-Domain Governance Health Matrix</b>", h2_style))
            dom_data = [["Domain", "Score", "Weight", "Weighted Contribution"]]
            for k, dom in snapshot_obj.domain_posture_breakdown.items():
                weighted = (dom.get("score", 0.0) * dom.get("weight", 0.0))
                dom_data.append([
                    dom.get("name", k),
                    f"{dom.get('score', 0.0):.1f}%",
                    f"{dom.get('weight', 0.0) * 100:.0f}%",
                    f"{weighted:.2f} pts",
                ])
            dt = Table(dom_data, colWidths=[200, 100, 100, 100])
            dt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            story.append(dt)
            story.append(Spacer(1, 10))

        # Briefing or Dossier Narrative Section
        if briefing_obj:
            story.append(Paragraph("<b>3. Executive Strategic Summary & Recommendations</b>", h2_style))
            story.append(Paragraph(f"<b>Summary:</b> {briefing_obj.executive_summary}", body_style))
            if briefing_obj.strategic_recommendations:
                story.append(Spacer(1, 4))
                story.append(Paragraph(f"<b>Recommendations:</b> {briefing_obj.strategic_recommendations}", body_style))
            story.append(Spacer(1, 8))

        if dossier_obj:
            story.append(Paragraph("<b>3. Regulatory Dossier Manifest & Scope</b>", h2_style))
            if dossier_obj.executive_summary:
                story.append(Paragraph(f"<b>Governance Statement:</b> {dossier_obj.executive_summary}", body_style))
            if dossier_obj.regulatory_commentary:
                story.append(Spacer(1, 4))
                story.append(Paragraph(f"<b>Regulatory Commentary:</b> {dossier_obj.regulatory_commentary}", body_style))
            story.append(Spacer(1, 8))

        # Forensic Audit Footer Stamp
        story.append(Spacer(1, 14))
        story.append(Paragraph("<b>CONFIDENTIAL — BOARD & EXECUTIVE AUDIT ARTIFACT</b>", ParagraphStyle(
            "Conf", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#94a3b8"), alignment=1
        )))

        # Build PDF file
        doc.build(story)

        # Compute SHA-256 of output file
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
            checksum = hashlib.sha256(pdf_bytes).hexdigest().lower()

        artifact = ExecutiveExportArtifact(
            organization_id=org_id,
            export_code=export_code,
            export_format=ExportFormatEnum.PDF,
            artifact_type=artifact_type,
            dossier_id=dossier_obj.id if dossier_obj else None,
            briefing_id=briefing_obj.id if briefing_obj else None,
            snapshot_id=snapshot_obj.id if snapshot_obj else None,
            storage_key=str(file_path),
            original_filename=safe_filename,
            mime_type="application/pdf",
            file_size_bytes=len(pdf_bytes),
            sha256_checksum=checksum,
            generated_by_id=user_id,
        )

        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        cls._log_action(
            db=db,
            organization_id=org_id,
            action="executive.export.generate",
            resource_type="EXECUTIVE_EXPORT",
            actor_id=user_id,
            resource_id=str(artifact.id),
            details={"export_code": export_code, "format": "PDF", "sha256": checksum},
        )

        return artifact

    @classmethod
    def generate_json_export(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        artifact_type: ArtifactTypeEnum,
        resource_id: int,
    ) -> ExecutiveExportArtifact:
        """Generates deterministic canonical JSON forensic export artifact."""
        dossier_obj: Optional[ExecutiveDossier] = None
        briefing_obj: Optional[ExecutiveBriefing] = None
        snapshot_obj: Optional[ExecutiveSnapshot] = None

        if artifact_type == ArtifactTypeEnum.DOSSIER_PACKAGE:
            dossier_obj = cls.get_dossier(db, org_id, resource_id)
            snapshot_obj = dossier_obj.snapshot or cls.get_snapshot(db, org_id, dossier_obj.snapshot_id) if dossier_obj.snapshot_id else None
            code_prefix = f"EXP-DOS-{dossier_obj.dossier_code}"
            resource_payload = {
                "dossier_code": dossier_obj.dossier_code,
                "title": dossier_obj.title,
                "dossier_type": dossier_obj.dossier_type.value,
                "status": dossier_obj.status.value,
                "scope_framework_ids": dossier_obj.scope_framework_ids,
                "executive_summary": dossier_obj.executive_summary,
                "regulatory_commentary": dossier_obj.regulatory_commentary,
                "compiled_sections": dossier_obj.compiled_sections,
            }
        elif artifact_type == ArtifactTypeEnum.EXECUTIVE_BRIEFING:
            briefing_obj = cls.get_briefing(db, org_id, resource_id)
            snapshot_obj = briefing_obj.snapshot
            code_prefix = f"EXP-BRF-{briefing_obj.briefing_code}"
            resource_payload = {
                "briefing_code": briefing_obj.briefing_code,
                "title": briefing_obj.title,
                "status": briefing_obj.status.value,
                "reporting_period_start": briefing_obj.reporting_period_start.isoformat(),
                "reporting_period_end": briefing_obj.reporting_period_end.isoformat(),
                "executive_summary": briefing_obj.executive_summary,
                "strategic_recommendations": briefing_obj.strategic_recommendations,
                "period_over_period_deltas": briefing_obj.period_over_period_deltas,
            }
        else:
            snapshot_obj = cls.get_snapshot(db, org_id, resource_id)
            code_prefix = f"EXP-SNP-{snapshot_obj.snapshot_code}"
            resource_payload = {}

        export_code = f"{code_prefix}-JSON-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        safe_filename = sanitize_filename(f"{export_code}.json")
        export_dir = cls._ensure_export_dir(org_id)
        file_path = export_dir / safe_filename

        export_data = {
            "metadata": {
                "export_code": export_code,
                "artifact_type": artifact_type.value,
                "organization_id": org_id,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "generated_by_id": user_id,
            },
            "resource": resource_payload,
            "snapshot": {
                "snapshot_code": snapshot_obj.snapshot_code if snapshot_obj else None,
                "overall_posture_score": snapshot_obj.overall_posture_score if snapshot_obj else None,
                "inherent_risk_index": snapshot_obj.inherent_risk_index if snapshot_obj else None,
                "residual_risk_index": snapshot_obj.residual_risk_index if snapshot_obj else None,
                "financial_exposure_ale": snapshot_obj.financial_exposure_ale if snapshot_obj else None,
                "audit_readiness_index": snapshot_obj.audit_readiness_index if snapshot_obj else None,
                "remediation_sla_health_score": snapshot_obj.remediation_sla_health_score if snapshot_obj else None,
                "domain_posture_breakdown": snapshot_obj.domain_posture_breakdown if snapshot_obj else None,
                "framework_compliance_summary": snapshot_obj.framework_compliance_summary if snapshot_obj else None,
                "source_manifest": snapshot_obj.source_manifest if snapshot_obj else None,
                "data_hash_sha256": snapshot_obj.data_hash_sha256 if snapshot_obj else None,
            } if snapshot_obj else None,
        }

        canonical_bytes = canonical_json_dumps(export_data).encode("utf-8")
        checksum = hashlib.sha256(canonical_bytes).hexdigest().lower()

        with open(file_path, "wb") as f:
            f.write(canonical_bytes)

        artifact = ExecutiveExportArtifact(
            organization_id=org_id,
            export_code=export_code,
            export_format=ExportFormatEnum.JSON,
            artifact_type=artifact_type,
            dossier_id=dossier_obj.id if dossier_obj else None,
            briefing_id=briefing_obj.id if briefing_obj else None,
            snapshot_id=snapshot_obj.id if snapshot_obj else None,
            storage_key=str(file_path),
            original_filename=safe_filename,
            mime_type="application/json",
            file_size_bytes=len(canonical_bytes),
            sha256_checksum=checksum,
            generated_by_id=user_id,
        )

        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        cls._log_action(
            db=db,
            organization_id=org_id,
            action="executive.export.generate",
            resource_type="EXECUTIVE_EXPORT",
            actor_id=user_id,
            resource_id=str(artifact.id),
            details={"export_code": export_code, "format": "JSON", "sha256": checksum},
        )

        return artifact

    @classmethod
    def list_exports(cls, db: Session, org_id: int) -> List[ExecutiveExportArtifact]:
        return db.query(ExecutiveExportArtifact).filter(
            ExecutiveExportArtifact.organization_id == org_id
        ).order_by(ExecutiveExportArtifact.generated_at.desc()).all()

    @classmethod
    def get_export_stream(
        cls, db: Session, org_id: int, user_id: int, export_id: int
    ) -> Tuple[bytes, str, str]:
        """
        Retrieves export artifact file bytes with strict SHA-256 integrity verification.
        Returns (file_bytes, original_filename, mime_type).
        """
        artifact = db.query(ExecutiveExportArtifact).filter(
            ExecutiveExportArtifact.id == export_id,
            ExecutiveExportArtifact.organization_id == org_id,
        ).first()

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Export artifact {export_id} not found.",
            )

        file_path = Path(artifact.storage_key)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical artifact file not found on storage.",
            )

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        current_sha256 = hashlib.sha256(file_bytes).hexdigest().lower()
        if current_sha256 != artifact.sha256_checksum.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Forensic checksum mismatch: physical artifact content has been altered.",
            )

        cls._log_action(
            db=db,
            organization_id=org_id,
            action="executive.export.download",
            resource_type="EXECUTIVE_EXPORT",
            actor_id=user_id,
            resource_id=str(artifact.id),
            details={"export_code": artifact.export_code, "sha256": artifact.sha256_checksum},
        )

        return file_bytes, artifact.original_filename, artifact.mime_type
