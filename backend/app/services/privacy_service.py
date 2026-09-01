from datetime import datetime
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.privacy import (
    DataAsset,
    DataSensitivityLevel,
    DataTransferAssessment,
    DPIAAssessment,
    DPIARiskBand,
    JurisdictionRiskTier,
    PrivacyApprovalStatus,
    ProcessingActivity,
    ProcessingLegalBasis,
    ProcessingLifecycleState,
    TransferMechanism,
)
from app.models.resilience import BusinessProcess
from app.models.ai_governance import AISystem
from app.models.tprm import Vendor
from app.models.remediation import RemediationPlan
from app.models.user import User
from app.schemas.privacy import (
    DataAssetCreate,
    DataAssetUpdate,
    DataTransferCreate,
    DataTransferReviewRequest,
    DataTransferUpdate,
    DPIACreate,
    DPIAReviewRequest,
    DPIAUpdate,
    PrivacyPostureSummaryResponse,
    ProcessingActivityCreate,
    ProcessingActivityStatusUpdate,
    ProcessingActivityUpdate,
)
from app.services.audit_service import AuditService


class PrivacyService:
    # ─── Mathematical Engine ──────────────────────────────────────────────────

    BASE_SENSITIVITY_MAP = {
        DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI: 65.0,
        DataSensitivityLevel.RESTRICTED_PII: 40.0,
        DataSensitivityLevel.CONFIDENTIAL: 20.0,
        DataSensitivityLevel.INTERNAL: 5.0,
        DataSensitivityLevel.PUBLIC: 0.0,
    }

    VOLUME_MULTIPLIER_MAP = {
        "HIGH": 1.30,      # > 1,000,000 subjects
        "MEDIUM": 1.15,    # 10,000 - 1,000,000 subjects
        "LOW": 1.00,       # < 10,000 subjects
    }

    JURISDICTION_BASE_MAP = {
        JurisdictionRiskTier.PROHIBITED_TRANSFERS: 100.0,
        JurisdictionRiskTier.HIGH_RISK_SURVEILLANCE: 75.0,
        JurisdictionRiskTier.MODERATE_SAFEGUARDS_REQUIRED: 40.0,
        JurisdictionRiskTier.ADEQUATE_LOW_RISK: 10.0,
    }

    MECHANISM_MULTIPLIER_MAP = {
        TransferMechanism.NONE_INTRA_EEA: 0.00,
        TransferMechanism.ADEQUACY_DECISION: 0.50,
        TransferMechanism.BINDING_CORPORATE_RULES_BCR: 0.80,
        TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES_SCC: 1.00,
        TransferMechanism.DEROGATION_EXPLICIT_CONSENT: 1.20,
    }

    @classmethod
    def _log_audit(
        cls,
        db: Session,
        organization_id: int,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int],
        details: Optional[Dict] = None,
    ) -> None:
        user = db.query(User).filter(User.id == user_id).first()
        actor_email = user.email if user else "system@control-sphere.internal"
        AuditService.log(
            db=db,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            actor_email=actor_email,
            actor_id=user_id,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details or {},
        )

    @classmethod
    def calculate_dpia_inherent_risk(
        cls,
        sensitivity_level: DataSensitivityLevel,
        volume_tier: str = "LOW",
        is_special_category: bool = False,
        automated_decision_making_risk: bool = False,
        large_scale_monitoring_risk: bool = False,
        vulnerable_subjects_risk: bool = False,
    ) -> float:
        """
        Calculates server-authoritative DPIA Inherent Risk Score (IRS) on 0.00 - 100.00 scale:
        IRS = min(100.00, (BaseSensitivity * VolumeMultiplier * SpecialCategoryMultiplier) + TriggerPenalty)
        """
        base_sensitivity = cls.BASE_SENSITIVITY_MAP.get(sensitivity_level, 5.0)
        norm_vol = str(volume_tier).upper() if volume_tier else "LOW"
        vol_mult = cls.VOLUME_MULTIPLIER_MAP.get(norm_vol, 1.00)
        special_mult = 1.25 if is_special_category else 1.00

        # Trigger penalties (+10 each, capped at +30)
        trigger_penalty = 0.0
        if automated_decision_making_risk:
            trigger_penalty += 10.0
        if large_scale_monitoring_risk:
            trigger_penalty += 10.0
        if vulnerable_subjects_risk:
            trigger_penalty += 10.0
        trigger_penalty = min(30.0, trigger_penalty)

        raw_irs = (base_sensitivity * vol_mult * special_mult) + trigger_penalty
        return min(100.00, max(0.00, round(raw_irs, 2)))

    @classmethod
    def calculate_dpia_residual_risk(
        cls,
        inherent_risk_score: float,
        safeguards_mitigation_score: float = 0.0,
        has_threat_exposure: bool = False,
    ) -> float:
        """
        Calculates server-authoritative DPIA Residual Risk Score (RRS) on 0.00 - 100.00 scale:
        RRS = max(0.00, min(100.00, IRS * (1.0 - SafeguardsMitigationRate) + ThreatExposurePenalty))
        Safeguards mitigation is capped at 70% (0.70).
        """
        irs = max(0.0, min(100.0, float(inherent_risk_score)))
        safeguards_raw = max(0.0, min(100.0, float(safeguards_mitigation_score)))
        # Map 0-100 score to 0.0 - 0.70 rate
        safeguards_rate = min(0.70, (safeguards_raw / 100.0) * 0.70)

        threat_penalty = 15.0 if has_threat_exposure else 0.0
        raw_rrs = (irs * (1.0 - safeguards_rate)) + threat_penalty
        return min(100.00, max(0.00, round(raw_rrs, 2)))

    @classmethod
    def determine_dpia_risk_band(cls, residual_risk_score: float) -> DPIARiskBand:
        rrs = float(residual_risk_score)
        if rrs >= 80.0:
            return DPIARiskBand.CRITICAL
        elif rrs >= 60.0:
            return DPIARiskBand.VERY_HIGH
        elif rrs >= 40.0:
            return DPIARiskBand.HIGH
        elif rrs >= 20.0:
            return DPIARiskBand.MODERATE
        return DPIARiskBand.LOW

    @classmethod
    def calculate_transfer_risk_index(
        cls,
        destination_tier: JurisdictionRiskTier,
        mechanism: TransferMechanism,
        supplementary_measures_score: float = 0.0,
    ) -> float:
        """
        Calculates server-authoritative Transfer Risk Index (TRI) on 0.00 - 100.00 scale:
        TRI = min(100.00, max(0.00, (JurisdictionBase * MechanismMultiplier) - SupplementaryMeasures))
        """
        jurisdiction_base = cls.JURISDICTION_BASE_MAP.get(destination_tier, 40.0)
        mechanism_mult = cls.MECHANISM_MULTIPLIER_MAP.get(mechanism, 1.00)
        supplementary_mitigation = max(0.0, min(30.0, float(supplementary_measures_score)))

        raw_tri = (jurisdiction_base * mechanism_mult) - supplementary_mitigation
        return min(100.00, max(0.00, round(raw_tri, 2)))

    # ─── Cross-Module Tenant Validation ───────────────────────────────────────

    @classmethod
    def validate_cross_module_references(
        cls,
        db: Session,
        organization_id: int,
        business_process_id: Optional[int] = None,
        ai_system_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        remediation_plan_id: Optional[int] = None,
    ) -> None:
        if business_process_id is not None:
            bp = db.query(BusinessProcess).filter(
                BusinessProcess.id == business_process_id,
                BusinessProcess.organization_id == organization_id,
            ).first()
            if not bp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Business process {business_process_id} not found in this organization",
                )

        if ai_system_id is not None:
            ai_sys = db.query(AISystem).filter(
                AISystem.id == ai_system_id,
                AISystem.organization_id == organization_id,
            ).first()
            if not ai_sys:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"AI system {ai_system_id} not found in this organization",
                )

        if vendor_id is not None:
            v = db.query(Vendor).filter(
                Vendor.id == vendor_id,
                Vendor.organization_id == organization_id,
            ).first()
            if not v:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vendor {vendor_id} not found in this organization",
                )

        if remediation_plan_id is not None:
            rp = db.query(RemediationPlan).filter(
                RemediationPlan.id == remediation_plan_id,
                RemediationPlan.organization_id == organization_id,
            ).first()
            if not rp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Remediation plan {remediation_plan_id} not found in this organization",
                )

    # ─── Data Asset Operations ────────────────────────────────────────────────

    @classmethod
    def create_data_asset(
        cls,
        db: Session,
        organization_id: int,
        owner_id: int,
        payload: DataAssetCreate,
    ) -> DataAsset:
        existing = db.query(DataAsset).filter(
            DataAsset.organization_id == organization_id,
            DataAsset.asset_code == payload.asset_code,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Data asset with code '{payload.asset_code}' already exists",
            )

        cls.validate_cross_module_references(
            db=db,
            organization_id=organization_id,
            business_process_id=payload.business_process_id,
            ai_system_id=payload.ai_system_id,
            vendor_id=payload.vendor_id,
        )

        asset = DataAsset(
            organization_id=organization_id,
            owner_id=owner_id,
            asset_code=payload.asset_code,
            name=payload.name,
            description=payload.description,
            data_sensitivity_level=payload.data_sensitivity_level,
            data_volume_range=payload.data_volume_range,
            storage_type=payload.storage_type,
            hosting_jurisdiction=payload.hosting_jurisdiction,
            is_encrypted_at_rest=payload.is_encrypted_at_rest,
            is_encrypted_in_transit=payload.is_encrypted_in_transit,
            is_pseudonymized=payload.is_pseudonymized,
            retention_period_months=payload.retention_period_months,
            business_process_id=payload.business_process_id,
            ai_system_id=payload.ai_system_id,
            vendor_id=payload.vendor_id,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=owner_id,
            action="CREATE",
            resource_type="DataAsset",
            resource_id=asset.id,
            details={"asset_code": asset.asset_code, "name": asset.name},
        )
        return asset

    @classmethod
    def get_data_asset(cls, db: Session, organization_id: int, asset_id: int) -> DataAsset:
        asset = db.query(DataAsset).filter(
            DataAsset.id == asset_id,
            DataAsset.organization_id == organization_id,
        ).first()
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data asset {asset_id} not found",
            )
        return asset

    @classmethod
    def list_data_assets(
        cls,
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        sensitivity: Optional[DataSensitivityLevel] = None,
    ) -> List[DataAsset]:
        query = db.query(DataAsset).filter(DataAsset.organization_id == organization_id)
        if sensitivity:
            query = query.filter(DataAsset.data_sensitivity_level == sensitivity)
        return query.offset(skip).limit(limit).all()

    @classmethod
    def update_data_asset(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        user_id: int,
        payload: DataAssetUpdate,
    ) -> DataAsset:
        asset = cls.get_data_asset(db, organization_id, asset_id)

        cls.validate_cross_module_references(
            db=db,
            organization_id=organization_id,
            business_process_id=payload.business_process_id,
            ai_system_id=payload.ai_system_id,
            vendor_id=payload.vendor_id,
        )

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(asset, key, value)
        asset.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="UPDATE",
            resource_type="DataAsset",
            resource_id=asset.id,
            details={"asset_code": asset.asset_code},
        )
        return asset

    @classmethod
    def delete_data_asset(cls, db: Session, organization_id: int, asset_id: int, user_id: int) -> None:
        asset = cls.get_data_asset(db, organization_id, asset_id)
        code = asset.asset_code
        db.delete(asset)
        db.commit()

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="DELETE",
            resource_type="DataAsset",
            resource_id=asset_id,
            details={"asset_code": code},
        )

    # ─── Processing Activity (RoPA) Operations ────────────────────────────────

    LEGAL_STATE_TRANSITIONS = {
        ProcessingLifecycleState.DRAFT: [
            ProcessingLifecycleState.DPO_REVIEW,
            ProcessingLifecycleState.ARCHIVED,
        ],
        ProcessingLifecycleState.DPO_REVIEW: [
            ProcessingLifecycleState.ACTIVE,
            ProcessingLifecycleState.DRAFT,
            ProcessingLifecycleState.SUSPENDED,
        ],
        ProcessingLifecycleState.ACTIVE: [
            ProcessingLifecycleState.SUSPENDED,
            ProcessingLifecycleState.ARCHIVED,
            ProcessingLifecycleState.RETIRED,
        ],
        ProcessingLifecycleState.SUSPENDED: [
            ProcessingLifecycleState.DPO_REVIEW,
            ProcessingLifecycleState.ARCHIVED,
            ProcessingLifecycleState.RETIRED,
        ],
        ProcessingLifecycleState.ARCHIVED: [
            ProcessingLifecycleState.RETIRED,
        ],
        ProcessingLifecycleState.RETIRED: [],  # Terminal immutable state
    }

    @classmethod
    def create_processing_activity(
        cls,
        db: Session,
        organization_id: int,
        owner_id: int,
        payload: ProcessingActivityCreate,
    ) -> ProcessingActivity:
        existing = db.query(ProcessingActivity).filter(
            ProcessingActivity.organization_id == organization_id,
            ProcessingActivity.activity_code == payload.activity_code,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Processing activity with code '{payload.activity_code}' already exists",
            )

        cls.validate_cross_module_references(
            db=db,
            organization_id=organization_id,
            business_process_id=payload.business_process_id,
            ai_system_id=payload.ai_system_id,
            vendor_id=payload.vendor_id,
        )

        activity = ProcessingActivity(
            organization_id=organization_id,
            owner_id=owner_id,
            activity_code=payload.activity_code,
            name=payload.name,
            purpose_description=payload.purpose_description,
            legal_basis=payload.legal_basis,
            data_subject_categories=payload.data_subject_categories,
            personal_data_categories=payload.personal_data_categories,
            is_special_category_data=payload.is_special_category_data,
            is_automated_decision_making=payload.is_automated_decision_making,
            is_large_scale_monitoring=payload.is_large_scale_monitoring,
            is_vulnerable_subjects=payload.is_vulnerable_subjects,
            is_cross_border_transfer=payload.is_cross_border_transfer,
            transfer_mechanism=payload.transfer_mechanism,
            destination_country=payload.destination_country,
            security_measures_summary=payload.security_measures_summary,
            data_controller_name=payload.data_controller_name,
            lifecycle_state=ProcessingLifecycleState.DRAFT,
            dpo_approval_status=PrivacyApprovalStatus.PENDING,
            business_process_id=payload.business_process_id,
            ai_system_id=payload.ai_system_id,
            vendor_id=payload.vendor_id,
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=owner_id,
            action="CREATE",
            resource_type="ProcessingActivity",
            resource_id=activity.id,
            details={"activity_code": activity.activity_code, "name": activity.name},
        )
        return activity

    @classmethod
    def get_processing_activity(cls, db: Session, organization_id: int, activity_id: int) -> ProcessingActivity:
        activity = db.query(ProcessingActivity).filter(
            ProcessingActivity.id == activity_id,
            ProcessingActivity.organization_id == organization_id,
        ).first()
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processing activity {activity_id} not found",
            )
        return activity

    @classmethod
    def list_processing_activities(
        cls,
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        lifecycle_state: Optional[ProcessingLifecycleState] = None,
        legal_basis: Optional[ProcessingLegalBasis] = None,
    ) -> List[ProcessingActivity]:
        query = db.query(ProcessingActivity).filter(ProcessingActivity.organization_id == organization_id)
        if lifecycle_state:
            query = query.filter(ProcessingActivity.lifecycle_state == lifecycle_state)
        if legal_basis:
            query = query.filter(ProcessingActivity.legal_basis == legal_basis)
        return query.offset(skip).limit(limit).all()

    @classmethod
    def update_processing_activity(
        cls,
        db: Session,
        organization_id: int,
        activity_id: int,
        user_id: int,
        payload: ProcessingActivityUpdate,
    ) -> ProcessingActivity:
        activity = cls.get_processing_activity(db, organization_id, activity_id)

        # Immutability check for RETIRED
        if activity.lifecycle_state == ProcessingLifecycleState.RETIRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Processing activity '{activity.activity_code}' is RETIRED and permanently immutable",
            )

        cls.validate_cross_module_references(
            db=db,
            organization_id=organization_id,
            business_process_id=payload.business_process_id,
            ai_system_id=payload.ai_system_id,
            vendor_id=payload.vendor_id,
        )

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(activity, key, value)
        activity.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(activity)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="UPDATE",
            resource_type="ProcessingActivity",
            resource_id=activity.id,
            details={"activity_code": activity.activity_code},
        )
        return activity

    @classmethod
    def update_processing_activity_status(
        cls,
        db: Session,
        organization_id: int,
        activity_id: int,
        user_id: int,
        payload: ProcessingActivityStatusUpdate,
    ) -> ProcessingActivity:
        activity = cls.get_processing_activity(db, organization_id, activity_id)

        # Immutability check
        if activity.lifecycle_state == ProcessingLifecycleState.RETIRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Processing activity '{activity.activity_code}' is RETIRED and cannot transition to other states",
            )

        target_state = payload.lifecycle_state
        allowed_targets = cls.LEGAL_STATE_TRANSITIONS.get(activity.lifecycle_state, [])

        if target_state not in allowed_targets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Illegal lifecycle transition from {activity.lifecycle_state.value} to {target_state.value}. Allowed: {[s.value for s in allowed_targets]}",
            )

        # Activation requires DPO approval
        if target_state == ProcessingLifecycleState.ACTIVE:
            if activity.dpo_approval_status != PrivacyApprovalStatus.APPROVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot transition processing activity to ACTIVE without prior DPO approval",
                )

        old_state = activity.lifecycle_state
        activity.lifecycle_state = target_state
        activity.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(activity)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="STATUS_CHANGE",
            resource_type="ProcessingActivity",
            resource_id=activity.id,
            details={"old_state": old_state.value, "new_state": target_state.value},
        )
        return activity

    @classmethod
    def delete_processing_activity(cls, db: Session, organization_id: int, activity_id: int, user_id: int) -> None:
        activity = cls.get_processing_activity(db, organization_id, activity_id)

        if activity.lifecycle_state == ProcessingLifecycleState.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete an ACTIVE processing activity. Suspend or Retire it first.",
            )

        code = activity.activity_code
        db.delete(activity)
        db.commit()

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="DELETE",
            resource_type="ProcessingActivity",
            resource_id=activity_id,
            details={"activity_code": code},
        )

    # ─── DPIA Assessment Operations ───────────────────────────────────────────

    @classmethod
    def create_dpia_assessment(
        cls,
        db: Session,
        organization_id: int,
        created_by_id: int,
        payload: DPIACreate,
    ) -> DPIAAssessment:
        activity = cls.get_processing_activity(db, organization_id, payload.processing_activity_id)

        if activity.lifecycle_state == ProcessingLifecycleState.RETIRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot create DPIA for a RETIRED processing activity",
            )

        existing = db.query(DPIAAssessment).filter(
            DPIAAssessment.organization_id == organization_id,
            DPIAAssessment.assessment_code == payload.assessment_code,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"DPIA assessment with code '{payload.assessment_code}' already exists",
            )

        cls.validate_cross_module_references(
            db=db,
            organization_id=organization_id,
            remediation_plan_id=payload.remediation_plan_id,
        )

        # Inherent Risk Calculation
        sensitivity = DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI if activity.is_special_category_data else DataSensitivityLevel.RESTRICTED_PII
        irs = cls.calculate_dpia_inherent_risk(
            sensitivity_level=sensitivity,
            volume_tier="HIGH" if activity.is_large_scale_monitoring else "LOW",
            is_special_category=activity.is_special_category_data,
            automated_decision_making_risk=payload.automated_decision_making_risk or activity.is_automated_decision_making,
            large_scale_monitoring_risk=payload.large_scale_monitoring_risk or activity.is_large_scale_monitoring,
            vulnerable_subjects_risk=payload.vulnerable_subjects_risk or activity.is_vulnerable_subjects,
        )

        # Residual Risk Calculation
        rrs = cls.calculate_dpia_residual_risk(
            inherent_risk_score=irs,
            safeguards_mitigation_score=payload.safeguards_mitigation_score,
            has_threat_exposure=False,
        )
        risk_band = cls.determine_dpia_risk_band(rrs)

        dpia = DPIAAssessment(
            organization_id=organization_id,
            created_by_id=created_by_id,
            assessment_code=payload.assessment_code,
            processing_activity_id=payload.processing_activity_id,
            necessity_proportionality_score=payload.necessity_proportionality_score,
            data_subject_rights_score=payload.data_subject_rights_score,
            safeguards_mitigation_score=payload.safeguards_mitigation_score,
            inherent_risk_score=irs,
            residual_risk_score=rrs,
            risk_band=risk_band,
            automated_decision_making_risk=payload.automated_decision_making_risk,
            large_scale_monitoring_risk=payload.large_scale_monitoring_risk,
            vulnerable_subjects_risk=payload.vulnerable_subjects_risk,
            dpo_consultation_status=PrivacyApprovalStatus.PENDING,
            prior_consultation_required=payload.prior_consultation_required or (rrs >= 80.0),
            remediation_plan_id=payload.remediation_plan_id,
        )
        db.add(dpia)
        db.commit()
        db.refresh(dpia)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=created_by_id,
            action="CREATE",
            resource_type="DPIAAssessment",
            resource_id=dpia.id,
            details={"assessment_code": dpia.assessment_code, "irs": irs, "rrs": rrs},
        )
        return dpia

    @classmethod
    def get_dpia_assessment(cls, db: Session, organization_id: int, dpia_id: int) -> DPIAAssessment:
        dpia = db.query(DPIAAssessment).filter(
            DPIAAssessment.id == dpia_id,
            DPIAAssessment.organization_id == organization_id,
        ).first()
        if not dpia:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DPIA assessment {dpia_id} not found",
            )
        return dpia

    @classmethod
    def list_dpia_assessments(
        cls,
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        activity_id: Optional[int] = None,
        risk_band: Optional[DPIARiskBand] = None,
        status_filter: Optional[PrivacyApprovalStatus] = None,
    ) -> List[DPIAAssessment]:
        query = db.query(DPIAAssessment).filter(DPIAAssessment.organization_id == organization_id)
        if activity_id:
            query = query.filter(DPIAAssessment.processing_activity_id == activity_id)
        if risk_band:
            query = query.filter(DPIAAssessment.risk_band == risk_band)
        if status_filter:
            query = query.filter(DPIAAssessment.dpo_consultation_status == status_filter)
        return query.offset(skip).limit(limit).all()

    @classmethod
    def update_dpia_assessment(
        cls,
        db: Session,
        organization_id: int,
        dpia_id: int,
        user_id: int,
        payload: DPIAUpdate,
    ) -> DPIAAssessment:
        dpia = cls.get_dpia_assessment(db, organization_id, dpia_id)

        if dpia.dpo_consultation_status in [PrivacyApprovalStatus.APPROVED, PrivacyApprovalStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify finalized DPIA assessment '{dpia.assessment_code}'",
            )

        cls.validate_cross_module_references(
            db=db,
            organization_id=organization_id,
            remediation_plan_id=payload.remediation_plan_id,
        )

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(dpia, key, value)

        # Recalculate scores server-side
        activity = dpia.processing_activity
        sensitivity = DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI if activity.is_special_category_data else DataSensitivityLevel.RESTRICTED_PII
        irs = cls.calculate_dpia_inherent_risk(
            sensitivity_level=sensitivity,
            volume_tier="HIGH" if activity.is_large_scale_monitoring else "LOW",
            is_special_category=activity.is_special_category_data,
            automated_decision_making_risk=dpia.automated_decision_making_risk,
            large_scale_monitoring_risk=dpia.large_scale_monitoring_risk,
            vulnerable_subjects_risk=dpia.vulnerable_subjects_risk,
        )
        rrs = cls.calculate_dpia_residual_risk(
            inherent_risk_score=irs,
            safeguards_mitigation_score=float(dpia.safeguards_mitigation_score),
            has_threat_exposure=False,
        )
        dpia.inherent_risk_score = irs
        dpia.residual_risk_score = rrs
        dpia.risk_band = cls.determine_dpia_risk_band(rrs)
        dpia.prior_consultation_required = dpia.prior_consultation_required or (rrs >= 80.0)
        dpia.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(dpia)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="UPDATE",
            resource_type="DPIAAssessment",
            resource_id=dpia.id,
            details={"assessment_code": dpia.assessment_code, "new_rrs": rrs},
        )
        return dpia

    @classmethod
    def review_dpia_assessment(
        cls,
        db: Session,
        organization_id: int,
        dpia_id: int,
        reviewer_id: int,
        review_data: DPIAReviewRequest,
    ) -> DPIAAssessment:
        dpia = cls.get_dpia_assessment(db, organization_id, dpia_id)

        # Four-Eyes Segregation of Duties Enforcement
        if dpia.created_by_id == reviewer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Segregation of Duties Violation: The creator of a DPIA cannot serve as the reviewing DPO.",
            )

        # Prevent replay / re-review
        if dpia.dpo_consultation_status in [PrivacyApprovalStatus.APPROVED, PrivacyApprovalStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"DPIA assessment '{dpia.assessment_code}' has already been finalized with status '{dpia.dpo_consultation_status.value}'",
            )

        decision = review_data.decision
        if decision not in [PrivacyApprovalStatus.APPROVED, PrivacyApprovalStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decision must be either APPROVED or REJECTED",
            )

        dpia.dpo_consultation_status = decision
        dpia.dpo_recommendation_notes = review_data.recommendation_notes
        dpia.dpo_reviewed_by_id = reviewer_id
        dpia.dpo_reviewed_at = datetime.utcnow()
        dpia.updated_at = datetime.utcnow()

        # Update parent activity DPO approval status if approved
        activity = dpia.processing_activity
        if decision == PrivacyApprovalStatus.APPROVED:
            activity.dpo_approval_status = PrivacyApprovalStatus.APPROVED
            activity.approved_by_dpo_id = reviewer_id
            activity.approved_at = datetime.utcnow()
            if activity.lifecycle_state == ProcessingLifecycleState.DPO_REVIEW:
                activity.lifecycle_state = ProcessingLifecycleState.ACTIVE

        db.commit()
        db.refresh(dpia)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=reviewer_id,
            action="DPO_REVIEW",
            resource_type="DPIAAssessment",
            resource_id=dpia.id,
            details={"assessment_code": dpia.assessment_code, "decision": decision.value},
        )
        return dpia

    # ─── Data Transfer Assessment Operations ──────────────────────────────────

    @classmethod
    def create_data_transfer(
        cls,
        db: Session,
        organization_id: int,
        requested_by_id: int,
        payload: DataTransferCreate,
    ) -> DataTransferAssessment:
        activity = cls.get_processing_activity(db, organization_id, payload.processing_activity_id)

        existing = db.query(DataTransferAssessment).filter(
            DataTransferAssessment.organization_id == organization_id,
            DataTransferAssessment.transfer_code == payload.transfer_code,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Data transfer assessment with code '{payload.transfer_code}' already exists",
            )

        tri = cls.calculate_transfer_risk_index(
            destination_tier=payload.destination_jurisdiction_tier,
            mechanism=payload.transfer_mechanism,
            supplementary_measures_score=payload.supplementary_measures_score,
        )

        transfer = DataTransferAssessment(
            organization_id=organization_id,
            requested_by_id=requested_by_id,
            transfer_code=payload.transfer_code,
            processing_activity_id=payload.processing_activity_id,
            source_country=payload.source_country,
            destination_country=payload.destination_country,
            destination_jurisdiction_tier=payload.destination_jurisdiction_tier,
            transfer_mechanism=payload.transfer_mechanism,
            supplementary_safeguards_description=payload.supplementary_safeguards_description,
            supplementary_measures_score=payload.supplementary_measures_score,
            government_access_risk_score=payload.government_access_risk_score,
            legal_remedies_score=payload.legal_remedies_score,
            transfer_risk_index=tri,
            approval_status=PrivacyApprovalStatus.PENDING,
            audit_notes=payload.audit_notes,
        )
        db.add(transfer)
        db.commit()
        db.refresh(transfer)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=requested_by_id,
            action="CREATE",
            resource_type="DataTransferAssessment",
            resource_id=transfer.id,
            details={"transfer_code": transfer.transfer_code, "tri": tri},
        )
        return transfer

    @classmethod
    def get_data_transfer(cls, db: Session, organization_id: int, transfer_id: int) -> DataTransferAssessment:
        transfer = db.query(DataTransferAssessment).filter(
            DataTransferAssessment.id == transfer_id,
            DataTransferAssessment.organization_id == organization_id,
        ).first()
        if not transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data transfer assessment {transfer_id} not found",
            )
        return transfer

    @classmethod
    def list_data_transfers(
        cls,
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        activity_id: Optional[int] = None,
        tier: Optional[JurisdictionRiskTier] = None,
    ) -> List[DataTransferAssessment]:
        query = db.query(DataTransferAssessment).filter(DataTransferAssessment.organization_id == organization_id)
        if activity_id:
            query = query.filter(DataTransferAssessment.processing_activity_id == activity_id)
        if tier:
            query = query.filter(DataTransferAssessment.destination_jurisdiction_tier == tier)
        return query.offset(skip).limit(limit).all()

    @classmethod
    def review_data_transfer(
        cls,
        db: Session,
        organization_id: int,
        transfer_id: int,
        reviewer_id: int,
        review_data: DataTransferReviewRequest,
    ) -> DataTransferAssessment:
        transfer = cls.get_data_transfer(db, organization_id, transfer_id)

        # Four-Eyes Segregation of Duties Enforcement
        if transfer.requested_by_id == reviewer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Segregation of Duties Violation: The requester of a data transfer assessment cannot approve it.",
            )

        # Prevent replay / re-review
        if transfer.approval_status in [PrivacyApprovalStatus.APPROVED, PrivacyApprovalStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Data transfer assessment '{transfer.transfer_code}' has already been finalized with status '{transfer.approval_status.value}'",
            )

        decision = review_data.decision
        if decision not in [PrivacyApprovalStatus.APPROVED, PrivacyApprovalStatus.REJECTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decision must be either APPROVED or REJECTED",
            )

        transfer.approval_status = decision
        transfer.approved_by_id = reviewer_id
        transfer.approved_at = datetime.utcnow()
        transfer.audit_notes = review_data.reviewer_notes
        transfer.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(transfer)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            user_id=reviewer_id,
            action="TRANSFER_REVIEW",
            resource_type="DataTransferAssessment",
            resource_id=transfer.id,
            details={"transfer_code": transfer.transfer_code, "decision": decision.value},
        )
        return transfer

    # ─── Posture Summary Operations ───────────────────────────────────────────

    @classmethod
    def get_privacy_posture_summary(cls, db: Session, organization_id: int) -> PrivacyPostureSummaryResponse:
        total_assets = db.query(func.count(DataAsset.id)).filter(DataAsset.organization_id == organization_id).scalar() or 0
        total_activities = db.query(func.count(ProcessingActivity.id)).filter(ProcessingActivity.organization_id == organization_id).scalar() or 0
        active_activities = db.query(func.count(ProcessingActivity.id)).filter(
            ProcessingActivity.organization_id == organization_id,
            ProcessingActivity.lifecycle_state == ProcessingLifecycleState.ACTIVE,
        ).scalar() or 0

        high_risk_activities = db.query(func.count(ProcessingActivity.id)).filter(
            ProcessingActivity.organization_id == organization_id,
            (ProcessingActivity.is_special_category_data == True) |
            (ProcessingActivity.is_automated_decision_making == True) |
            (ProcessingActivity.is_large_scale_monitoring == True),
        ).scalar() or 0

        cross_border_count = db.query(func.count(DataTransferAssessment.id)).filter(
            DataTransferAssessment.organization_id == organization_id,
        ).scalar() or 0

        pending_dpia = db.query(func.count(DPIAAssessment.id)).filter(
            DPIAAssessment.organization_id == organization_id,
            DPIAAssessment.dpo_consultation_status == PrivacyApprovalStatus.PENDING,
        ).scalar() or 0

        pending_transfers = db.query(func.count(DataTransferAssessment.id)).filter(
            DataTransferAssessment.organization_id == organization_id,
            DataTransferAssessment.approval_status == PrivacyApprovalStatus.PENDING,
        ).scalar() or 0

        avg_rrs = db.query(func.avg(DPIAAssessment.residual_risk_score)).filter(
            DPIAAssessment.organization_id == organization_id,
        ).scalar() or 0.0

        # Risk band distribution
        bands = db.query(DPIAAssessment.risk_band, func.count(DPIAAssessment.id)).filter(
            DPIAAssessment.organization_id == organization_id,
        ).group_by(DPIAAssessment.risk_band).all()
        risk_dist = {b.value: 0 for b in DPIARiskBand}
        for band, count in bands:
            if band:
                risk_dist[band.value] = count

        # Legal basis distribution
        bases = db.query(ProcessingActivity.legal_basis, func.count(ProcessingActivity.id)).filter(
            ProcessingActivity.organization_id == organization_id,
        ).group_by(ProcessingActivity.legal_basis).all()
        basis_dist = {b.value: 0 for b in ProcessingLegalBasis}
        for base, count in bases:
            if base:
                basis_dist[base.value] = count

        # Sensitivity distribution
        sensitivities = db.query(DataAsset.data_sensitivity_level, func.count(DataAsset.id)).filter(
            DataAsset.organization_id == organization_id,
        ).group_by(DataAsset.data_sensitivity_level).all()
        sens_dist = {s.value: 0 for s in DataSensitivityLevel}
        for sens, count in sensitivities:
            if sens:
                sens_dist[sens.value] = count

        return PrivacyPostureSummaryResponse(
            total_data_assets=total_assets,
            total_processing_activities=total_activities,
            active_ropa_count=active_activities,
            high_risk_processing_count=high_risk_activities,
            cross_border_transfers_count=cross_border_count,
            pending_dpia_approvals=pending_dpia,
            pending_transfer_approvals=pending_transfers,
            average_residual_risk_score=round(float(avg_rrs), 2),
            risk_band_distribution=risk_dist,
            legal_basis_distribution=basis_dist,
            sensitivity_distribution=sens_dist,
        )
