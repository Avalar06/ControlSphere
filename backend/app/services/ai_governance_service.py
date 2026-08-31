from datetime import datetime
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.ai_governance import (
    AIApprovalStatusEnum,
    AIAutonomyLevelEnum,
    AIDataSensitivityEnum,
    AIDeploymentApproval,
    AILifecycleStateEnum,
    AIModelCard,
    AIRegulatoryTierEnum,
    AISystem,
    AISystemTypeEnum,
)
from app.models.resilience import BusinessProcess, CriticalityTierEnum
from app.models.remediation import RemediationPlan
from app.models.user import User
from app.models.tprm import Vendor
from app.schemas.ai_governance import (
    AIDeploymentApprovalCreate,
    AIDeploymentApprovalReviewRequest,
    AIModelCardCreate,
    AIPostureSummaryResponse,
    AISystemCreate,
    AISystemUpdate,
)
from app.services.audit_service import AuditService


class AIGovernanceService:
    # ─── Mathematical Engine ──────────────────────────────────────────────────

    BASE_RISK_MAP = {
        AIRegulatoryTierEnum.PROHIBITED: 100.0,
        AIRegulatoryTierEnum.HIGH_RISK: 65.0,
        AIRegulatoryTierEnum.GPAI_SYSTEMIC_RISK: 50.0,
        AIRegulatoryTierEnum.LIMITED_RISK: 25.0,
        AIRegulatoryTierEnum.MINIMAL_RISK: 5.0,
    }

    AUTONOMY_MULTIPLIER_MAP = {
        AIAutonomyLevelEnum.FULL_AUTONOMY: 1.40,
        AIAutonomyLevelEnum.HUMAN_ON_THE_LOOP: 1.20,
        AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP: 1.00,
        AIAutonomyLevelEnum.NO_AUTONOMY: 0.80,
    }

    PROCESS_TIER_MULTIPLIER_MAP = {
        "TIER_1": 1.25,
        "TIER_2": 1.15,
        "TIER_3": 1.05,
        "TIER_4": 1.00,
    }

    DATA_SENSITIVITY_ADDON_MAP = {
        AIDataSensitivityEnum.RESTRICTED_PII_PHI: 15.0,
        AIDataSensitivityEnum.CONFIDENTIAL: 8.0,
        AIDataSensitivityEnum.INTERNAL: 2.0,
        AIDataSensitivityEnum.PUBLIC: 0.0,
    }

    @classmethod
    def calculate_algorithmic_risk_index(
        cls,
        regulatory_tier: AIRegulatoryTierEnum,
        autonomy_level: AIAutonomyLevelEnum,
        data_sensitivity: AIDataSensitivityEnum,
        process_tier: Optional[str] = None,
        hallucination_rate_percent: float = 0.0,
        prompt_injection_resistance_score: float = 100.0,
    ) -> float:
        """
        Calculates server-authoritative Algorithmic Risk Index (ARI) on 0.00 - 100.00 scale:
        ARI = min(100.00, (BaseRisk * AutonomyMult * ProcessTierMult) + SafetyPenalty)
        """
        base_risk = cls.BASE_RISK_MAP.get(regulatory_tier, 25.0)
        autonomy_mult = cls.AUTONOMY_MULTIPLIER_MAP.get(autonomy_level, 1.00)

        # Normalize process tier string
        norm_tier = str(process_tier).upper() if process_tier else "TIER_4"
        process_mult = cls.PROCESS_TIER_MULTIPLIER_MAP.get(norm_tier, 1.00)

        # Safety & Telemetry Penalty
        data_addon = cls.DATA_SENSITIVITY_ADDON_MAP.get(data_sensitivity, 2.0)
        hallucination_penalty = max(0.0, min(100.0, float(hallucination_rate_percent))) * 0.20
        injection_penalty = max(0.0, min(100.0, 100.0 - float(prompt_injection_resistance_score))) * 0.15
        safety_penalty = hallucination_penalty + injection_penalty + data_addon

        raw_ari = (base_risk * autonomy_mult * process_mult) + safety_penalty
        return min(100.00, max(0.00, round(raw_ari, 2)))

    @classmethod
    def calculate_eu_compliance_score(
        cls,
        regulatory_tier: AIRegulatoryTierEnum,
        autonomy_level: AIAutonomyLevelEnum,
        hallucination_rate_percent: float = 0.0,
        prompt_injection_resistance_score: float = 100.0,
    ) -> float:
        """
        Calculates EU AI Act conformity readiness score on 0.00 - 100.00% scale.
        """
        if regulatory_tier == AIRegulatoryTierEnum.PROHIBITED:
            return 0.00

        base_readiness = {
            AIRegulatoryTierEnum.MINIMAL_RISK: 100.00,
            AIRegulatoryTierEnum.LIMITED_RISK: 85.00,
            AIRegulatoryTierEnum.GPAI_SYSTEMIC_RISK: 70.00,
            AIRegulatoryTierEnum.HIGH_RISK: 50.00,
        }.get(regulatory_tier, 50.00)

        hallucination_deduction = max(0.0, min(100.0, float(hallucination_rate_percent))) * 0.25
        injection_deduction = max(0.0, min(100.0, 100.0 - float(prompt_injection_resistance_score))) * 0.20
        hitl_bonus = 10.0 if autonomy_level in [AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP, AIAutonomyLevelEnum.NO_AUTONOMY] else 0.0

        score = base_readiness - hallucination_deduction - injection_deduction + hitl_bonus
        return min(100.00, max(0.00, round(score, 2)))

    # ─── AI System Operations ─────────────────────────────────────────────────

    @classmethod
    def create_ai_system(
        cls,
        db: Session,
        organization_id: int,
        data: AISystemCreate,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AISystem:
        # Check system_code uniqueness within organization
        existing = (
            db.query(AISystem)
            .filter(
                AISystem.organization_id == organization_id,
                AISystem.system_code == data.system_code.strip(),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"AI System with code '{data.system_code}' already exists in this organization.",
            )

        # Cross-module validation: Business Process
        process_tier: Optional[str] = None
        if data.business_process_id:
            bp = (
                db.query(BusinessProcess)
                .filter(
                    BusinessProcess.id == data.business_process_id,
                    BusinessProcess.organization_id == organization_id,
                )
                .first()
            )
            if not bp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Business process #{data.business_process_id} not found in this organization.",
                )
            process_tier = bp.criticality_tier.value if hasattr(bp.criticality_tier, "value") else str(bp.criticality_tier)

        # Cross-module validation: Vendor
        if data.vendor_id:
            vendor = (
                db.query(Vendor)
                .filter(
                    Vendor.id == data.vendor_id,
                    Vendor.organization_id == organization_id,
                )
                .first()
            )
            if not vendor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vendor #{data.vendor_id} not found in this organization.",
                )

        # Cross-module validation: Remediation Plan
        if data.remediation_plan_id:
            plan = (
                db.query(RemediationPlan)
                .filter(
                    RemediationPlan.id == data.remediation_plan_id,
                    RemediationPlan.organization_id == organization_id,
                )
                .first()
            )
            if not plan:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Remediation plan #{data.remediation_plan_id} not found in this organization.",
                )

        is_prohibited = (data.regulatory_tier == AIRegulatoryTierEnum.PROHIBITED)
        requires_conformity = data.regulatory_tier in [AIRegulatoryTierEnum.HIGH_RISK, AIRegulatoryTierEnum.GPAI_SYSTEMIC_RISK]

        # Calculate scores
        ari = cls.calculate_algorithmic_risk_index(
            regulatory_tier=data.regulatory_tier,
            autonomy_level=data.autonomy_level,
            data_sensitivity=data.data_sensitivity,
            process_tier=process_tier,
        )
        eu_score = cls.calculate_eu_compliance_score(
            regulatory_tier=data.regulatory_tier,
            autonomy_level=data.autonomy_level,
        )

        ai_sys = AISystem(
            organization_id=organization_id,
            system_code=data.system_code.strip(),
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            system_type=data.system_type,
            lifecycle_state=AILifecycleStateEnum.DEVELOPMENT,
            regulatory_tier=data.regulatory_tier,
            autonomy_level=data.autonomy_level,
            data_sensitivity=data.data_sensitivity,
            hosting_type=data.hosting_type,
            foundation_model_name=data.foundation_model_name.strip() if data.foundation_model_name else None,
            model_version=data.model_version.strip() if data.model_version else None,
            training_data_cutoff=data.training_data_cutoff.strip() if data.training_data_cutoff else None,
            parameters_billion=data.parameters_billion,
            context_window_tokens=data.context_window_tokens,
            compute_flops_exponent=data.compute_flops_exponent,
            algorithmic_risk_index=ari,
            eu_compliance_score=eu_score,
            is_prohibited_practice=is_prohibited,
            requires_conformity_assessment=requires_conformity,
            business_process_id=data.business_process_id,
            vendor_id=data.vendor_id,
            remediation_plan_id=data.remediation_plan_id,
            owner_id=current_user.id,
        )
        db.add(ai_sys)
        db.commit()
        db.refresh(ai_sys)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="CREATE",
            resource_type="AISystem",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(ai_sys.id),
            details={
                "system_code": ai_sys.system_code,
                "name": ai_sys.name,
                "regulatory_tier": ai_sys.regulatory_tier.value,
                "algorithmic_risk_index": float(ai_sys.algorithmic_risk_index),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return ai_sys

    @classmethod
    def get_ai_system(cls, db: Session, organization_id: int, system_id: int) -> AISystem:
        ai_sys = (
            db.query(AISystem)
            .filter(AISystem.id == system_id, AISystem.organization_id == organization_id)
            .first()
        )
        if not ai_sys:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AI System #{system_id} not found in this organization.",
            )
        return ai_sys

    @classmethod
    def list_ai_systems(
        cls,
        db: Session,
        organization_id: int,
        regulatory_tier: Optional[AIRegulatoryTierEnum] = None,
        lifecycle_state: Optional[AILifecycleStateEnum] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AISystem]:
        query = db.query(AISystem).filter(AISystem.organization_id == organization_id)
        if regulatory_tier:
            query = query.filter(AISystem.regulatory_tier == regulatory_tier)
        if lifecycle_state:
            query = query.filter(AISystem.lifecycle_state == lifecycle_state)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                (AISystem.system_code.ilike(term))
                | (AISystem.name.ilike(term))
                | (AISystem.description.ilike(term))
                | (AISystem.foundation_model_name.ilike(term))
            )
        return query.order_by(AISystem.id.desc()).offset(skip).limit(limit).all()

    @classmethod
    def update_ai_system(
        cls,
        db: Session,
        organization_id: int,
        system_id: int,
        data: AISystemUpdate,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AISystem:
        ai_sys = cls.get_ai_system(db, organization_id, system_id)

        if ai_sys.lifecycle_state == AILifecycleStateEnum.DECOMMISSIONED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Decommissioned AI systems are permanently immutable.",
            )

        old_values = {
            "name": ai_sys.name,
            "regulatory_tier": ai_sys.regulatory_tier.value,
            "algorithmic_risk_index": float(ai_sys.algorithmic_risk_index),
        }

        # Validate cross-module updates
        process_tier: Optional[str] = None
        if data.business_process_id is not None:
            if data.business_process_id > 0:
                bp = (
                    db.query(BusinessProcess)
                    .filter(
                        BusinessProcess.id == data.business_process_id,
                        BusinessProcess.organization_id == organization_id,
                    )
                    .first()
                )
                if not bp:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Business process #{data.business_process_id} not found.",
                    )
                process_tier = bp.criticality_tier.value if hasattr(bp.criticality_tier, "value") else str(bp.criticality_tier)
                ai_sys.business_process_id = data.business_process_id
            else:
                ai_sys.business_process_id = None
        elif ai_sys.business_process_id:
            bp = db.query(BusinessProcess).filter(BusinessProcess.id == ai_sys.business_process_id).first()
            if bp:
                process_tier = bp.criticality_tier.value if hasattr(bp.criticality_tier, "value") else str(bp.criticality_tier)

        if data.vendor_id is not None:
            if data.vendor_id > 0:
                vendor = db.query(Vendor).filter(Vendor.id == data.vendor_id, Vendor.organization_id == organization_id).first()
                if not vendor:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vendor #{data.vendor_id} not found.")
                ai_sys.vendor_id = data.vendor_id
            else:
                ai_sys.vendor_id = None

        if data.remediation_plan_id is not None:
            if data.remediation_plan_id > 0:
                plan = db.query(RemediationPlan).filter(RemediationPlan.id == data.remediation_plan_id, RemediationPlan.organization_id == organization_id).first()
                if not plan:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Remediation plan #{data.remediation_plan_id} not found.")
                ai_sys.remediation_plan_id = data.remediation_plan_id
            else:
                ai_sys.remediation_plan_id = None

        # Field updates
        if data.name is not None:
            ai_sys.name = data.name.strip()
        if data.description is not None:
            ai_sys.description = data.description.strip() if data.description else None
        if data.system_type is not None:
            ai_sys.system_type = data.system_type
        if data.regulatory_tier is not None:
            ai_sys.regulatory_tier = data.regulatory_tier
            ai_sys.is_prohibited_practice = (data.regulatory_tier == AIRegulatoryTierEnum.PROHIBITED)
            ai_sys.requires_conformity_assessment = data.regulatory_tier in [AIRegulatoryTierEnum.HIGH_RISK, AIRegulatoryTierEnum.GPAI_SYSTEMIC_RISK]
        if data.autonomy_level is not None:
            ai_sys.autonomy_level = data.autonomy_level
        if data.data_sensitivity is not None:
            ai_sys.data_sensitivity = data.data_sensitivity
        if data.hosting_type is not None:
            ai_sys.hosting_type = data.hosting_type
        if data.foundation_model_name is not None:
            ai_sys.foundation_model_name = data.foundation_model_name.strip() if data.foundation_model_name else None
        if data.model_version is not None:
            ai_sys.model_version = data.model_version.strip() if data.model_version else None
        if data.training_data_cutoff is not None:
            ai_sys.training_data_cutoff = data.training_data_cutoff.strip() if data.training_data_cutoff else None
        if data.parameters_billion is not None:
            ai_sys.parameters_billion = data.parameters_billion
        if data.context_window_tokens is not None:
            ai_sys.context_window_tokens = data.context_window_tokens
        if data.compute_flops_exponent is not None:
            ai_sys.compute_flops_exponent = data.compute_flops_exponent

        # Fetch latest safety metrics from latest model card if available
        latest_card = (
            db.query(AIModelCard)
            .filter(AIModelCard.ai_system_id == ai_sys.id)
            .order_by(AIModelCard.id.desc())
            .first()
        )
        hallucination = float(latest_card.hallucination_rate_percent) if latest_card else 0.0
        injection_res = float(latest_card.prompt_injection_resistance_score) if latest_card else 100.0

        ai_sys.algorithmic_risk_index = cls.calculate_algorithmic_risk_index(
            regulatory_tier=ai_sys.regulatory_tier,
            autonomy_level=ai_sys.autonomy_level,
            data_sensitivity=ai_sys.data_sensitivity,
            process_tier=process_tier,
            hallucination_rate_percent=hallucination,
            prompt_injection_resistance_score=injection_res,
        )
        ai_sys.eu_compliance_score = cls.calculate_eu_compliance_score(
            regulatory_tier=ai_sys.regulatory_tier,
            autonomy_level=ai_sys.autonomy_level,
            hallucination_rate_percent=hallucination,
            prompt_injection_resistance_score=injection_res,
        )
        ai_sys.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(ai_sys)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="UPDATE",
            resource_type="AISystem",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(ai_sys.id),
            details={
                "old_values": old_values,
                "new_values": {
                    "name": ai_sys.name,
                    "regulatory_tier": ai_sys.regulatory_tier.value,
                    "algorithmic_risk_index": float(ai_sys.algorithmic_risk_index),
                },
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return ai_sys

    @classmethod
    def delete_ai_system(
        cls,
        db: Session,
        organization_id: int,
        system_id: int,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        ai_sys = cls.get_ai_system(db, organization_id, system_id)
        if ai_sys.lifecycle_state == AILifecycleStateEnum.PRODUCTION:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active production AI systems cannot be deleted directly; transition to DECOMMISSIONED first.",
            )

        system_code = ai_sys.system_code
        db.delete(ai_sys)
        db.commit()

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="DELETE",
            resource_type="AISystem",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(system_id),
            details={"system_code": system_code},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ─── Lifecycle State Machine ──────────────────────────────────────────────

    LEGAL_TRANSITIONS = {
        AILifecycleStateEnum.DEVELOPMENT: [
            AILifecycleStateEnum.VALIDATION,
            AILifecycleStateEnum.REJECTED,
            AILifecycleStateEnum.DECOMMISSIONED,
        ],
        AILifecycleStateEnum.VALIDATION: [
            AILifecycleStateEnum.ETHICAL_REVIEW,
            AILifecycleStateEnum.DEVELOPMENT,
            AILifecycleStateEnum.REJECTED,
            AILifecycleStateEnum.DECOMMISSIONED,
        ],
        AILifecycleStateEnum.ETHICAL_REVIEW: [
            AILifecycleStateEnum.APPROVED_STAGING,
            AILifecycleStateEnum.VALIDATION,
            AILifecycleStateEnum.REJECTED,
            AILifecycleStateEnum.DECOMMISSIONED,
        ],
        AILifecycleStateEnum.APPROVED_STAGING: [
            AILifecycleStateEnum.PRODUCTION,
            AILifecycleStateEnum.VALIDATION,
            AILifecycleStateEnum.DECOMMISSIONED,
        ],
        AILifecycleStateEnum.PRODUCTION: [
            AILifecycleStateEnum.ETHICAL_REVIEW,
            AILifecycleStateEnum.DECOMMISSIONED,
        ],
        AILifecycleStateEnum.REJECTED: [
            AILifecycleStateEnum.DEVELOPMENT,
            AILifecycleStateEnum.DECOMMISSIONED,
        ],
        AILifecycleStateEnum.DECOMMISSIONED: [],  # Permanently immutable
    }

    @classmethod
    def update_lifecycle_state(
        cls,
        db: Session,
        organization_id: int,
        system_id: int,
        target_state: AILifecycleStateEnum,
        notes: Optional[str],
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AISystem:
        ai_sys = cls.get_ai_system(db, organization_id, system_id)

        if ai_sys.lifecycle_state == AILifecycleStateEnum.DECOMMISSIONED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Decommissioned AI systems are permanently immutable.",
            )

        if target_state == ai_sys.lifecycle_state:
            return ai_sys

        allowed_targets = cls.LEGAL_TRANSITIONS.get(ai_sys.lifecycle_state, [])
        if target_state not in allowed_targets:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Illegal lifecycle transition from '{ai_sys.lifecycle_state.value}' to '{target_state.value}'.",
            )

        # Production Guardrail: Prohibited AI cannot be in production
        if target_state == AILifecycleStateEnum.PRODUCTION and ai_sys.is_prohibited_practice:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prohibited AI systems cannot be deployed to PRODUCTION under EU AI Act Article 5.",
            )

        # Four-Eyes Deployment Gate: Promoting to APPROVED_STAGING or PRODUCTION requires approved deployment request
        if target_state in [AILifecycleStateEnum.APPROVED_STAGING, AILifecycleStateEnum.PRODUCTION]:
            target_env = "PRODUCTION" if target_state == AILifecycleStateEnum.PRODUCTION else "STAGING"
            approved_req = (
                db.query(AIDeploymentApproval)
                .filter(
                    AIDeploymentApproval.ai_system_id == ai_sys.id,
                    AIDeploymentApproval.organization_id == organization_id,
                    AIDeploymentApproval.approval_status == AIApprovalStatusEnum.APPROVED,
                    AIDeploymentApproval.target_environment == target_env,
                )
                .first()
            )
            if not approved_req:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot transition to '{target_state.value}' without an independent APPROVED deployment approval for target environment '{target_env}'.",
                )

        old_state = ai_sys.lifecycle_state.value
        ai_sys.lifecycle_state = target_state
        ai_sys.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ai_sys)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="STATE_TRANSITION",
            resource_type="AISystem",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(ai_sys.id),
            details={
                "old_state": old_state,
                "new_state": target_state.value,
                "notes": notes,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return ai_sys

    # ─── Model Card Management ────────────────────────────────────────────────

    @classmethod
    def create_model_card(
        cls,
        db: Session,
        organization_id: int,
        system_id: int,
        data: AIModelCardCreate,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AIModelCard:
        ai_sys = cls.get_ai_system(db, organization_id, system_id)
        if ai_sys.lifecycle_state == AILifecycleStateEnum.DECOMMISSIONED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot attach model cards to decommissioned AI systems.",
            )

        existing = (
            db.query(AIModelCard)
            .filter(
                AIModelCard.ai_system_id == system_id,
                AIModelCard.version == data.version.strip(),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Model card version '{data.version}' already exists for this AI system.",
            )

        card = AIModelCard(
            organization_id=organization_id,
            ai_system_id=system_id,
            version=data.version.strip(),
            intended_use=data.intended_use.strip(),
            out_of_scope_uses=data.out_of_scope_uses.strip() if data.out_of_scope_uses else None,
            bias_mitigation_notes=data.bias_mitigation_notes.strip() if data.bias_mitigation_notes else None,
            training_data_provenance=data.training_data_provenance.strip() if data.training_data_provenance else None,
            synthetic_data_percentage=data.synthetic_data_percentage,
            hallucination_rate_percent=data.hallucination_rate_percent,
            prompt_injection_resistance_score=data.prompt_injection_resistance_score,
            toxicity_filter_efficiency_score=data.toxicity_filter_efficiency_score,
            benchmark_eval_dataset=data.benchmark_eval_dataset.strip() if data.benchmark_eval_dataset else None,
            benchmark_score=data.benchmark_score,
        )
        db.add(card)

        # Recalculate parent AI system's ARI with newly ingested safety telemetry
        process_tier: Optional[str] = None
        if ai_sys.business_process_id:
            bp = db.query(BusinessProcess).filter(BusinessProcess.id == ai_sys.business_process_id).first()
            if bp:
                process_tier = bp.criticality_tier.value if hasattr(bp.criticality_tier, "value") else str(bp.criticality_tier)

        ai_sys.algorithmic_risk_index = cls.calculate_algorithmic_risk_index(
            regulatory_tier=ai_sys.regulatory_tier,
            autonomy_level=ai_sys.autonomy_level,
            data_sensitivity=ai_sys.data_sensitivity,
            process_tier=process_tier,
            hallucination_rate_percent=card.hallucination_rate_percent,
            prompt_injection_resistance_score=card.prompt_injection_resistance_score,
        )
        ai_sys.eu_compliance_score = cls.calculate_eu_compliance_score(
            regulatory_tier=ai_sys.regulatory_tier,
            autonomy_level=ai_sys.autonomy_level,
            hallucination_rate_percent=card.hallucination_rate_percent,
            prompt_injection_resistance_score=card.prompt_injection_resistance_score,
        )
        ai_sys.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(card)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="CREATE",
            resource_type="AIModelCard",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(card.id),
            details={
                "version": card.version,
                "ai_system_id": card.ai_system_id,
                "hallucination_rate_percent": float(card.hallucination_rate_percent),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return card

    @classmethod
    def list_model_cards(cls, db: Session, organization_id: int, system_id: int) -> List[AIModelCard]:
        # Validate parent exists
        cls.get_ai_system(db, organization_id, system_id)
        return (
            db.query(AIModelCard)
            .filter(AIModelCard.ai_system_id == system_id, AIModelCard.organization_id == organization_id)
            .order_by(AIModelCard.id.desc())
            .all()
        )

    # ─── Four-Eyes Deployment Approvals ───────────────────────────────────────

    @classmethod
    def request_deployment_approval(
        cls,
        db: Session,
        organization_id: int,
        system_id: int,
        data: AIDeploymentApprovalCreate,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AIDeploymentApproval:
        ai_sys = cls.get_ai_system(db, organization_id, system_id)
        if ai_sys.lifecycle_state == AILifecycleStateEnum.DECOMMISSIONED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot request deployment approvals for decommissioned AI systems.",
            )

        if ai_sys.is_prohibited_practice:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot request deployment approval for prohibited AI practices.",
            )

        target_env = data.target_environment.strip().upper()
        if target_env not in ["STAGING", "PRODUCTION"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Target environment must be either 'STAGING' or 'PRODUCTION'.",
            )

        approval = AIDeploymentApproval(
            organization_id=organization_id,
            ai_system_id=system_id,
            requested_by_id=current_user.id,
            target_environment=target_env,
            approval_status=AIApprovalStatusEnum.PENDING,
            risk_acceptance_justification=data.risk_acceptance_justification.strip(),
            human_oversight_measures=data.human_oversight_measures.strip(),
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="REQUEST_DEPLOYMENT",
            resource_type="AIDeploymentApproval",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(approval.id),
            details={
                "ai_system_id": system_id,
                "target_environment": approval.target_environment,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return approval

    @classmethod
    def review_deployment_approval(
        cls,
        db: Session,
        organization_id: int,
        approval_id: int,
        data: AIDeploymentApprovalReviewRequest,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AIDeploymentApproval:
        approval = (
            db.query(AIDeploymentApproval)
            .filter(
                AIDeploymentApproval.id == approval_id,
                AIDeploymentApproval.organization_id == organization_id,
            )
            .first()
        )
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment approval request #{approval_id} not found.",
            )

        if approval.approval_status != AIApprovalStatusEnum.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Deployment approval #{approval_id} is already in '{approval.approval_status.value}' state and cannot be reviewed again.",
            )

        # Four-Eyes Segregation of Duties Invariant
        if approval.requested_by_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Segregation of Duties: Model requester cannot review or approve their own deployment request.",
            )

        decision_enum = AIApprovalStatusEnum.APPROVED if data.decision == "APPROVED" else AIApprovalStatusEnum.REJECTED
        approval.approval_status = decision_enum
        approval.reviewed_by_id = current_user.id
        approval.reviewed_at = datetime.utcnow()
        approval.reviewer_notes = data.reviewer_notes.strip() if data.reviewer_notes else None

        # Update parent system approved metadata if approved
        ai_sys = db.query(AISystem).filter(AISystem.id == approval.ai_system_id).first()
        if ai_sys and decision_enum == AIApprovalStatusEnum.APPROVED:
            ai_sys.approved_by_id = current_user.id
            ai_sys.approved_at = datetime.utcnow()

        db.commit()
        db.refresh(approval)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="REVIEW_DEPLOYMENT",
            resource_type="AIDeploymentApproval",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(approval.id),
            details={
                "decision": decision_enum.value,
                "reviewed_by_id": current_user.id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return approval

    @classmethod
    def get_model_card(cls, db: Session, organization_id: int, card_id: int) -> AIModelCard:
        card = (
            db.query(AIModelCard)
            .filter(
                AIModelCard.id == card_id,
                AIModelCard.organization_id == organization_id,
            )
            .first()
        )
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model card #{card_id} not found in this organization.",
            )
        return card

    @classmethod
    def get_deployment_approval(cls, db: Session, organization_id: int, approval_id: int) -> AIDeploymentApproval:
        approval = (
            db.query(AIDeploymentApproval)
            .filter(
                AIDeploymentApproval.id == approval_id,
                AIDeploymentApproval.organization_id == organization_id,
            )
            .first()
        )
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment approval request #{approval_id} not found in this organization.",
            )
        return approval

    @classmethod
    def list_deployment_approvals(
        cls,
        db: Session,
        organization_id: int,
        system_id: Optional[int] = None,
        approval_status: Optional[AIApprovalStatusEnum] = None,
    ) -> List[AIDeploymentApproval]:
        query = db.query(AIDeploymentApproval).filter(AIDeploymentApproval.organization_id == organization_id)
        if system_id:
            query = query.filter(AIDeploymentApproval.ai_system_id == system_id)
        if approval_status:
            query = query.filter(AIDeploymentApproval.approval_status == approval_status)
        return query.order_by(AIDeploymentApproval.id.desc()).all()

    # ─── Posture & Executive Intelligence ─────────────────────────────────────

    @classmethod
    def get_posture_summary(cls, db: Session, organization_id: int) -> AIPostureSummaryResponse:
        systems = db.query(AISystem).filter(AISystem.organization_id == organization_id).all()
        total = len(systems)

        high_risk = sum(1 for s in systems if s.regulatory_tier == AIRegulatoryTierEnum.HIGH_RISK)
        prohibited = sum(1 for s in systems if s.regulatory_tier == AIRegulatoryTierEnum.PROHIBITED)
        production = sum(1 for s in systems if s.lifecycle_state == AILifecycleStateEnum.PRODUCTION)

        pending_approvals = (
            db.query(func.count(AIDeploymentApproval.id))
            .filter(
                AIDeploymentApproval.organization_id == organization_id,
                AIDeploymentApproval.approval_status == AIApprovalStatusEnum.PENDING,
            )
            .scalar()
            or 0
        )

        avg_ari = sum(float(s.algorithmic_risk_index) for s in systems) / total if total > 0 else 0.0

        tier_dist: Dict[str, int] = {}
        for t in AIRegulatoryTierEnum:
            tier_dist[t.value] = sum(1 for s in systems if s.regulatory_tier == t)

        lifecycle_dist: Dict[str, int] = {}
        for l in AILifecycleStateEnum:
            lifecycle_dist[l.value] = sum(1 for s in systems if s.lifecycle_state == l)

        return AIPostureSummaryResponse(
            total_ai_systems=total,
            high_risk_systems=high_risk,
            prohibited_systems=prohibited,
            production_systems=production,
            pending_approvals_count=pending_approvals,
            average_algorithmic_risk_index=round(avg_ari, 2),
            tier_distribution=tier_dist,
            lifecycle_distribution=lifecycle_dist,
        )
