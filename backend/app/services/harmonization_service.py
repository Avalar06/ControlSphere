from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.framework import (
    Framework,
    FrameworkCategory,
    FrameworkFunction,
    FrameworkSubcategory,
)
from app.models.harmonization import (
    CommonControlDomainEnum,
    CommonControlMapping,
    FrameworkComplianceSnapshot,
    FrameworkCrosswalkMapping,
    MappingTypeEnum,
    RationalizationStatusEnum,
    RationalizedCommonControl,
)
from app.models.monitoring import ControlHealthSnapshot, ControlHealthStatusEnum, EvaluationTriggerEnum
from app.models.user import User
from app.schemas.harmonization import (
    CommonControlCreate,
    CommonControlUpdate,
    CrosswalkMappingCreate,
    FrameworkCompliancePostureOverview,
    SubcategoryComplianceMatrixItem,
)
from app.services.audit_service import AuditService
from app.services.control_service import ControlService
from app.services.monitoring_service import MonitoringService


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class HarmonizationService:

    # ── Global Crosswalk Mapping Management ───────────────────────────────────

    @staticmethod
    def list_crosswalks(
        db: Session,
        source_framework_id: Optional[int] = None,
        target_framework_id: Optional[int] = None,
    ) -> List[FrameworkCrosswalkMapping]:
        query = db.query(FrameworkCrosswalkMapping)
        if source_framework_id or target_framework_id:
            query = query.join(
                FrameworkSubcategory,
                FrameworkCrosswalkMapping.source_subcategory_id == FrameworkSubcategory.id,
            ).join(
                FrameworkCategory,
                FrameworkSubcategory.category_id == FrameworkCategory.id,
            ).join(
                FrameworkFunction,
                FrameworkCategory.function_id == FrameworkFunction.id,
            )
            if source_framework_id:
                query = query.filter(FrameworkFunction.framework_id == source_framework_id)
        return query.all()

    @staticmethod
    def create_crosswalk(
        db: Session,
        mapping_in: CrosswalkMappingCreate,
        current_user: User,
    ) -> FrameworkCrosswalkMapping:
        # Validate subcategories exist
        source = db.query(FrameworkSubcategory).filter(FrameworkSubcategory.id == mapping_in.source_subcategory_id).first()
        target = db.query(FrameworkSubcategory).filter(FrameworkSubcategory.id == mapping_in.target_subcategory_id).first()
        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source subcategory not found")
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target subcategory not found")
        if source.id == target.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot crosswalk subcategory to itself")

        # Check existing
        existing = (
            db.query(FrameworkCrosswalkMapping)
            .filter(
                FrameworkCrosswalkMapping.source_subcategory_id == mapping_in.source_subcategory_id,
                FrameworkCrosswalkMapping.target_subcategory_id == mapping_in.target_subcategory_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Crosswalk mapping already exists")

        mapping = FrameworkCrosswalkMapping(
            source_subcategory_id=mapping_in.source_subcategory_id,
            target_subcategory_id=mapping_in.target_subcategory_id,
            mapping_type=mapping_in.mapping_type,
            confidence_score=round(max(0.0, min(1.0, mapping_in.confidence_score)), 2),
            bidirectional=mapping_in.bidirectional,
            rationale=mapping_in.rationale,
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)

        AuditService.log(
            db=db,
            organization_id=current_user.organization_id,
            action="harmonization.crosswalk_create",
            resource_type="framework_crosswalk_mapping",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(mapping.id),
            details={
                "source_subcategory_id": mapping.source_subcategory_id,
                "target_subcategory_id": mapping.target_subcategory_id,
                "mapping_type": mapping.mapping_type.value,
                "confidence_score": mapping.confidence_score,
            },
        )
        return mapping

    @staticmethod
    def delete_crosswalk(
        db: Session,
        crosswalk_id: int,
        current_user: User,
    ) -> None:
        mapping = db.query(FrameworkCrosswalkMapping).filter(FrameworkCrosswalkMapping.id == crosswalk_id).first()
        if not mapping:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crosswalk mapping not found")

        AuditService.log(
            db=db,
            organization_id=current_user.organization_id,
            action="harmonization.crosswalk_delete",
            resource_type="framework_crosswalk_mapping",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(mapping.id),
            details={
                "source_subcategory_id": mapping.source_subcategory_id,
                "target_subcategory_id": mapping.target_subcategory_id,
            },
        )
        db.delete(mapping)
        db.commit()

    # ── Rationalized Common Control CRUD & Mappings ───────────────────────────

    @staticmethod
    def list_common_controls(
        db: Session,
        organization_id: int,
        domain: Optional[CommonControlDomainEnum] = None,
        status_filter: Optional[RationalizationStatusEnum] = None,
    ) -> List[RationalizedCommonControl]:
        query = db.query(RationalizedCommonControl).filter(
            RationalizedCommonControl.organization_id == organization_id
        )
        if domain:
            query = query.filter(RationalizedCommonControl.domain == domain)
        if status_filter:
            query = query.filter(RationalizedCommonControl.rationalization_status == status_filter)
        return query.order_by(RationalizedCommonControl.common_control_code.asc()).all()

    @staticmethod
    def get_common_control(
        db: Session,
        organization_id: int,
        common_control_id: int,
    ) -> RationalizedCommonControl:
        cc = (
            db.query(RationalizedCommonControl)
            .filter(
                RationalizedCommonControl.id == common_control_id,
                RationalizedCommonControl.organization_id == organization_id,
            )
            .first()
        )
        if not cc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Common control not found")
        return cc

    @staticmethod
    def create_common_control(
        db: Session,
        organization_id: int,
        cc_in: CommonControlCreate,
        current_user: User,
    ) -> RationalizedCommonControl:
        # Check code uniqueness within org
        existing = (
            db.query(RationalizedCommonControl)
            .filter(
                RationalizedCommonControl.organization_id == organization_id,
                RationalizedCommonControl.common_control_code == cc_in.common_control_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Common control code already exists in organization")

        # Validate owner if supplied
        if cc_in.owner_id:
            owner = (
                db.query(User)
                .filter(
                    User.id == cc_in.owner_id,
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
                .first()
            )
            if not owner:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned owner not found in organization or inactive")

        cc = RationalizedCommonControl(
            organization_id=organization_id,
            common_control_code=cc_in.common_control_code,
            title=cc_in.title,
            description=cc_in.description,
            domain=cc_in.domain,
            rationalization_status=cc_in.rationalization_status,
            owner_id=cc_in.owner_id,
            deprecation_reason=cc_in.deprecation_reason,
            inherited_health_score=100.0,
            inherited_health_status=ControlHealthStatusEnum.HEALTHY,
        )
        db.add(cc)
        db.commit()
        db.refresh(cc)

        # Map initial controls if supplied
        if cc_in.initial_control_ids:
            for ctrl_id in cc_in.initial_control_ids:
                HarmonizationService._map_single_control_internal(db, organization_id, cc.id, ctrl_id, 1.0)
            HarmonizationService.recalculate_common_control_health(db, organization_id, cc.id)
            db.refresh(cc)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="harmonization.common_control_create",
            resource_type="rationalized_common_control",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(cc.id),
            details={
                "common_control_code": cc.common_control_code,
                "title": cc.title,
                "domain": cc.domain.value,
                "status": cc.rationalization_status.value,
            },
        )
        return cc

    @staticmethod
    def update_common_control(
        db: Session,
        organization_id: int,
        common_control_id: int,
        cc_update: CommonControlUpdate,
        current_user: User,
    ) -> RationalizedCommonControl:
        cc = HarmonizationService.get_common_control(db, organization_id, common_control_id)

        # Validate owner if changed
        if cc_update.owner_id is not None:
            owner = (
                db.query(User)
                .filter(
                    User.id == cc_update.owner_id,
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
                .first()
            )
            if not owner:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned owner not found in organization or inactive")
            cc.owner_id = cc_update.owner_id

        if cc_update.title is not None:
            cc.title = cc_update.title
        if cc_update.description is not None:
            cc.description = cc_update.description
        if cc_update.domain is not None:
            cc.domain = cc_update.domain
        if cc_update.rationalization_status is not None:
            if cc_update.rationalization_status == RationalizationStatusEnum.RETIRED and not cc_update.deprecation_reason and not cc.deprecation_reason:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deprecation reason is mandatory when retiring a common control")
            cc.rationalization_status = cc_update.rationalization_status
        if cc_update.deprecation_reason is not None:
            cc.deprecation_reason = cc_update.deprecation_reason

        cc.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(cc)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="harmonization.common_control_update",
            resource_type="rationalized_common_control",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(cc.id),
            details={
                "common_control_code": cc.common_control_code,
                "status": cc.rationalization_status.value,
            },
        )
        return cc

    @staticmethod
    def map_organization_control(
        db: Session,
        organization_id: int,
        common_control_id: int,
        organization_control_id: int,
        weight: float,
        current_user: User,
    ) -> CommonControlMapping:
        cc = HarmonizationService.get_common_control(db, organization_id, common_control_id)
        if cc.rationalization_status == RationalizationStatusEnum.RETIRED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot map controls to a retired common control")

        mapping = HarmonizationService._map_single_control_internal(
            db, organization_id, common_control_id, organization_control_id, weight
        )
        HarmonizationService.recalculate_common_control_health(db, organization_id, common_control_id)

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="harmonization.mapping_create",
            resource_type="common_control_mapping",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(mapping.id),
            details={
                "common_control_id": common_control_id,
                "organization_control_id": organization_control_id,
                "weight": weight,
            },
        )
        return mapping

    @staticmethod
    def _map_single_control_internal(
        db: Session,
        organization_id: int,
        common_control_id: int,
        organization_control_id: int,
        weight: float,
    ) -> CommonControlMapping:
        # Validate control belongs to tenant
        ctrl = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == organization_control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .first()
        )
        if not ctrl:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization control not found in tenant")

        existing = (
            db.query(CommonControlMapping)
            .filter(
                CommonControlMapping.rationalized_common_control_id == common_control_id,
                CommonControlMapping.organization_control_id == organization_control_id,
            )
            .first()
        )
        if existing:
            existing.weight = max(0.1, weight)
            db.commit()
            return existing

        mapping = CommonControlMapping(
            organization_id=organization_id,
            rationalized_common_control_id=common_control_id,
            organization_control_id=organization_control_id,
            weight=max(0.1, weight),
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping

    @staticmethod
    def unmap_organization_control(
        db: Session,
        organization_id: int,
        common_control_id: int,
        organization_control_id: int,
        current_user: User,
    ) -> None:
        cc = HarmonizationService.get_common_control(db, organization_id, common_control_id)
        mapping = (
            db.query(CommonControlMapping)
            .filter(
                CommonControlMapping.rationalized_common_control_id == common_control_id,
                CommonControlMapping.organization_control_id == organization_control_id,
                CommonControlMapping.organization_id == organization_id,
            )
            .first()
        )
        if not mapping:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="harmonization.mapping_delete",
            resource_type="common_control_mapping",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(mapping.id),
            details={
                "common_control_id": common_control_id,
                "organization_control_id": organization_control_id,
            },
        )
        db.delete(mapping)
        db.commit()
        HarmonizationService.recalculate_common_control_health(db, organization_id, common_control_id)

    # ── Mathematical Calculations & Telemetry ─────────────────────────────────

    @staticmethod
    def recalculate_common_control_health(
        db: Session,
        organization_id: int,
        common_control_id: int,
    ) -> Tuple[float, ControlHealthStatusEnum]:
        cc = (
            db.query(RationalizedCommonControl)
            .filter(
                RationalizedCommonControl.id == common_control_id,
                RationalizedCommonControl.organization_id == organization_id,
            )
            .first()
        )
        if not cc:
            return 100.0, ControlHealthStatusEnum.HEALTHY

        mappings = (
            db.query(CommonControlMapping)
            .filter(
                CommonControlMapping.rationalized_common_control_id == common_control_id,
                CommonControlMapping.organization_id == organization_id,
            )
            .all()
        )

        if not mappings:
            # Approved architecture rule: zero linked controls evaluates to 100.0/HEALTHY
            cc.inherited_health_score = 100.0
            cc.inherited_health_status = ControlHealthStatusEnum.HEALTHY
            db.commit()
            return 100.0, ControlHealthStatusEnum.HEALTHY

        total_weight = 0.0
        weighted_sum = 0.0

        for m in mappings:
            w = max(0.1, m.weight)
            # Fetch latest Phase 7 snapshot for this control
            latest_snap = (
                db.query(ControlHealthSnapshot)
                .filter(
                    ControlHealthSnapshot.organization_control_id == m.organization_control_id,
                    ControlHealthSnapshot.organization_id == organization_id,
                )
                .order_by(ControlHealthSnapshot.evaluated_at.desc())
                .first()
            )
            if latest_snap:
                score = latest_snap.health_score
            else:
                # If no snapshot yet, perform on-the-fly evaluation using MonitoringService
                ctrl = db.query(OrganizationControl).filter(OrganizationControl.id == m.organization_control_id).first()
                if ctrl:
                    cfg = MonitoringService.get_or_create_config(db, organization_id)
                    snap, _, _ = MonitoringService._evaluate_single_control(
                        db=db,
                        organization_id=organization_id,
                        control=ctrl,
                        config=cfg,
                        trigger=EvaluationTriggerEnum.MANUAL,
                        eval_time=datetime.now(timezone.utc),
                    )
                    score = snap.health_score
                else:
                    score = 100.0

            weighted_sum += (w * score)
            total_weight += w

        avg_score = round(max(0.0, min(100.0, weighted_sum / max(0.1, total_weight))), 1)

        if avg_score >= 80.0:
            status_enum = ControlHealthStatusEnum.HEALTHY
        elif avg_score >= 60.0:
            status_enum = ControlHealthStatusEnum.DEGRADED
        elif avg_score >= 40.0:
            status_enum = ControlHealthStatusEnum.AT_RISK
        else:
            status_enum = ControlHealthStatusEnum.FAILING

        cc.inherited_health_score = avg_score
        cc.inherited_health_status = status_enum
        db.commit()
        return avg_score, status_enum

    @staticmethod
    def calculate_framework_compliance_posture(
        db: Session,
        organization_id: int,
        framework_id: int,
        eval_time: Optional[datetime] = None,
    ) -> Tuple[FrameworkCompliancePostureOverview, FrameworkComplianceSnapshot]:
        now = _to_utc(eval_time) or datetime.now(timezone.utc)
        framework = db.query(Framework).filter(Framework.id == framework_id).first()
        if not framework:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")

        # 1. Fetch all subcategories for this framework
        subcategories = (
            db.query(FrameworkSubcategory)
            .join(FrameworkCategory, FrameworkSubcategory.category_id == FrameworkCategory.id)
            .join(FrameworkFunction, FrameworkCategory.function_id == FrameworkFunction.id)
            .filter(FrameworkFunction.framework_id == framework_id)
            .all()
        )
        total_subcategories = len(subcategories)
        if total_subcategories == 0:
            snap = FrameworkComplianceSnapshot(
                organization_id=organization_id,
                framework_id=framework_id,
                calculation_version="v1.0",
                coverage_percentage=0.0,
                compliance_health_score=0.0,
                total_subcategories=0,
                covered_subcategories=0,
                unmapped_subcategories=0,
                evaluated_at=now,
            )
            overview = FrameworkCompliancePostureOverview(
                framework_id=framework_id,
                framework_identifier=framework.identifier,
                framework_name=framework.name,
                total_subcategories=0,
                directly_covered_subcategories=0,
                crosswalk_covered_subcategories=0,
                total_covered_subcategories=0,
                coverage_percentage=0.0,
                compliance_health_score=0.0,
                evaluated_at=now,
            )
            return overview, snap

        # 2. Get all organization controls for this tenant
        org_controls = (
            db.query(OrganizationControl)
            .filter(OrganizationControl.organization_id == organization_id)
            .all()
        )
        org_control_by_subcat: Dict[int, OrganizationControl] = {
            ctrl.subcategory_id: ctrl for ctrl in org_controls
        }

        # 3. Get all latest CCM snapshots for this tenant
        latest_snapshots = (
            db.query(ControlHealthSnapshot)
            .filter(ControlHealthSnapshot.organization_id == organization_id)
            .order_by(ControlHealthSnapshot.evaluated_at.desc())
            .all()
        )
        latest_score_by_ctrl: Dict[int, float] = {}
        for s in latest_snapshots:
            if s.organization_control_id not in latest_score_by_ctrl:
                latest_score_by_ctrl[s.organization_control_id] = s.health_score

        # 4. Fetch all global crosswalks with confidence >= 0.80
        crosswalks = (
            db.query(FrameworkCrosswalkMapping)
            .filter(FrameworkCrosswalkMapping.confidence_score >= 0.80)
            .all()
        )

        directly_covered_set: Set[int] = set()
        crosswalk_covered_set: Set[int] = set()
        effective_health_map: Dict[int, float] = {}

        for subcat in subcategories:
            sid = subcat.id
            ctrl = org_control_by_subcat.get(sid)
            is_direct = False

            # Direct coverage check
            if ctrl and ctrl.status == ImplementationStatusEnum.IMPLEMENTED:
                ctrl_health = latest_score_by_ctrl.get(ctrl.id, 100.0)
                if ctrl_health >= 60.0:
                    is_direct = True
                    directly_covered_set.add(sid)
                    effective_health_map[sid] = ctrl_health

            # Crosswalk inherited coverage check (if not directly covered)
            if not is_direct:
                best_inherited_health = 0.0
                has_inherited = False

                for cw in crosswalks:
                    other_subcat_id = None
                    if cw.target_subcategory_id == sid:
                        other_subcat_id = cw.source_subcategory_id
                    elif cw.source_subcategory_id == sid and cw.bidirectional:
                        other_subcat_id = cw.target_subcategory_id

                    if other_subcat_id:
                        other_ctrl = org_control_by_subcat.get(other_subcat_id)
                        if other_ctrl and other_ctrl.status == ImplementationStatusEnum.IMPLEMENTED:
                            other_health = latest_score_by_ctrl.get(other_ctrl.id, 100.0)
                            if other_health >= 60.0:
                                inherited_health = other_health * cw.confidence_score
                                if inherited_health > best_inherited_health:
                                    best_inherited_health = inherited_health
                                    has_inherited = True

                if has_inherited:
                    crosswalk_covered_set.add(sid)
                    effective_health_map[sid] = round(best_inherited_health, 1)

        total_covered_count = len(directly_covered_set | crosswalk_covered_set)
        coverage_percentage = round((total_covered_count / total_subcategories) * 100.0, 1)

        # Compliance score is the sum of EffectiveHealth for all covered subcategories / total_subcategories
        sum_effective_health = sum(effective_health_map.values())
        compliance_health_score = round(max(0.0, min(100.0, sum_effective_health / total_subcategories)), 1)
        unmapped_count = total_subcategories - total_covered_count

        # Create immutable snapshot record
        snapshot = FrameworkComplianceSnapshot(
            organization_id=organization_id,
            framework_id=framework_id,
            calculation_version="v1.0",
            coverage_percentage=coverage_percentage,
            compliance_health_score=compliance_health_score,
            total_subcategories=total_subcategories,
            covered_subcategories=total_covered_count,
            unmapped_subcategories=unmapped_count,
            evaluated_at=now,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        overview = FrameworkCompliancePostureOverview(
            framework_id=framework_id,
            framework_identifier=framework.identifier,
            framework_name=framework.name,
            total_subcategories=total_subcategories,
            directly_covered_subcategories=len(directly_covered_set),
            crosswalk_covered_subcategories=len(crosswalk_covered_set),
            total_covered_subcategories=total_covered_count,
            coverage_percentage=coverage_percentage,
            compliance_health_score=compliance_health_score,
            evaluated_at=now,
        )
        return overview, snapshot

    @staticmethod
    def execute_full_harmonization_evaluation(
        db: Session,
        organization_id: int,
        current_user: User,
    ) -> Tuple[int, int, int]:
        now = datetime.now(timezone.utc)
        # 1. Recalculate health for all tenant Common Controls
        common_controls = db.query(RationalizedCommonControl).filter(
            RationalizedCommonControl.organization_id == organization_id
        ).all()
        for cc in common_controls:
            HarmonizationService.recalculate_common_control_health(db, organization_id, cc.id)

        # 2. Calculate compliance snapshots for all active frameworks
        frameworks = db.query(Framework).all()
        snapshots_created = 0
        for fw in frameworks:
            _, _ = HarmonizationService.calculate_framework_compliance_posture(db, organization_id, fw.id, now)
            snapshots_created += 1

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="harmonization.evaluate",
            resource_type="organization",
            actor_email=current_user.email,
            actor_id=current_user.id,
            resource_id=str(organization_id),
            details={
                "evaluated_common_controls": len(common_controls),
                "evaluated_frameworks": len(frameworks),
                "snapshots_created": snapshots_created,
            },
        )
        return len(common_controls), len(frameworks), snapshots_created
