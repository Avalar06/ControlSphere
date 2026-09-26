from collections import deque
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ai_governance import AISystem
from app.models.cloudsec import (
    CloudAsset,
    CloudLifecycleStateEnum,
    CloudPostureStatusEnum,
)
from app.models.control import OrganizationControl
from app.models.data_governance import (
    DataAssetCloudLink,
    DataAssetControlLink,
    DataAssetEvidenceLink,
    DataAssetLifecycleEnum,
    DataAssetProcessingLink,
    DataClassificationApprovalStatusEnum,
    DataClassificationChangeTypeEnum,
    DataClassificationLevel,
    DataClassificationRecord,
    DataClassificationRecordStatusEnum,
    DataClassificationScheme,
    DataClassificationSchemeStatusEnum,
    DataCloudHostingRoleEnum,
    DataDisposalMethodEnum,
    DataLineageEdge,
    DataLineageStatusEnum,
    DataOwnerTransferStatusEnum,
)
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.privacy import (
    DataAsset,
    DataSensitivityLevel,
    ProcessingActivity,
    ProcessingLifecycleState,
)
from app.models.regulatory import RegulatoryObligation
from app.models.resilience import BusinessProcess
from app.models.tprm import Vendor
from app.models.user import User
from app.schemas.data_governance import (
    CloudPostureAlignmentInfo,
    DataAssetCloudLinkCreate,
    DataAssetControlLinkCreate,
    DataAssetDeprecateRequest,
    DataAssetEvidenceLinkCreate,
    DataAssetProcessingLinkCreate,
    DataAssetRegisterRequest,
    DataAssetRestoreRequest,
    DataAssetRetireRequest,
    DataClassificationLevelCreate,
    DataClassificationRejectRequest,
    DataClassificationRequestCreate,
    DataClassificationSchemeCreate,
    DataGovernanceSummaryResponse,
    DataLineageEdgeCreate,
    DataLineageEdgeRevokeRequest,
    DataOwnershipUpdateRequest,
    GovernedDataAssetCreate,
    GovernedDataAssetDossierResponse,
    GovernedDataAssetResponse,
    GovernedDataAssetUpdate,
    RegulatoryObligationRef,
)
from app.services.audit_service import AuditService


class DataGovernanceService:
    """Authoritative Enterprise Data Governance, Classification, Stewardship & Lineage Engine."""

    SENSITIVITY_RANK_MAP: Dict[DataSensitivityLevel, int] = {
        DataSensitivityLevel.PUBLIC: 1,
        DataSensitivityLevel.INTERNAL: 2,
        DataSensitivityLevel.CONFIDENTIAL: 3,
        DataSensitivityLevel.RESTRICTED_PII: 4,
        DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI: 5,
    }

    @classmethod
    def _log_audit(
        cls,
        db: Session,
        organization_id: int,
        actor_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int],
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        user = db.query(User).filter(User.id == actor_id).first()
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

    @classmethod
    def _commit_or_conflict(cls, db: Session, conflict_detail: str = "Resource conflict or duplicate record") -> None:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=conflict_detail,
            )

    @classmethod
    def compute_lineage_provenance_hash(
        cls,
        organization_id: int,
        edge_code: str,
        version: int,
        source_data_asset_id: int,
        target_data_asset_id: int,
        relationship_type: str,
        transformation_summary: Optional[str],
        is_encrypted_in_transit: bool,
        is_masked_or_anonymized: bool,
        processing_activity_id: Optional[int],
        cloud_asset_id: Optional[int],
        created_by_id: int,
        effective_from: datetime,
    ) -> str:
        """
        Computes deterministic canonical SHA-256 provenance digest for a DataLineageEdge.
        """
        eff_utc = effective_from
        if eff_utc.tzinfo is None:
            eff_utc = eff_utc.replace(tzinfo=timezone.utc)
        else:
            eff_utc = eff_utc.astimezone(timezone.utc)
        eff_iso = eff_utc.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

        canonical_payload = {
            "cloud_asset_id": cloud_asset_id,
            "created_by_id": int(created_by_id),
            "edge_code": str(edge_code).strip(),
            "effective_from": eff_iso,
            "is_encrypted_in_transit": bool(is_encrypted_in_transit),
            "is_masked_or_anonymized": bool(is_masked_or_anonymized),
            "organization_id": int(organization_id),
            "processing_activity_id": processing_activity_id,
            "relationship_type": str(relationship_type).strip(),
            "source_data_asset_id": int(source_data_asset_id),
            "target_data_asset_id": int(target_data_asset_id),
            "transformation_summary": (transformation_summary or "").strip() or None,
            "version": int(version),
        }
        canonical_str = json.dumps(
            canonical_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest().lower()

    # ─── Cross-Tenant & Active User Validation Helpers ────────────────────────

    @classmethod
    def _validate_tenant_user(
        cls,
        db: Session,
        organization_id: int,
        user_id: int,
        role_label: str = "User",
    ) -> User:
        user = (
            db.query(User)
            .filter(User.id == user_id, User.organization_id == organization_id)
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{role_label} {user_id} not found in this organization",
            )
        if not getattr(user, "is_active", True):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot assign inactive user {user_id} as {role_label}",
            )
        return user

    @classmethod
    def _validate_tenant_cloud_asset(
        cls,
        db: Session,
        organization_id: int,
        cloud_asset_id: int,
    ) -> CloudAsset:
        cloud_asset = (
            db.query(CloudAsset)
            .filter(
                CloudAsset.id == cloud_asset_id,
                CloudAsset.organization_id == organization_id,
            )
            .first()
        )
        if not cloud_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cloud asset {cloud_asset_id} not found in this organization",
            )
        return cloud_asset

    @classmethod
    def _validate_optional_context_refs(
        cls,
        db: Session,
        organization_id: int,
        business_process_id: Optional[int] = None,
        ai_system_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        cloud_asset_id: Optional[int] = None,
    ) -> None:
        if business_process_id is not None:
            bp = (
                db.query(BusinessProcess)
                .filter(
                    BusinessProcess.id == business_process_id,
                    BusinessProcess.organization_id == organization_id,
                )
                .first()
            )
            if not bp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Business process {business_process_id} not found in this organization",
                )
        if ai_system_id is not None:
            ai = (
                db.query(AISystem)
                .filter(
                    AISystem.id == ai_system_id,
                    AISystem.organization_id == organization_id,
                )
                .first()
            )
            if not ai:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"AI system {ai_system_id} not found in this organization",
                )
        if vendor_id is not None:
            v = (
                db.query(Vendor)
                .filter(
                    Vendor.id == vendor_id,
                    Vendor.organization_id == organization_id,
                )
                .first()
            )
            if not v:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vendor {vendor_id} not found in this organization",
                )
        if cloud_asset_id is not None:
            cls._validate_tenant_cloud_asset(db, organization_id, cloud_asset_id)

    # ─── 1. Classification Schemes & Levels ───────────────────────────────────

    @classmethod
    def create_scheme(
        cls,
        db: Session,
        organization_id: int,
        actor_id: int,
        payload: DataClassificationSchemeCreate,
    ) -> DataClassificationScheme:
        existing = (
            db.query(DataClassificationScheme)
            .filter(
                DataClassificationScheme.organization_id == organization_id,
                DataClassificationScheme.scheme_code == payload.scheme_code,
                DataClassificationScheme.version == payload.version,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Classification scheme '{payload.scheme_code}' v{payload.version} already exists",
            )

        scheme = DataClassificationScheme(
            organization_id=organization_id,
            scheme_code=payload.scheme_code,
            name=payload.name,
            description=payload.description,
            version=payload.version,
            status=DataClassificationSchemeStatusEnum.DRAFT.value,
            is_default=payload.is_default,
            created_by_id=actor_id,
        )
        db.add(scheme)
        cls._commit_or_conflict(db, "Duplicate classification scheme code and version")
        db.refresh(scheme)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_SCHEME_CREATED",
            resource_type="data_classification_scheme",
            resource_id=scheme.id,
            details={
                "scheme_code": scheme.scheme_code,
                "version": scheme.version,
                "is_default": scheme.is_default,
            },
        )
        return scheme

    @classmethod
    def get_scheme(
        cls,
        db: Session,
        organization_id: int,
        scheme_id: int,
    ) -> DataClassificationScheme:
        scheme = (
            db.query(DataClassificationScheme)
            .filter(
                DataClassificationScheme.id == scheme_id,
                DataClassificationScheme.organization_id == organization_id,
            )
            .first()
        )
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Classification scheme {scheme_id} not found",
            )
        return scheme

    @classmethod
    def list_schemes(
        cls,
        db: Session,
        organization_id: int,
        status_filter: Optional[str] = None,
    ) -> List[DataClassificationScheme]:
        query = db.query(DataClassificationScheme).filter(
            DataClassificationScheme.organization_id == organization_id
        )
        if status_filter:
            query = query.filter(DataClassificationScheme.status == status_filter)
        return query.order_by(DataClassificationScheme.id.desc()).all()

    @classmethod
    def add_level_to_scheme(
        cls,
        db: Session,
        organization_id: int,
        scheme_id: int,
        actor_id: int,
        payload: DataClassificationLevelCreate,
    ) -> DataClassificationLevel:
        scheme = cls.get_scheme(db, organization_id, scheme_id)
        if scheme.status != DataClassificationSchemeStatusEnum.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot add levels to scheme '{scheme.scheme_code}' in status '{scheme.status}'",
            )

        dup_code = (
            db.query(DataClassificationLevel)
            .filter(
                DataClassificationLevel.scheme_id == scheme.id,
                DataClassificationLevel.level_code == payload.level_code,
            )
            .first()
        )
        if dup_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Level code '{payload.level_code}' already exists in scheme '{scheme.scheme_code}'",
            )

        dup_rank = (
            db.query(DataClassificationLevel)
            .filter(
                DataClassificationLevel.scheme_id == scheme.id,
                DataClassificationLevel.ordinal_rank == payload.ordinal_rank,
            )
            .first()
        )
        if dup_rank:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ordinal rank {payload.ordinal_rank} already exists in scheme '{scheme.scheme_code}'",
            )

        # Enforce monotonic rank-to-sensitivity ordering across existing levels
        new_sens_rank = cls.SENSITIVITY_RANK_MAP[payload.mapped_sensitivity_level]
        for existing_lvl in scheme.levels:
            ex_sens_rank = cls.SENSITIVITY_RANK_MAP[existing_lvl.mapped_sensitivity_level]
            if existing_lvl.ordinal_rank < payload.ordinal_rank and ex_sens_rank > new_sens_rank:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Monotonic sensitivity violation: level '{payload.level_code}' (rank {payload.ordinal_rank}) "
                        f"maps to lower sensitivity ({payload.mapped_sensitivity_level.value}) than lower-ranked level "
                        f"'{existing_lvl.level_code}' (rank {existing_lvl.ordinal_rank}, {existing_lvl.mapped_sensitivity_level.value})"
                    ),
                )
            if existing_lvl.ordinal_rank > payload.ordinal_rank and ex_sens_rank < new_sens_rank:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Monotonic sensitivity violation: level '{payload.level_code}' (rank {payload.ordinal_rank}) "
                        f"maps to higher sensitivity ({payload.mapped_sensitivity_level.value}) than higher-ranked level "
                        f"'{existing_lvl.level_code}' (rank {existing_lvl.ordinal_rank}, {existing_lvl.mapped_sensitivity_level.value})"
                    ),
                )

        requires_4eyes = payload.requires_four_eyes_approval or (
            payload.mapped_sensitivity_level
            in (
                DataSensitivityLevel.RESTRICTED_PII,
                DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI,
            )
        )

        level = DataClassificationLevel(
            organization_id=organization_id,
            scheme_id=scheme.id,
            level_code=payload.level_code,
            name=payload.name,
            description=payload.description,
            ordinal_rank=payload.ordinal_rank,
            mapped_sensitivity_level=payload.mapped_sensitivity_level,
            requires_encryption_at_rest=payload.requires_encryption_at_rest,
            requires_encryption_in_transit=payload.requires_encryption_in_transit,
            requires_four_eyes_approval=requires_4eyes,
            default_retention_months=payload.default_retention_months,
            required_disposal_method=(
                payload.required_disposal_method.value
                if payload.required_disposal_method
                else None
            ),
        )
        db.add(level)
        cls._commit_or_conflict(db, "Duplicate classification level in scheme")
        db.refresh(level)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_LEVEL_CREATED",
            resource_type="data_classification_level",
            resource_id=level.id,
            details={
                "scheme_id": scheme.id,
                "level_code": level.level_code,
                "ordinal_rank": level.ordinal_rank,
                "mapped_sensitivity_level": level.mapped_sensitivity_level.value,
            },
        )
        return level

    @classmethod
    def submit_scheme(
        cls,
        db: Session,
        organization_id: int,
        scheme_id: int,
        actor_id: int,
    ) -> DataClassificationScheme:
        scheme = cls.get_scheme(db, organization_id, scheme_id)
        if scheme.status != DataClassificationSchemeStatusEnum.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Scheme '{scheme.scheme_code}' cannot be submitted from status '{scheme.status}'",
            )
        if len(scheme.levels) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Classification scheme must define at least 2 ordered levels before submission",
            )

        scheme.status = DataClassificationSchemeStatusEnum.PENDING_APPROVAL.value
        scheme.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scheme)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_SCHEME_SUBMITTED",
            resource_type="data_classification_scheme",
            resource_id=scheme.id,
            details={"scheme_code": scheme.scheme_code, "levels_count": len(scheme.levels)},
        )
        return scheme

    @classmethod
    def approve_scheme(
        cls,
        db: Session,
        organization_id: int,
        scheme_id: int,
        approver_id: int,
    ) -> DataClassificationScheme:
        scheme = cls.get_scheme(db, organization_id, scheme_id)
        if scheme.status != DataClassificationSchemeStatusEnum.PENDING_APPROVAL.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Scheme '{scheme.scheme_code}' is not in PENDING_APPROVAL status (current: '{scheme.status}')",
            )
        if len(scheme.levels) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Classification scheme must have at least 2 levels before activation",
            )
        if scheme.created_by_id == approver_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Segregation of Duties violation: scheme creator cannot approve activation",
            )

        now = datetime.now(timezone.utc)
        # Archive previous ACTIVE versions of the same scheme_code
        (
            db.query(DataClassificationScheme)
            .filter(
                DataClassificationScheme.organization_id == organization_id,
                DataClassificationScheme.scheme_code == scheme.scheme_code,
                DataClassificationScheme.id != scheme.id,
                DataClassificationScheme.status == DataClassificationSchemeStatusEnum.ACTIVE.value,
            )
            .update(
                {
                    "status": DataClassificationSchemeStatusEnum.ARCHIVED.value,
                    "is_default": False,
                    "updated_at": now,
                },
                synchronize_session=False,
            )
        )
        if scheme.is_default:
            (
                db.query(DataClassificationScheme)
                .filter(
                    DataClassificationScheme.organization_id == organization_id,
                    DataClassificationScheme.id != scheme.id,
                    DataClassificationScheme.is_default == True,
                )
                .update({"is_default": False}, synchronize_session=False)
            )

        scheme.status = DataClassificationSchemeStatusEnum.ACTIVE.value
        scheme.approved_by_id = approver_id
        scheme.approved_at = now
        scheme.updated_at = now
        db.commit()
        db.refresh(scheme)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=approver_id,
            action="DATA_GOV_SCHEME_APPROVED",
            resource_type="data_classification_scheme",
            resource_id=scheme.id,
            details={
                "scheme_code": scheme.scheme_code,
                "version": scheme.version,
                "created_by_id": scheme.created_by_id,
                "approved_by_id": approver_id,
            },
        )
        return scheme

    # ─── 2. Governed Data Asset Catalog & Lifecycle ───────────────────────────

    @classmethod
    def get_governed_asset(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
    ) -> DataAsset:
        asset = (
            db.query(DataAsset)
            .filter(
                DataAsset.id == asset_id,
                DataAsset.organization_id == organization_id,
            )
            .first()
        )
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data asset {asset_id} not found",
            )
        return asset

    @classmethod
    def _ensure_not_retired(cls, asset: DataAsset) -> None:
        if asset.lifecycle_state == DataAssetLifecycleEnum.RETIRED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Data asset '{asset.asset_code}' is RETIRED and cannot be mutated",
            )

    @classmethod
    def create_governed_asset(
        cls,
        db: Session,
        organization_id: int,
        actor_id: int,
        payload: GovernedDataAssetCreate,
    ) -> DataAsset:
        existing = (
            db.query(DataAsset)
            .filter(
                DataAsset.organization_id == organization_id,
                DataAsset.asset_code == payload.asset_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Data asset with code '{payload.asset_code}' already exists",
            )

        # Validate initial lifecycle state: cannot jump straight to ACTIVE, CLASSIFIED, DEPRECATED, or RETIRED without governance workflow
        if payload.initial_lifecycle_state not in (
            DataAssetLifecycleEnum.DISCOVERED,
            DataAssetLifecycleEnum.REGISTERED,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Initial lifecycle state must be DISCOVERED or REGISTERED "
                    f"(got '{payload.initial_lifecycle_state.value}'); "
                    "activation requires approved classification"
                ),
            )

        resolved_owner_id = payload.owner_id if payload.owner_id is not None else actor_id
        cls._validate_tenant_user(db, organization_id, resolved_owner_id, "Data Owner")
        if payload.steward_id is not None:
            cls._validate_tenant_user(db, organization_id, payload.steward_id, "Data Steward")

        cls._validate_optional_context_refs(
            db=db,
            organization_id=organization_id,
            business_process_id=payload.business_process_id,
            ai_system_id=payload.ai_system_id,
            vendor_id=payload.vendor_id,
            cloud_asset_id=payload.cloud_asset_id,
        )

        # Cloud discovery / newly registered assets do not silently gain Restricted classification without Four-Eyes
        initial_sensitivity = payload.data_sensitivity_level
        if payload.initial_lifecycle_state == DataAssetLifecycleEnum.DISCOVERED:
            initial_sensitivity = DataSensitivityLevel.INTERNAL

        asset = DataAsset(
            organization_id=organization_id,
            owner_id=resolved_owner_id,
            steward_id=payload.steward_id,
            cloud_asset_id=payload.cloud_asset_id,
            asset_code=payload.asset_code,
            name=payload.name,
            description=payload.description,
            asset_type=payload.asset_type.value,
            lifecycle_state=payload.initial_lifecycle_state.value,
            data_sensitivity_level=initial_sensitivity,
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
            classification_status=DataClassificationApprovalStatusEnum.UNCLASSIFIED.value,
            owner_transfer_status=DataOwnerTransferStatusEnum.NONE.value,
        )
        db.add(asset)
        db.flush()

        if payload.cloud_asset_id is not None:
            cloud_link = DataAssetCloudLink(
                organization_id=organization_id,
                data_asset_id=asset.id,
                cloud_asset_id=payload.cloud_asset_id,
                hosting_role=DataCloudHostingRoleEnum.PRIMARY_STORE.value,
                notes="Primary cloud store linked at asset registration",
                linked_by_id=actor_id,
            )
            db.add(cloud_link)

        cls._commit_or_conflict(db, "Duplicate data asset code")
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_ASSET_CREATED",
            resource_type="data_asset",
            resource_id=asset.id,
            details={
                "asset_code": asset.asset_code,
                "asset_type": asset.asset_type,
                "lifecycle_state": asset.lifecycle_state,
                "owner_id": asset.owner_id,
                "steward_id": asset.steward_id,
                "cloud_asset_id": asset.cloud_asset_id,
            },
        )
        return asset

    @classmethod
    def list_governed_assets(
        cls,
        db: Session,
        organization_id: int,
        lifecycle_state: Optional[str] = None,
        sensitivity: Optional[DataSensitivityLevel] = None,
        classification_status: Optional[str] = None,
        owner_id: Optional[int] = None,
        steward_id: Optional[int] = None,
        cloud_asset_id: Optional[int] = None,
    ) -> List[DataAsset]:
        query = db.query(DataAsset).filter(DataAsset.organization_id == organization_id)
        if lifecycle_state:
            query = query.filter(DataAsset.lifecycle_state == lifecycle_state)
        if sensitivity:
            query = query.filter(DataAsset.data_sensitivity_level == sensitivity)
        if classification_status:
            query = query.filter(DataAsset.classification_status == classification_status)
        if owner_id is not None:
            query = query.filter(DataAsset.owner_id == owner_id)
        if steward_id is not None:
            query = query.filter(DataAsset.steward_id == steward_id)
        if cloud_asset_id is not None:
            query = query.filter(DataAsset.cloud_asset_id == cloud_asset_id)
        return query.order_by(DataAsset.id.desc()).all()

    @classmethod
    def update_governed_asset(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        actor_id: int,
        payload: GovernedDataAssetUpdate,
    ) -> DataAsset:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)

        cls._validate_optional_context_refs(
            db=db,
            organization_id=organization_id,
            business_process_id=payload.business_process_id,
            ai_system_id=payload.ai_system_id,
            vendor_id=payload.vendor_id,
        )

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "asset_type" and value is not None:
                setattr(asset, key, value.value if hasattr(value, "value") else str(value))
            else:
                setattr(asset, key, value)
        asset.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_ASSET_UPDATED",
            resource_type="data_asset",
            resource_id=asset.id,
            details={"asset_code": asset.asset_code, "updated_fields": list(update_data.keys())},
        )
        return asset

    @classmethod
    def register_discovered_asset(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        actor_id: int,
        payload: DataAssetRegisterRequest,
    ) -> DataAsset:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)
        if asset.lifecycle_state != DataAssetLifecycleEnum.DISCOVERED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only DISCOVERED assets can be registered via this transition (current: '{asset.lifecycle_state}')",
            )

        target_owner_id = payload.owner_id if payload.owner_id is not None else asset.owner_id
        cls._validate_tenant_user(db, organization_id, target_owner_id, "Data Owner")
        cls._validate_tenant_user(db, organization_id, payload.steward_id, "Data Steward")

        prev_state = asset.lifecycle_state
        asset.owner_id = target_owner_id
        asset.steward_id = payload.steward_id
        asset.lifecycle_state = DataAssetLifecycleEnum.REGISTERED.value
        asset.last_reviewed_at = datetime.now(timezone.utc)
        asset.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_ASSET_REGISTERED",
            resource_type="data_asset",
            resource_id=asset.id,
            details={
                "asset_code": asset.asset_code,
                "previous_state": prev_state,
                "new_state": asset.lifecycle_state,
                "owner_id": asset.owner_id,
                "steward_id": asset.steward_id,
            },
        )
        return asset

    @classmethod
    def activate_asset(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        actor_id: int,
    ) -> DataAsset:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)

        if asset.lifecycle_state == DataAssetLifecycleEnum.DISCOVERED.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot transition a DISCOVERED asset directly to ACTIVE; register and classify first",
            )
        if (
            asset.classification_status != DataClassificationApprovalStatusEnum.APPROVED.value
            or asset.classification_level_id is None
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Data asset must have an APPROVED governance classification level before transitioning to ACTIVE",
            )

        cls._validate_tenant_user(db, organization_id, asset.owner_id, "Data Owner")
        prev_state = asset.lifecycle_state
        asset.lifecycle_state = DataAssetLifecycleEnum.ACTIVE.value
        asset.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_ASSET_UPDATED",
            resource_type="data_asset",
            resource_id=asset.id,
            details={
                "asset_code": asset.asset_code,
                "transition": f"{prev_state}->ACTIVE",
            },
        )
        return asset

    # ─── 3. Classification Assignment, Downgrade Protection & Four-Eyes ───────

    @classmethod
    def request_classification(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        actor_id: int,
        payload: DataClassificationRequestCreate,
    ) -> DataClassificationRecord:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)

        if asset.lifecycle_state == DataAssetLifecycleEnum.DISCOVERED.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="DISCOVERED data asset must transition to REGISTERED before formal classification",
            )

        # Ensure no concurrent PENDING_APPROVAL classification record exists for this asset
        pending_existing = (
            db.query(DataClassificationRecord)
            .filter(
                DataClassificationRecord.data_asset_id == asset.id,
                DataClassificationRecord.status == DataClassificationRecordStatusEnum.PENDING_APPROVAL.value,
            )
            .first()
        )
        if pending_existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Data asset '{asset.asset_code}' already has a pending classification request (record {pending_existing.id})",
            )

        scheme = cls.get_scheme(db, organization_id, payload.scheme_id)
        level = (
            db.query(DataClassificationLevel)
            .filter(
                DataClassificationLevel.id == payload.level_id,
                DataClassificationLevel.organization_id == organization_id,
            )
            .first()
        )
        if not level:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Classification level {payload.level_id} not found",
            )
        if level.scheme_id != scheme.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Classification level {level.id} does not belong to scheme {scheme.id}",
            )
        if scheme.status != DataClassificationSchemeStatusEnum.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Classification scheme '{scheme.scheme_code}' is not ACTIVE (current: '{scheme.status}')",
            )

        # Determine version & change_type
        latest_record = (
            db.query(DataClassificationRecord)
            .filter(DataClassificationRecord.data_asset_id == asset.id)
            .order_by(DataClassificationRecord.version.desc())
            .first()
        )
        next_version = (latest_record.version + 1) if latest_record else 1

        prev_sens = asset.data_sensitivity_level
        new_sens = level.mapped_sensitivity_level
        prev_sens_rank = cls.SENSITIVITY_RANK_MAP[prev_sens]
        new_sens_rank = cls.SENSITIVITY_RANK_MAP[new_sens]

        current_level = (
            db.query(DataClassificationLevel)
            .filter(DataClassificationLevel.id == asset.classification_level_id)
            .first()
            if asset.classification_level_id
            else None
        )

        if asset.classification_level_id is None and latest_record is None:
            if new_sens_rank < prev_sens_rank:
                change_type = DataClassificationChangeTypeEnum.DOWNGRADE.value
            else:
                change_type = DataClassificationChangeTypeEnum.INITIAL.value
        else:
            is_rank_downgrade = (
                new_sens_rank < prev_sens_rank
                or (
                    current_level is not None
                    and current_level.scheme_id == scheme.id
                    and level.ordinal_rank < current_level.ordinal_rank
                )
            )
            is_rank_upgrade = (
                new_sens_rank > prev_sens_rank
                or (
                    current_level is not None
                    and current_level.scheme_id == scheme.id
                    and level.ordinal_rank > current_level.ordinal_rank
                )
            )
            if is_rank_downgrade:
                change_type = DataClassificationChangeTypeEnum.DOWNGRADE.value
            elif is_rank_upgrade:
                change_type = DataClassificationChangeTypeEnum.UPGRADE.value
            else:
                change_type = DataClassificationChangeTypeEnum.REVALIDATION.value

        requires_four_eyes = (
            change_type == DataClassificationChangeTypeEnum.DOWNGRADE.value
            or new_sens
            in (
                DataSensitivityLevel.RESTRICTED_PII,
                DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI,
            )
            or prev_sens
            in (
                DataSensitivityLevel.RESTRICTED_PII,
                DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI,
            )
            or level.requires_four_eyes_approval
            or payload.require_approval
        )

        now = datetime.now(timezone.utc)

        if requires_four_eyes:
            record = DataClassificationRecord(
                organization_id=organization_id,
                data_asset_id=asset.id,
                version=next_version,
                scheme_id=scheme.id,
                level_id=level.id,
                previous_level_id=asset.classification_level_id,
                previous_sensitivity_level=prev_sens,
                new_sensitivity_level=new_sens,
                change_type=change_type,
                status=DataClassificationRecordStatusEnum.PENDING_APPROVAL.value,
                justification=payload.justification,
                requested_by_id=actor_id,
            )
            asset.classification_status = DataClassificationApprovalStatusEnum.PENDING_APPROVAL.value
            asset.updated_at = now
            db.add(record)
            cls._commit_or_conflict(db, "Concurrent classification request conflict")
            db.refresh(record)
        else:
            # Supersede any prior APPROVED record
            (
                db.query(DataClassificationRecord)
                .filter(
                    DataClassificationRecord.data_asset_id == asset.id,
                    DataClassificationRecord.status == DataClassificationRecordStatusEnum.APPROVED.value,
                )
                .update(
                    {
                        "status": DataClassificationRecordStatusEnum.SUPERSEDED.value,
                        "effective_to": now,
                    },
                    synchronize_session=False,
                )
            )
            record = DataClassificationRecord(
                organization_id=organization_id,
                data_asset_id=asset.id,
                version=next_version,
                scheme_id=scheme.id,
                level_id=level.id,
                previous_level_id=asset.classification_level_id,
                previous_sensitivity_level=prev_sens,
                new_sensitivity_level=new_sens,
                change_type=change_type,
                status=DataClassificationRecordStatusEnum.APPROVED.value,
                justification=payload.justification,
                requested_by_id=actor_id,
                approved_by_id=actor_id,
                approved_at=now,
                effective_from=now,
            )
            asset.classification_scheme_id = scheme.id
            asset.classification_level_id = level.id
            asset.data_sensitivity_level = new_sens
            asset.classification_status = DataClassificationApprovalStatusEnum.APPROVED.value
            asset.classified_by_id = actor_id
            asset.classification_approved_by_id = actor_id
            asset.classification_approved_at = now
            asset.last_reviewed_at = now
            if level.default_retention_months and not asset.retention_period_months:
                asset.retention_period_months = level.default_retention_months
            if asset.lifecycle_state == DataAssetLifecycleEnum.REGISTERED.value:
                asset.lifecycle_state = DataAssetLifecycleEnum.CLASSIFIED.value
            asset.updated_at = now

            db.add(record)
            cls._commit_or_conflict(db, "Concurrent classification request conflict")
            db.refresh(record)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_CLASSIFICATION_REQUESTED",
            resource_type="data_classification_record",
            resource_id=record.id,
            details={
                "data_asset_id": asset.id,
                "version": record.version,
                "change_type": record.change_type,
                "previous_sensitivity": prev_sens.value if prev_sens else None,
                "new_sensitivity": new_sens.value,
                "status": record.status,
            },
        )
        return record

    @classmethod
    def list_asset_classifications(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
    ) -> List[DataClassificationRecord]:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        return (
            db.query(DataClassificationRecord)
            .filter(
                DataClassificationRecord.data_asset_id == asset.id,
                DataClassificationRecord.organization_id == organization_id,
            )
            .order_by(DataClassificationRecord.version.desc())
            .all()
        )

    @classmethod
    def approve_classification(
        cls,
        db: Session,
        organization_id: int,
        record_id: int,
        approver_id: int,
    ) -> DataClassificationRecord:
        record = (
            db.query(DataClassificationRecord)
            .filter(
                DataClassificationRecord.id == record_id,
                DataClassificationRecord.organization_id == organization_id,
            )
            .first()
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Classification record {record_id} not found",
            )
        if record.status != DataClassificationRecordStatusEnum.PENDING_APPROVAL.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Classification record {record_id} has already been finalized with status '{record.status}'",
            )
        if record.requested_by_id == approver_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Segregation of Duties violation: requester cannot self-approve classification",
            )

        asset = cls.get_governed_asset(db, organization_id, record.data_asset_id)
        cls._ensure_not_retired(asset)

        now = datetime.now(timezone.utc)
        (
            db.query(DataClassificationRecord)
            .filter(
                DataClassificationRecord.data_asset_id == asset.id,
                DataClassificationRecord.status == DataClassificationRecordStatusEnum.APPROVED.value,
                DataClassificationRecord.id != record.id,
            )
            .update(
                {
                    "status": DataClassificationRecordStatusEnum.SUPERSEDED.value,
                    "effective_to": now,
                },
                synchronize_session=False,
            )
        )

        record.status = DataClassificationRecordStatusEnum.APPROVED.value
        record.approved_by_id = approver_id
        record.approved_at = now
        record.effective_from = now

        asset.classification_scheme_id = record.scheme_id
        asset.classification_level_id = record.level_id
        asset.data_sensitivity_level = record.new_sensitivity_level
        asset.classification_status = DataClassificationApprovalStatusEnum.APPROVED.value
        asset.classified_by_id = record.requested_by_id
        asset.classification_approved_by_id = approver_id
        asset.classification_approved_at = now
        asset.last_reviewed_at = now
        if asset.lifecycle_state == DataAssetLifecycleEnum.REGISTERED.value:
            asset.lifecycle_state = DataAssetLifecycleEnum.CLASSIFIED.value
        asset.updated_at = now

        db.commit()
        db.refresh(record)

        action_name = (
            "DATA_GOV_CLASSIFICATION_DOWNGRADED"
            if record.change_type == DataClassificationChangeTypeEnum.DOWNGRADE.value
            else "DATA_GOV_CLASSIFICATION_APPROVED"
        )
        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=approver_id,
            action=action_name,
            resource_type="data_classification_record",
            resource_id=record.id,
            details={
                "data_asset_id": asset.id,
                "change_type": record.change_type,
                "requested_by_id": record.requested_by_id,
                "approved_by_id": approver_id,
                "new_sensitivity": record.new_sensitivity_level.value,
            },
        )
        return record

    @classmethod
    def reject_classification(
        cls,
        db: Session,
        organization_id: int,
        record_id: int,
        reviewer_id: int,
        payload: DataClassificationRejectRequest,
    ) -> DataClassificationRecord:
        record = (
            db.query(DataClassificationRecord)
            .filter(
                DataClassificationRecord.id == record_id,
                DataClassificationRecord.organization_id == organization_id,
            )
            .first()
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Classification record {record_id} not found",
            )
        if record.status != DataClassificationRecordStatusEnum.PENDING_APPROVAL.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Classification record {record_id} has already been finalized with status '{record.status}'",
            )

        asset = cls.get_governed_asset(db, organization_id, record.data_asset_id)
        now = datetime.now(timezone.utc)

        record.status = DataClassificationRecordStatusEnum.REJECTED.value
        record.approved_by_id = reviewer_id
        record.approved_at = now
        record.rejection_reason = payload.rejection_reason

        # Restore asset classification_status to APPROVED if it had a prior approved level, else UNCLASSIFIED
        if asset.classification_level_id is not None:
            asset.classification_status = DataClassificationApprovalStatusEnum.APPROVED.value
        else:
            asset.classification_status = DataClassificationApprovalStatusEnum.REJECTED.value
        asset.updated_at = now

        db.commit()
        db.refresh(record)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=reviewer_id,
            action="DATA_GOV_CLASSIFICATION_REJECTED",
            resource_type="data_classification_record",
            resource_id=record.id,
            details={
                "data_asset_id": asset.id,
                "requested_by_id": record.requested_by_id,
                "rejected_by_id": reviewer_id,
                "rejection_reason": payload.rejection_reason,
            },
        )
        return record

    # ─── 4. Ownership & Stewardship Management ────────────────────────────────

    @classmethod
    def update_ownership(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        actor_id: int,
        payload: DataOwnershipUpdateRequest,
    ) -> DataAsset:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)

        if payload.owner_id is None and payload.steward_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one of owner_id or steward_id must be provided",
            )

        if payload.owner_id is not None:
            cls._validate_tenant_user(db, organization_id, payload.owner_id, "Data Owner")
        if payload.steward_id is not None:
            cls._validate_tenant_user(db, organization_id, payload.steward_id, "Data Steward")

        owner_unchanged = payload.owner_id is None or payload.owner_id == asset.owner_id
        steward_unchanged = payload.steward_id is None or payload.steward_id == asset.steward_id
        if owner_unchanged and steward_unchanged:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Specified owner_id and steward_id are already assigned to this asset",
            )

        prev_owner_id = asset.owner_id
        prev_steward_id = asset.steward_id
        now = datetime.now(timezone.utc)

        if payload.steward_id is not None and payload.steward_id != asset.steward_id:
            asset.steward_id = payload.steward_id

        if payload.owner_id is not None and payload.owner_id != asset.owner_id:
            is_restricted_asset = asset.data_sensitivity_level in (
                DataSensitivityLevel.RESTRICTED_PII,
                DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI,
            )
            if is_restricted_asset or payload.require_approval:
                if asset.owner_transfer_status == DataOwnerTransferStatusEnum.PENDING_TRANSFER.value:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Data asset '{asset.asset_code}' already has a pending ownership transfer request",
                    )
                asset.owner_transfer_status = DataOwnerTransferStatusEnum.PENDING_TRANSFER.value
                asset.pending_owner_id = payload.owner_id
                asset.owner_transfer_requested_by_id = actor_id
                asset.owner_transfer_justification = payload.justification
            else:
                asset.owner_id = payload.owner_id
                asset.owner_transfer_status = DataOwnerTransferStatusEnum.APPROVED.value
                asset.pending_owner_id = None
                asset.owner_transfer_requested_by_id = actor_id
                asset.owner_transfer_justification = payload.justification

        asset.last_reviewed_at = now
        asset.updated_at = now
        db.commit()
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_OWNER_ASSIGNED",
            resource_type="data_asset",
            resource_id=asset.id,
            details={
                "asset_code": asset.asset_code,
                "previous_owner_id": prev_owner_id,
                "new_owner_id": asset.owner_id,
                "pending_owner_id": asset.pending_owner_id,
                "previous_steward_id": prev_steward_id,
                "new_steward_id": asset.steward_id,
                "owner_transfer_status": asset.owner_transfer_status,
                "justification": payload.justification,
            },
        )
        return asset

    @classmethod
    def approve_ownership_transfer(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        approver_id: int,
    ) -> DataAsset:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)

        if (
            asset.owner_transfer_status != DataOwnerTransferStatusEnum.PENDING_TRANSFER.value
            or asset.pending_owner_id is None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Data asset '{asset.asset_code}' does not have a pending ownership transfer",
            )
        if asset.owner_transfer_requested_by_id == approver_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Segregation of Duties violation: requester cannot self-approve ownership transfer",
            )

        cls._validate_tenant_user(db, organization_id, asset.pending_owner_id, "New Data Owner")

        prev_owner_id = asset.owner_id
        asset.owner_id = asset.pending_owner_id
        asset.pending_owner_id = None
        asset.owner_transfer_status = DataOwnerTransferStatusEnum.APPROVED.value
        asset.last_reviewed_at = datetime.now(timezone.utc)
        asset.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=approver_id,
            action="DATA_GOV_OWNER_TRANSFERRED",
            resource_type="data_asset",
            resource_id=asset.id,
            details={
                "asset_code": asset.asset_code,
                "previous_owner_id": prev_owner_id,
                "new_owner_id": asset.owner_id,
                "requested_by_id": asset.owner_transfer_requested_by_id,
                "approved_by_id": approver_id,
            },
        )
        return asset

    # ─── 5. Directed Lineage Engine, DAG Cycle Detection & Flow Gate ──────────

    @classmethod
    def _validate_no_lineage_cycle(
        cls,
        db: Session,
        organization_id: int,
        source_asset_id: int,
        target_asset_id: int,
        exclude_edge_code: Optional[str] = None,
    ) -> None:
        if source_asset_id == target_asset_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Lineage DAG violation: self-loop (source_data_asset_id == target_data_asset_id) is prohibited",
            )

        edges_query = db.query(
            DataLineageEdge.source_data_asset_id,
            DataLineageEdge.target_data_asset_id,
            DataLineageEdge.edge_code,
        ).filter(
            DataLineageEdge.organization_id == organization_id,
            DataLineageEdge.status.in_(
                [
                    DataLineageStatusEnum.ACTIVE.value,
                    DataLineageStatusEnum.PENDING_APPROVAL.value,
                ]
            ),
        )
        if exclude_edge_code:
            edges_query = edges_query.filter(DataLineageEdge.edge_code != exclude_edge_code)

        adj: Dict[int, List[int]] = {}
        for src_id, dst_id, _ in edges_query.all():
            adj.setdefault(src_id, []).append(dst_id)

        # BFS reachability from target_asset_id -> source_asset_id
        visited = {target_asset_id}
        queue = deque([target_asset_id])
        while queue:
            curr = queue.popleft()
            if curr == source_asset_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Lineage DAG cycle detected: target asset {target_asset_id} "
                        f"already has a directed path to source asset {source_asset_id}"
                    ),
                )
            for nxt in adj.get(curr, []):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)

    @classmethod
    def create_or_version_lineage_edge(
        cls,
        db: Session,
        organization_id: int,
        actor_id: int,
        payload: DataLineageEdgeCreate,
    ) -> DataLineageEdge:
        if payload.source_data_asset_id == payload.target_data_asset_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Lineage DAG violation: self-loop (source_data_asset_id == target_data_asset_id) is prohibited",
            )

        source_asset = cls.get_governed_asset(db, organization_id, payload.source_data_asset_id)
        target_asset = cls.get_governed_asset(db, organization_id, payload.target_data_asset_id)

        if source_asset.lifecycle_state == DataAssetLifecycleEnum.RETIRED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot create lineage from RETIRED source asset '{source_asset.asset_code}'",
            )
        if target_asset.lifecycle_state == DataAssetLifecycleEnum.RETIRED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot create lineage into RETIRED target asset '{target_asset.asset_code}'",
            )
        if source_asset.lifecycle_state == DataAssetLifecycleEnum.DEPRECATED.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot create new outbound lineage from DEPRECATED source asset '{source_asset.asset_code}'",
            )

        if payload.processing_activity_id is not None:
            pa = (
                db.query(ProcessingActivity)
                .filter(
                    ProcessingActivity.id == payload.processing_activity_id,
                    ProcessingActivity.organization_id == organization_id,
                )
                .first()
            )
            if not pa:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Processing activity {payload.processing_activity_id} not found in this organization",
                )
            if pa.lifecycle_state == ProcessingLifecycleState.RETIRED:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Cannot link lineage to RETIRED processing activity '{pa.activity_code}'",
                )

        if payload.cloud_asset_id is not None:
            cls._validate_tenant_cloud_asset(db, organization_id, payload.cloud_asset_id)

        # Check existing versions of edge_code or duplicate active pair
        existing_by_code = (
            db.query(DataLineageEdge)
            .filter(
                DataLineageEdge.organization_id == organization_id,
                DataLineageEdge.edge_code == payload.edge_code,
            )
            .order_by(DataLineageEdge.version.desc())
            .first()
        )
        if existing_by_code is None:
            # Check if an active/pending edge with a DIFFERENT code already connects the same source -> target
            dup_pair = (
                db.query(DataLineageEdge)
                .filter(
                    DataLineageEdge.organization_id == organization_id,
                    DataLineageEdge.source_data_asset_id == source_asset.id,
                    DataLineageEdge.target_data_asset_id == target_asset.id,
                    DataLineageEdge.status.in_(
                        [
                            DataLineageStatusEnum.ACTIVE.value,
                            DataLineageStatusEnum.PENDING_APPROVAL.value,
                        ]
                    ),
                )
                .first()
            )
            if dup_pair:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Active or pending lineage edge '{dup_pair.edge_code}' already connects "
                        f"asset {source_asset.id} to asset {target_asset.id}"
                    ),
                )
            next_version = 1
        else:
            if (
                existing_by_code.source_data_asset_id == source_asset.id
                and existing_by_code.target_data_asset_id == target_asset.id
                and existing_by_code.relationship_type == payload.relationship_type.value
                and (existing_by_code.transformation_summary or "") == (payload.transformation_summary or "")
                and existing_by_code.is_encrypted_in_transit == payload.is_encrypted_in_transit
                and existing_by_code.is_masked_or_anonymized == payload.is_masked_or_anonymized
                and existing_by_code.status in (
                    DataLineageStatusEnum.ACTIVE.value,
                    DataLineageStatusEnum.PENDING_APPROVAL.value,
                )
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Lineage edge '{payload.edge_code}' with identical attributes is already active/pending",
                )
            next_version = existing_by_code.version + 1

        # DAG Cycle Check
        cls._validate_no_lineage_cycle(
            db=db,
            organization_id=organization_id,
            source_asset_id=source_asset.id,
            target_asset_id=target_asset.id,
            exclude_edge_code=payload.edge_code if existing_by_code else None,
        )

        # Sensitivity Flow Gate (Section 14.1 of Hardened Architecture)
        src_rank = cls.SENSITIVITY_RANK_MAP[source_asset.data_sensitivity_level]
        dst_rank = cls.SENSITIVITY_RANK_MAP[target_asset.data_sensitivity_level]
        is_sensitivity_downgrade = src_rank > dst_rank

        if is_sensitivity_downgrade:
            if (
                src_rank >= 4
                and target_asset.data_sensitivity_level == DataSensitivityLevel.PUBLIC
                and not payload.is_masked_or_anonymized
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Sensitivity flow violation: RESTRICTED_PII or SPECIAL_CATEGORY_SENSITIVE_PHI data "
                        "cannot flow unmasked into a PUBLIC target asset"
                    ),
                )
            if not payload.transformation_summary or len(payload.transformation_summary.strip()) < 10:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Sensitivity downgrade lineage flow requires a documented transformation_summary "
                        "(minimum 10 characters) explaining masking, tokenization, or field filtering"
                    ),
                )
            edge_status = DataLineageStatusEnum.PENDING_APPROVAL.value
        elif payload.require_approval:
            edge_status = DataLineageStatusEnum.PENDING_APPROVAL.value
        else:
            edge_status = DataLineageStatusEnum.ACTIVE.value

        now = datetime.now(timezone.utc)
        if existing_by_code and edge_status == DataLineageStatusEnum.ACTIVE.value:
            (
                db.query(DataLineageEdge)
                .filter(
                    DataLineageEdge.organization_id == organization_id,
                    DataLineageEdge.edge_code == payload.edge_code,
                    DataLineageEdge.status == DataLineageStatusEnum.ACTIVE.value,
                )
                .update(
                    {
                        "status": DataLineageStatusEnum.SUPERSEDED.value,
                        "effective_to": now,
                    },
                    synchronize_session=False,
                )
            )

        provenance_hash = cls.compute_lineage_provenance_hash(
            organization_id=organization_id,
            edge_code=payload.edge_code,
            version=next_version,
            source_data_asset_id=source_asset.id,
            target_data_asset_id=target_asset.id,
            relationship_type=payload.relationship_type.value,
            transformation_summary=payload.transformation_summary,
            is_encrypted_in_transit=payload.is_encrypted_in_transit,
            is_masked_or_anonymized=payload.is_masked_or_anonymized,
            processing_activity_id=payload.processing_activity_id,
            cloud_asset_id=payload.cloud_asset_id,
            created_by_id=actor_id,
            effective_from=now,
        )

        edge = DataLineageEdge(
            organization_id=organization_id,
            edge_code=payload.edge_code,
            version=next_version,
            source_data_asset_id=source_asset.id,
            target_data_asset_id=target_asset.id,
            relationship_type=payload.relationship_type.value,
            transformation_summary=payload.transformation_summary,
            field_mapping_manifest=payload.field_mapping_manifest,
            is_encrypted_in_transit=payload.is_encrypted_in_transit,
            is_masked_or_anonymized=payload.is_masked_or_anonymized,
            processing_activity_id=payload.processing_activity_id,
            cloud_asset_id=payload.cloud_asset_id,
            status=edge_status,
            provenance_hash=provenance_hash,
            created_by_id=actor_id,
            approved_by_id=actor_id if edge_status == DataLineageStatusEnum.ACTIVE.value else None,
            approved_at=now if edge_status == DataLineageStatusEnum.ACTIVE.value else None,
            effective_from=now,
        )
        db.add(edge)
        cls._commit_or_conflict(db, "Duplicate lineage edge code and version")
        db.refresh(edge)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_LINEAGE_REVISED" if next_version > 1 else "DATA_GOV_LINEAGE_CREATED",
            resource_type="data_lineage_edge",
            resource_id=edge.id,
            details={
                "edge_code": edge.edge_code,
                "version": edge.version,
                "source_data_asset_id": edge.source_data_asset_id,
                "target_data_asset_id": edge.target_data_asset_id,
                "status": edge.status,
                "provenance_hash": edge.provenance_hash,
            },
        )
        return edge

    @classmethod
    def list_lineage_edges(
        cls,
        db: Session,
        organization_id: int,
        data_asset_id: Optional[int] = None,
        status_filter: Optional[str] = None,
    ) -> List[DataLineageEdge]:
        query = db.query(DataLineageEdge).filter(
            DataLineageEdge.organization_id == organization_id
        )
        if data_asset_id is not None:
            query = query.filter(
                (DataLineageEdge.source_data_asset_id == data_asset_id)
                | (DataLineageEdge.target_data_asset_id == data_asset_id)
            )
        if status_filter:
            query = query.filter(DataLineageEdge.status == status_filter)
        return query.order_by(DataLineageEdge.id.desc()).all()

    @classmethod
    def approve_lineage_edge(
        cls,
        db: Session,
        organization_id: int,
        edge_id: int,
        approver_id: int,
    ) -> DataLineageEdge:
        edge = (
            db.query(DataLineageEdge)
            .filter(
                DataLineageEdge.id == edge_id,
                DataLineageEdge.organization_id == organization_id,
            )
            .first()
        )
        if not edge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lineage edge {edge_id} not found",
            )
        if edge.status != DataLineageStatusEnum.PENDING_APPROVAL.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Lineage edge {edge_id} is not in PENDING_APPROVAL status (current: '{edge.status}')",
            )
        if edge.created_by_id == approver_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Segregation of Duties violation: lineage creator cannot self-approve restricted flow",
            )

        now = datetime.now(timezone.utc)
        (
            db.query(DataLineageEdge)
            .filter(
                DataLineageEdge.organization_id == organization_id,
                DataLineageEdge.edge_code == edge.edge_code,
                DataLineageEdge.status == DataLineageStatusEnum.ACTIVE.value,
                DataLineageEdge.id != edge.id,
            )
            .update(
                {
                    "status": DataLineageStatusEnum.SUPERSEDED.value,
                    "effective_to": now,
                },
                synchronize_session=False,
            )
        )

        edge.status = DataLineageStatusEnum.ACTIVE.value
        edge.approved_by_id = approver_id
        edge.approved_at = now
        db.commit()
        db.refresh(edge)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=approver_id,
            action="DATA_GOV_LINEAGE_APPROVED",
            resource_type="data_lineage_edge",
            resource_id=edge.id,
            details={
                "edge_code": edge.edge_code,
                "version": edge.version,
                "created_by_id": edge.created_by_id,
                "approved_by_id": approver_id,
                "provenance_hash": edge.provenance_hash,
            },
        )
        return edge

    @classmethod
    def revoke_lineage_edge(
        cls,
        db: Session,
        organization_id: int,
        edge_id: int,
        actor_id: int,
        payload: DataLineageEdgeRevokeRequest,
    ) -> DataLineageEdge:
        edge = (
            db.query(DataLineageEdge)
            .filter(
                DataLineageEdge.id == edge_id,
                DataLineageEdge.organization_id == organization_id,
            )
            .first()
        )
        if not edge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lineage edge {edge_id} not found",
            )
        if edge.status == DataLineageStatusEnum.REVOKED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Lineage edge {edge_id} is already REVOKED",
            )

        now = datetime.now(timezone.utc)
        edge.status = DataLineageStatusEnum.REVOKED.value
        edge.revoked_by_id = actor_id
        edge.revoked_at = now
        edge.revocation_reason = payload.revocation_reason
        edge.effective_to = now
        db.commit()
        db.refresh(edge)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_LINEAGE_REVOKED",
            resource_type="data_lineage_edge",
            resource_id=edge.id,
            details={
                "edge_code": edge.edge_code,
                "version": edge.version,
                "revoked_by_id": actor_id,
                "revocation_reason": payload.revocation_reason,
            },
        )
        return edge

    # ─── 6. Cross-Domain Bridges (Cloud, Processing, Control, Evidence) ───────

    @classmethod
    def link_cloud_asset(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        actor_id: int,
        payload: DataAssetCloudLinkCreate,
    ) -> DataAssetCloudLink:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)
        cloud_asset = cls._validate_tenant_cloud_asset(db, organization_id, payload.cloud_asset_id)

        existing = (
            db.query(DataAssetCloudLink)
            .filter(
                DataAssetCloudLink.organization_id == organization_id,
                DataAssetCloudLink.data_asset_id == asset.id,
                DataAssetCloudLink.cloud_asset_id == cloud_asset.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cloud asset {cloud_asset.id} is already linked to data asset {asset.id}",
            )

        link = DataAssetCloudLink(
            organization_id=organization_id,
            data_asset_id=asset.id,
            cloud_asset_id=cloud_asset.id,
            hosting_role=payload.hosting_role.value,
            notes=payload.notes,
            linked_by_id=actor_id,
        )
        if payload.hosting_role == DataCloudHostingRoleEnum.PRIMARY_STORE or asset.cloud_asset_id is None:
            asset.cloud_asset_id = cloud_asset.id
            asset.updated_at = datetime.now(timezone.utc)

        db.add(link)
        cls._commit_or_conflict(db, "Duplicate cloud asset link")
        db.refresh(link)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_CLOUD_LINK_CREATED",
            resource_type="data_asset_cloud_link",
            resource_id=link.id,
            details={
                "data_asset_id": asset.id,
                "cloud_asset_id": cloud_asset.id,
                "hosting_role": link.hosting_role,
            },
        )
        return link

    @classmethod
    def link_processing_activity(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        actor_id: int,
        payload: DataAssetProcessingLinkCreate,
    ) -> DataAssetProcessingLink:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)

        activity = (
            db.query(ProcessingActivity)
            .filter(
                ProcessingActivity.id == payload.processing_activity_id,
                ProcessingActivity.organization_id == organization_id,
            )
            .first()
        )
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processing activity {payload.processing_activity_id} not found in this organization",
            )
        if activity.lifecycle_state == ProcessingLifecycleState.RETIRED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot link data asset to a RETIRED processing activity '{activity.activity_code}'",
            )

        existing = (
            db.query(DataAssetProcessingLink)
            .filter(
                DataAssetProcessingLink.organization_id == organization_id,
                DataAssetProcessingLink.data_asset_id == asset.id,
                DataAssetProcessingLink.processing_activity_id == activity.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Processing activity {activity.id} is already linked to data asset {asset.id}",
            )

        link = DataAssetProcessingLink(
            organization_id=organization_id,
            data_asset_id=asset.id,
            processing_activity_id=activity.id,
            usage_role=payload.usage_role.value,
            notes=payload.notes,
            linked_by_id=actor_id,
        )
        db.add(link)
        cls._commit_or_conflict(db, "Duplicate processing activity link")
        db.refresh(link)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_PROCESSING_LINK_CREATED",
            resource_type="data_asset_processing_link",
            resource_id=link.id,
            details={
                "data_asset_id": asset.id,
                "processing_activity_id": activity.id,
                "usage_role": link.usage_role,
            },
        )
        return link

    @classmethod
    def link_control(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        actor_id: int,
        payload: DataAssetControlLinkCreate,
    ) -> DataAssetControlLink:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)

        control = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == payload.organization_control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .first()
        )
        if not control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization control {payload.organization_control_id} not found in this organization",
            )

        existing = (
            db.query(DataAssetControlLink)
            .filter(
                DataAssetControlLink.organization_id == organization_id,
                DataAssetControlLink.data_asset_id == asset.id,
                DataAssetControlLink.organization_control_id == control.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Control {control.id} is already linked to data asset {asset.id}",
            )

        link = DataAssetControlLink(
            organization_id=organization_id,
            data_asset_id=asset.id,
            organization_control_id=control.id,
            control_objective=payload.control_objective.value,
            is_mandatory=payload.is_mandatory,
            coverage_notes=payload.coverage_notes,
            linked_by_id=actor_id,
        )
        db.add(link)
        cls._commit_or_conflict(db, "Duplicate control link")
        db.refresh(link)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_CONTROL_LINK_CREATED",
            resource_type="data_asset_control_link",
            resource_id=link.id,
            details={
                "data_asset_id": asset.id,
                "organization_control_id": control.id,
                "control_objective": link.control_objective,
            },
        )
        return link

    @classmethod
    def _validate_usable_evidence(
        cls,
        db: Session,
        organization_id: int,
        evidence_item_id: int,
    ) -> EvidenceItem:
        ev = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == evidence_item_id,
                EvidenceItem.organization_id == organization_id,
            )
            .first()
        )
        if not ev:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence item {evidence_item_id} not found in this organization",
            )
        if ev.status in (EvidenceStatusEnum.REJECTED, EvidenceStatusEnum.SUPERSEDED):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot use evidence item {evidence_item_id} with status '{ev.status.value}'",
            )
        return ev

    @classmethod
    def link_evidence(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        actor_id: int,
        payload: DataAssetEvidenceLinkCreate,
    ) -> DataAssetEvidenceLink:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)
        ev = cls._validate_usable_evidence(db, organization_id, payload.evidence_item_id)

        existing = (
            db.query(DataAssetEvidenceLink)
            .filter(
                DataAssetEvidenceLink.organization_id == organization_id,
                DataAssetEvidenceLink.data_asset_id == asset.id,
                DataAssetEvidenceLink.evidence_item_id == ev.id,
                DataAssetEvidenceLink.evidence_purpose == payload.evidence_purpose.value,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Evidence item {ev.id} is already linked to data asset {asset.id} for purpose '{payload.evidence_purpose.value}'",
            )

        link = DataAssetEvidenceLink(
            organization_id=organization_id,
            data_asset_id=asset.id,
            evidence_item_id=ev.id,
            evidence_purpose=payload.evidence_purpose.value,
            notes=payload.notes,
            linked_by_id=actor_id,
        )
        db.add(link)
        cls._commit_or_conflict(db, "Duplicate evidence link")
        db.refresh(link)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_EVIDENCE_LINK_CREATED",
            resource_type="data_asset_evidence_link",
            resource_id=link.id,
            details={
                "data_asset_id": asset.id,
                "evidence_item_id": ev.id,
                "evidence_purpose": link.evidence_purpose,
            },
        )
        return link

    # ─── 7. Deprecation, Retirement & Governed Restoration ────────────────────

    @classmethod
    def deprecate_asset(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        actor_id: int,
        payload: DataAssetDeprecateRequest,
    ) -> DataAsset:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)

        prev_state = asset.lifecycle_state
        asset.lifecycle_state = DataAssetLifecycleEnum.DEPRECATED.value
        asset.deprecation_notes = payload.deprecation_notes
        asset.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_ASSET_DEPRECATED",
            resource_type="data_asset",
            resource_id=asset.id,
            details={
                "asset_code": asset.asset_code,
                "previous_state": prev_state,
                "deprecation_notes": payload.deprecation_notes,
            },
        )
        return asset

    @classmethod
    def request_retirement(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        actor_id: int,
        payload: DataAssetRetireRequest,
    ) -> DataAsset:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        cls._ensure_not_retired(asset)

        if payload.disposal_method == DataDisposalMethodEnum.NONE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Valid disposal_method (not NONE) is required for retirement",
            )

        is_high_sensitivity = asset.data_sensitivity_level in (
            DataSensitivityLevel.CONFIDENTIAL,
            DataSensitivityLevel.RESTRICTED_PII,
            DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI,
        )
        if is_high_sensitivity and payload.retirement_evidence_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="retirement_evidence_id is mandatory when retiring CONFIDENTIAL, RESTRICTED_PII, or PHI data assets",
            )

        if payload.retirement_evidence_id is not None:
            cls._validate_usable_evidence(db, organization_id, payload.retirement_evidence_id)

        asset.disposal_method = payload.disposal_method.value
        asset.retirement_notes = payload.retirement_notes
        asset.retirement_evidence_id = payload.retirement_evidence_id
        asset.retirement_requested_by_id = actor_id
        if asset.lifecycle_state != DataAssetLifecycleEnum.DEPRECATED.value:
            asset.lifecycle_state = DataAssetLifecycleEnum.DEPRECATED.value
        asset.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="DATA_GOV_ASSET_RETIRE_REQUESTED",
            resource_type="data_asset",
            resource_id=asset.id,
            details={
                "asset_code": asset.asset_code,
                "requested_by_id": actor_id,
                "disposal_method": asset.disposal_method,
                "retirement_evidence_id": asset.retirement_evidence_id,
            },
        )
        return asset

    @classmethod
    def finalize_retirement(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        approver_id: int,
        payload: DataAssetRetireRequest,
    ) -> DataAsset:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        if asset.lifecycle_state == DataAssetLifecycleEnum.RETIRED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Data asset '{asset.asset_code}' is already RETIRED",
            )

        if payload.disposal_method == DataDisposalMethodEnum.NONE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Valid disposal_method (not NONE) is required to retire a data asset",
            )

        is_high_sensitivity = asset.data_sensitivity_level in (
            DataSensitivityLevel.CONFIDENTIAL,
            DataSensitivityLevel.RESTRICTED_PII,
            DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI,
        )
        ev_id = payload.retirement_evidence_id or asset.retirement_evidence_id
        if is_high_sensitivity and ev_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="retirement_evidence_id referencing a valid EvidenceItem is mandatory to retire confidential/restricted data assets",
            )
        if ev_id is not None:
            cls._validate_usable_evidence(db, organization_id, ev_id)

        if asset.retirement_requested_by_id is not None and asset.retirement_requested_by_id == approver_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Segregation of Duties violation: retirement requester cannot self-approve retirement",
            )

        now = datetime.now(timezone.utc)
        # Revoke any active/pending lineage edges involving this asset
        (
            db.query(DataLineageEdge)
            .filter(
                DataLineageEdge.organization_id == organization_id,
                (DataLineageEdge.source_data_asset_id == asset.id)
                | (DataLineageEdge.target_data_asset_id == asset.id),
                DataLineageEdge.status.in_(
                    [
                        DataLineageStatusEnum.ACTIVE.value,
                        DataLineageStatusEnum.PENDING_APPROVAL.value,
                    ]
                ),
            )
            .update(
                {
                    "status": DataLineageStatusEnum.REVOKED.value,
                    "revoked_by_id": approver_id,
                    "revoked_at": now,
                    "revocation_reason": f"Asset '{asset.asset_code}' retired",
                    "effective_to": now,
                },
                synchronize_session=False,
            )
        )

        asset.lifecycle_state = DataAssetLifecycleEnum.RETIRED.value
        asset.disposal_method = payload.disposal_method.value
        asset.retirement_notes = payload.retirement_notes
        asset.retirement_evidence_id = ev_id
        asset.retired_by_id = approver_id
        asset.retired_at = now
        asset.updated_at = now
        db.commit()
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=approver_id,
            action="DATA_GOV_ASSET_RETIRED",
            resource_type="data_asset",
            resource_id=asset.id,
            details={
                "asset_code": asset.asset_code,
                "requested_by_id": asset.retirement_requested_by_id,
                "retired_by_id": approver_id,
                "disposal_method": asset.disposal_method,
                "retirement_evidence_id": asset.retirement_evidence_id,
            },
        )
        return asset

    @classmethod
    def restore_retired_asset(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
        approver_id: int,
        payload: DataAssetRestoreRequest,
    ) -> DataAsset:
        asset = cls.get_governed_asset(db, organization_id, asset_id)
        if asset.lifecycle_state != DataAssetLifecycleEnum.RETIRED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Data asset '{asset.asset_code}' is not RETIRED (current: '{asset.lifecycle_state}')",
            )
        if asset.retired_by_id is not None and asset.retired_by_id == approver_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Segregation of Duties violation: the user who retired the asset cannot self-approve restoration",
            )

        now = datetime.now(timezone.utc)
        asset.lifecycle_state = (
            DataAssetLifecycleEnum.ACTIVE.value
            if asset.classification_level_id is not None
            else DataAssetLifecycleEnum.REGISTERED.value
        )
        asset.retirement_notes = f"{asset.retirement_notes or ''} | RESTORED: {payload.restoration_justification}".strip(" |")
        asset.last_reviewed_at = now
        asset.updated_at = now
        db.commit()
        db.refresh(asset)

        cls._log_audit(
            db=db,
            organization_id=organization_id,
            actor_id=approver_id,
            action="DATA_GOV_ASSET_RESTORED",
            resource_type="data_asset",
            resource_id=asset.id,
            details={
                "asset_code": asset.asset_code,
                "restored_by_id": approver_id,
                "restoration_justification": payload.restoration_justification,
            },
        )
        return asset

    # ─── 8. Cloud Posture Alignment, Dossier & Telemetry ──────────────────────

    @classmethod
    def evaluate_asset_cloud_alignment(
        cls,
        db: Session,
        organization_id: int,
        asset: DataAsset,
    ) -> CloudPostureAlignmentInfo:
        cloud_links = (
            db.query(DataAssetCloudLink)
            .filter(
                DataAssetCloudLink.organization_id == organization_id,
                DataAssetCloudLink.data_asset_id == asset.id,
            )
            .all()
        )
        cloud_ids = {lnk.cloud_asset_id for lnk in cloud_links}
        if asset.cloud_asset_id is not None:
            cloud_ids.add(asset.cloud_asset_id)

        if not cloud_ids:
            return CloudPostureAlignmentInfo(
                cloud_posture_aligned=True,
                linked_cloud_asset_ids=[],
                mismatch_flags=[],
            )

        cloud_assets = (
            db.query(CloudAsset)
            .filter(
                CloudAsset.organization_id == organization_id,
                CloudAsset.id.in_(list(cloud_ids)),
            )
            .all()
        )

        mismatch_flags: List[str] = []
        requires_enc = asset.is_encrypted_at_rest or (
            cls.SENSITIVITY_RANK_MAP[asset.data_sensitivity_level] >= 3
        )
        is_non_public = asset.data_sensitivity_level != DataSensitivityLevel.PUBLIC

        for ca in cloud_assets:
            if requires_enc and not ca.encryption_enabled:
                mismatch_flags.append("CLOUD_ENCRYPTION_MISMATCH")
            if is_non_public and ca.is_internet_facing:
                mismatch_flags.append("CLOUD_PUBLIC_EXPOSURE_MISMATCH")
            if ca.posture_status == CloudPostureStatusEnum.NON_COMPLIANT:
                mismatch_flags.append("CLOUD_POSTURE_NON_COMPLIANT")
            if (
                asset.lifecycle_state == DataAssetLifecycleEnum.ACTIVE.value
                and ca.lifecycle_state == CloudLifecycleStateEnum.DECOMMISSIONED
            ):
                mismatch_flags.append("CLOUD_HOST_DECOMMISSIONED")

        unique_flags = sorted(set(mismatch_flags))
        return CloudPostureAlignmentInfo(
            cloud_posture_aligned=(len(unique_flags) == 0),
            linked_cloud_asset_ids=sorted(cloud_ids),
            mismatch_flags=unique_flags,
        )

    @classmethod
    def get_asset_governance_dossier(
        cls,
        db: Session,
        organization_id: int,
        asset_id: int,
    ) -> GovernedDataAssetDossierResponse:
        asset = cls.get_governed_asset(db, organization_id, asset_id)

        owner = db.query(User).filter(User.id == asset.owner_id).first()
        owner_active = bool(owner and getattr(owner, "is_active", True))

        steward_active: Optional[bool] = None
        if asset.steward_id is not None:
            steward = db.query(User).filter(User.id == asset.steward_id).first()
            steward_active = bool(steward and getattr(steward, "is_active", True))

        cloud_alignment = cls.evaluate_asset_cloud_alignment(db, organization_id, asset)
        class_history = cls.list_asset_classifications(db, organization_id, asset.id)

        upstream_lineage = (
            db.query(DataLineageEdge)
            .filter(
                DataLineageEdge.organization_id == organization_id,
                DataLineageEdge.target_data_asset_id == asset.id,
            )
            .order_by(DataLineageEdge.id.desc())
            .all()
        )
        downstream_lineage = (
            db.query(DataLineageEdge)
            .filter(
                DataLineageEdge.organization_id == organization_id,
                DataLineageEdge.source_data_asset_id == asset.id,
            )
            .order_by(DataLineageEdge.id.desc())
            .all()
        )

        cloud_links = (
            db.query(DataAssetCloudLink)
            .filter(
                DataAssetCloudLink.organization_id == organization_id,
                DataAssetCloudLink.data_asset_id == asset.id,
            )
            .all()
        )
        processing_links = (
            db.query(DataAssetProcessingLink)
            .filter(
                DataAssetProcessingLink.organization_id == organization_id,
                DataAssetProcessingLink.data_asset_id == asset.id,
            )
            .all()
        )
        control_links = (
            db.query(DataAssetControlLink)
            .filter(
                DataAssetControlLink.organization_id == organization_id,
                DataAssetControlLink.data_asset_id == asset.id,
            )
            .all()
        )
        evidence_links = (
            db.query(DataAssetEvidenceLink)
            .filter(
                DataAssetEvidenceLink.organization_id == organization_id,
                DataAssetEvidenceLink.data_asset_id == asset.id,
            )
            .all()
        )

        control_ids = [cl.organization_control_id for cl in control_links]
        reg_obligations: List[RegulatoryObligationRef] = []
        if control_ids:
            obligations = (
                db.query(RegulatoryObligation)
                .filter(
                    RegulatoryObligation.organization_id == organization_id,
                    RegulatoryObligation.organization_control_id.in_(control_ids),
                )
                .all()
            )
            for ob in obligations:
                reg_obligations.append(
                    RegulatoryObligationRef(
                        obligation_id=ob.id,
                        obligation_code=ob.obligation_code,
                        title=ob.title,
                        mandate_id=ob.mandate_id,
                        organization_control_id=ob.organization_control_id,
                        compliance_status=(
                            ob.compliance_status.value
                            if hasattr(ob.compliance_status, "value")
                            else str(ob.compliance_status)
                        ),
                    )
                )

        return GovernedDataAssetDossierResponse(
            asset=GovernedDataAssetResponse.model_validate(asset),
            owner_active=owner_active,
            steward_active=steward_active,
            cloud_alignment=cloud_alignment,
            classification_history=class_history,
            upstream_lineage=upstream_lineage,
            downstream_lineage=downstream_lineage,
            cloud_links=cloud_links,
            processing_links=processing_links,
            control_links=control_links,
            evidence_links=evidence_links,
            regulatory_obligations=reg_obligations,
        )

    @classmethod
    def get_governance_summary(
        cls,
        db: Session,
        organization_id: int,
    ) -> DataGovernanceSummaryResponse:
        assets = (
            db.query(DataAsset)
            .filter(DataAsset.organization_id == organization_id)
            .all()
        )
        total_assets = len(assets)

        sens_dist = {s.value: 0 for s in DataSensitivityLevel}
        life_dist = {l.value: 0 for l in DataAssetLifecycleEnum}

        active_assets = 0
        discovered_unregistered = 0
        deprecated_assets = 0
        retired_assets = 0
        classified_count = 0
        pending_class_approvals = 0
        unclassified_count = 0
        restricted_or_phi = 0
        steward_assigned = 0
        inactive_owners = 0
        cloud_linked_assets = 0
        cloud_mismatch_assets = 0

        user_ids = {a.owner_id for a in assets if a.owner_id is not None}
        users_map = {
            u.id: u
            for u in db.query(User).filter(User.id.in_(list(user_ids))).all()
        } if user_ids else {}

        for a in assets:
            s_val = a.data_sensitivity_level.value if hasattr(a.data_sensitivity_level, "value") else str(a.data_sensitivity_level)
            sens_dist[s_val] = sens_dist.get(s_val, 0) + 1
            life_dist[a.lifecycle_state] = life_dist.get(a.lifecycle_state, 0) + 1

            if a.lifecycle_state == DataAssetLifecycleEnum.ACTIVE.value:
                active_assets += 1
            elif a.lifecycle_state == DataAssetLifecycleEnum.DISCOVERED.value:
                discovered_unregistered += 1
            elif a.lifecycle_state == DataAssetLifecycleEnum.DEPRECATED.value:
                deprecated_assets += 1
            elif a.lifecycle_state == DataAssetLifecycleEnum.RETIRED.value:
                retired_assets += 1

            if a.classification_status == DataClassificationApprovalStatusEnum.APPROVED.value:
                classified_count += 1
            elif a.classification_status == DataClassificationApprovalStatusEnum.PENDING_APPROVAL.value:
                pending_class_approvals += 1
            else:
                unclassified_count += 1

            if a.data_sensitivity_level in (
                DataSensitivityLevel.RESTRICTED_PII,
                DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI,
            ):
                restricted_or_phi += 1

            if a.steward_id is not None:
                steward_assigned += 1

            owner_obj = users_map.get(a.owner_id)
            if not owner_obj or not getattr(owner_obj, "is_active", True):
                inactive_owners += 1

            alignment = cls.evaluate_asset_cloud_alignment(db, organization_id, a)
            if alignment.linked_cloud_asset_ids:
                cloud_linked_assets += 1
            if not alignment.cloud_posture_aligned:
                cloud_mismatch_assets += 1

        active_lineage_count = (
            db.query(DataLineageEdge)
            .filter(
                DataLineageEdge.organization_id == organization_id,
                DataLineageEdge.status == DataLineageStatusEnum.ACTIVE.value,
            )
            .count()
        )
        pending_lineage_count = (
            db.query(DataLineageEdge)
            .filter(
                DataLineageEdge.organization_id == organization_id,
                DataLineageEdge.status == DataLineageStatusEnum.PENDING_APPROVAL.value,
            )
            .count()
        )

        proc_linked_assets = (
            db.query(DataAssetProcessingLink.data_asset_id)
            .filter(DataAssetProcessingLink.organization_id == organization_id)
            .distinct()
            .count()
        )
        ctrl_linked_assets = (
            db.query(DataAssetControlLink.data_asset_id)
            .filter(DataAssetControlLink.organization_id == organization_id)
            .distinct()
            .count()
        )
        ev_linked_assets = (
            db.query(DataAssetEvidenceLink.data_asset_id)
            .filter(DataAssetEvidenceLink.organization_id == organization_id)
            .distinct()
            .count()
        )

        if total_assets == 0:
            owner_cov = 100.0
            steward_cov = 100.0
            health_score = 100.0
        else:
            valid_owners = max(0, total_assets - inactive_owners)
            owner_cov = round((valid_owners / total_assets) * 100.0, 2)
            steward_cov = round((steward_assigned / total_assets) * 100.0, 2)
            class_cov = (classified_count / total_assets) * 100.0
            cloud_ok_rate = ((total_assets - cloud_mismatch_assets) / total_assets) * 100.0
            health_score = round(
                (0.35 * class_cov)
                + (0.25 * owner_cov)
                + (0.20 * steward_cov)
                + (0.20 * cloud_ok_rate),
                2,
            )

        return DataGovernanceSummaryResponse(
            total_assets=total_assets,
            active_assets=active_assets,
            discovered_unregistered_assets=discovered_unregistered,
            deprecated_assets=deprecated_assets,
            retired_assets=retired_assets,
            classified_assets_count=classified_count,
            pending_classification_approvals=pending_class_approvals,
            unclassified_assets_count=unclassified_count,
            restricted_or_phi_assets_count=restricted_or_phi,
            owner_coverage_pct=owner_cov,
            steward_coverage_pct=steward_cov,
            inactive_owner_count=inactive_owners,
            active_lineage_edges_count=active_lineage_count,
            pending_lineage_approvals_count=pending_lineage_count,
            cloud_linked_assets_count=cloud_linked_assets,
            cloud_posture_mismatch_count=cloud_mismatch_assets,
            processing_linked_assets_count=proc_linked_assets,
            control_linked_assets_count=ctrl_linked_assets,
            evidence_linked_assets_count=ev_linked_assets,
            governance_health_score=health_score,
            sensitivity_distribution=sens_dist,
            lifecycle_distribution=life_dist,
        )
