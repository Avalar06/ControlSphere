from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.supply_chain import (
    ComponentEcosystemEnum,
    ComponentVulnerabilityLink,
    ExemptionApprovalStatusEnum,
    LicenseCategoryEnum,
    LicenseCompliancePolicy,
    ProductCriticalityTierEnum,
    ProductLifecycleStateEnum,
    SBOMDocument,
    SBOMFormatStandardEnum,
    SBOMStatusEnum,
    SoftwareComponent,
    SoftwareProduct,
    SoftwareProductTypeEnum,
    SupplyChainExemption,
    SupplyChainRiskBandEnum,
)
from app.models.resilience import BusinessProcess
from app.models.ai_governance import AISystem
from app.models.tprm import Vendor
from app.models.remediation import RemediationPlan
from app.models.exposure import VulnerabilityExposure
from app.models.user import User
from app.schemas.supply_chain import (
    ComponentCalculatePreviewRequest,
    ComponentCalculatePreviewResponse,
    ComponentVulnerabilityLinkCreate,
    LicenseCompliancePolicyCreate,
    LicenseCompliancePolicyUpdate,
    ProductCalculatePreviewRequest,
    ProductCalculatePreviewResponse,
    SBOMDocumentCreate,
    SoftwareComponentCreate,
    SoftwareComponentUpdate,
    SoftwareProductCreate,
    SoftwareProductStatusUpdate,
    SoftwareProductUpdate,
    SupplyChainExemptionCreate,
    SupplyChainExemptionReviewRequest,
    SupplyChainPostureSummaryResponse,
)
from app.services.audit_service import AuditService


class SupplyChainService:
    # ─── 1. Mathematical & Classification Engine ──────────────────────────────

    LICENSE_RISK_MAP = {
        LicenseCategoryEnum.PERMISSIVE: 0.0,
        LicenseCategoryEnum.WEAK_COPYLEFT: 10.0,
        LicenseCategoryEnum.STRONG_COPYLEFT: 25.0,
        LicenseCategoryEnum.PROHIBITED: 30.0,
        LicenseCategoryEnum.UNCLASSIFIED: 15.0,
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
    def calculate_vulnerability_score(
        cls, cvss_scores: List[float], is_any_exploitable: bool = False
    ) -> float:
        """
        Calculates Component Inherent Vulnerability Score:
        Vscore = min(100.0, max(CVSS * 10 * E) + sum(other_CVSS * 1.5))
        where E = 1.25 if exploitable else 1.0.
        """
        if not cvss_scores:
            return 0.0

        clamped_scores = [max(0.0, min(10.0, float(s))) for s in cvss_scores]
        if not clamped_scores:
            return 0.0

        max_score = max(clamped_scores)
        exploit_mult = 1.25 if is_any_exploitable else 1.0
        primary_impact = max_score * 10.0 * exploit_mult

        other_scores = list(clamped_scores)
        other_scores.remove(max_score)
        secondary_impact = sum(s * 1.5 for s in other_scores)

        return round(min(100.0, primary_impact + secondary_impact), 2)

    @classmethod
    def calculate_depth_penalty(cls, depth: int) -> float:
        """
        Transitive dependency depth penalty multiplier:
        depth = 1 -> 1.00 (Direct)
        depth >= 2 -> 1.00 + min(0.30, 0.10 * (depth - 1))
        """
        if depth <= 1:
            return 1.00
        penalty = min(0.30, 0.10 * (depth - 1))
        return round(1.00 + penalty, 2)

    @classmethod
    def calculate_license_risk_points(cls, category: LicenseCategoryEnum) -> float:
        """Maps license classification to risk penalty points."""
        return cls.LICENSE_RISK_MAP.get(category, 15.0)

    @classmethod
    def calculate_component_risk_index(
        cls,
        vscore: float,
        lrisk: float,
        depth_mult: float,
        is_exempted: bool = False,
    ) -> float:
        """
        Composite Component Risk Index (CRI):
        CRI = min(100.0, (Vscore + Lrisk) * depth_mult * (0.50 if exempted else 1.00))
        """
        exemption_mult = 0.50 if is_exempted else 1.00
        raw_cri = (vscore + lrisk) * depth_mult * exemption_mult
        return round(min(100.0, max(0.0, raw_cri)), 2)

    @classmethod
    def calculate_supply_chain_exposure_index(cls, cri_list: List[float]) -> float:
        """
        Product Supply Chain Exposure Index (SCEI):
        SCEI = min(100.0, max(CRI) * 0.60 + mean(CRI) * 0.40)
        """
        if not cri_list:
            return 0.0

        clamped = [max(0.0, min(100.0, float(c))) for c in cri_list]
        max_cri = max(clamped)
        avg_cri = sum(clamped) / len(clamped)
        scei = (max_cri * 0.60) + (avg_cri * 0.40)
        return round(min(100.0, max(0.0, scei)), 2)

    @classmethod
    def get_risk_band(cls, score: float) -> SupplyChainRiskBandEnum:
        """Maps a 0-100 score to its authoritative Risk Band."""
        if score < 25.0:
            return SupplyChainRiskBandEnum.LOW
        elif score < 50.0:
            return SupplyChainRiskBandEnum.MODERATE
        elif score < 75.0:
            return SupplyChainRiskBandEnum.HIGH
        elif score < 90.0:
            return SupplyChainRiskBandEnum.VERY_HIGH
        else:
            return SupplyChainRiskBandEnum.CRITICAL

    # ─── 2. Cross-Module Foreign Key Validation ───────────────────────────────

    @classmethod
    def validate_cross_module_lineage(
        cls,
        db: Session,
        org_id: int,
        business_process_id: Optional[int] = None,
        ai_system_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        remediation_plan_id: Optional[int] = None,
        vulnerability_id: Optional[int] = None,
    ) -> None:
        """Validates that all cross-module foreign keys exist within the caller's tenant."""
        if business_process_id:
            bp = db.query(BusinessProcess).filter(
                BusinessProcess.id == business_process_id,
                BusinessProcess.organization_id == org_id,
            ).first()
            if not bp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"BusinessProcess #{business_process_id} not found in this organization",
                )

        if ai_system_id:
            ai = db.query(AISystem).filter(
                AISystem.id == ai_system_id,
                AISystem.organization_id == org_id,
            ).first()
            if not ai:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"AISystem #{ai_system_id} not found in this organization",
                )

        if vendor_id:
            v = db.query(Vendor).filter(
                Vendor.id == vendor_id,
                Vendor.organization_id == org_id,
            ).first()
            if not v:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vendor #{vendor_id} not found in this organization",
                )

        if remediation_plan_id:
            rem = db.query(RemediationPlan).filter(
                RemediationPlan.id == remediation_plan_id,
                RemediationPlan.organization_id == org_id,
            ).first()
            if not rem:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"RemediationPlan #{remediation_plan_id} not found in this organization",
                )

        if vulnerability_id:
            vuln = db.query(VulnerabilityExposure).filter(
                VulnerabilityExposure.id == vulnerability_id,
                VulnerabilityExposure.organization_id == org_id,
            ).first()
            if not vuln:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"VulnerabilityExposure #{vulnerability_id} not found in this organization",
                )

    # ─── 3. Software Product CRUD & Lifecycle ─────────────────────────────────

    @classmethod
    def create_product(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        data: SoftwareProductCreate,
    ) -> SoftwareProduct:
        # Check duplicate code
        existing = db.query(SoftwareProduct).filter(
            SoftwareProduct.organization_id == org_id,
            SoftwareProduct.product_code == data.product_code.strip(),
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Software product with code '{data.product_code}' already exists in this organization",
            )

        # Cross-module lineage check
        cls.validate_cross_module_lineage(
            db,
            org_id,
            business_process_id=data.business_process_id,
            ai_system_id=data.ai_system_id,
            vendor_id=data.vendor_id,
        )

        product = SoftwareProduct(
            organization_id=org_id,
            owner_id=user_id,
            product_code=data.product_code.strip().upper(),
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            product_type=data.product_type,
            criticality_tier=data.criticality_tier,
            business_process_id=data.business_process_id,
            ai_system_id=data.ai_system_id,
            vendor_id=data.vendor_id,
            lifecycle_state=ProductLifecycleStateEnum.DRAFT,
            supply_chain_exposure_index=0.0,
            total_components_count=0,
            vulnerable_components_count=0,
            policy_violations_count=0,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        cls._log_audit(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            action="supplychain.product.create",
            resource_type="software_product",
            resource_id=product.id,
            details={"product_code": product.product_code, "name": product.name},
        )
        return product

    @classmethod
    def get_product(cls, db: Session, org_id: int, product_id: int) -> SoftwareProduct:
        product = db.query(SoftwareProduct).filter(
            SoftwareProduct.id == product_id,
            SoftwareProduct.organization_id == org_id,
        ).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Software product #{product_id} not found in this organization",
            )
        return product

    @classmethod
    def list_products(
        cls,
        db: Session,
        org_id: int,
        lifecycle_state: Optional[ProductLifecycleStateEnum] = None,
        criticality_tier: Optional[ProductCriticalityTierEnum] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SoftwareProduct]:
        query = db.query(SoftwareProduct).filter(SoftwareProduct.organization_id == org_id)
        if lifecycle_state:
            query = query.filter(SoftwareProduct.lifecycle_state == lifecycle_state)
        if criticality_tier:
            query = query.filter(SoftwareProduct.criticality_tier == criticality_tier)
        return query.order_by(SoftwareProduct.created_at.desc()).offset(skip).limit(limit).all()

    @classmethod
    def update_product(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        product_id: int,
        data: SoftwareProductUpdate,
    ) -> SoftwareProduct:
        product = cls.get_product(db, org_id, product_id)

        # Immutability Lock for RETIRED products
        if product.lifecycle_state == ProductLifecycleStateEnum.RETIRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update product in RETIRED state (Governance Immutability Lock)",
            )

        cls.validate_cross_module_lineage(
            db,
            org_id,
            business_process_id=data.business_process_id,
            ai_system_id=data.ai_system_id,
            vendor_id=data.vendor_id,
        )

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(product, key, value)

        product.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(product)

        cls._log_audit(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            action="supplychain.product.update",
            resource_type="software_product",
            resource_id=product.id,
            details=update_dict,
        )
        return product

    @classmethod
    def update_product_status(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        product_id: int,
        status_data: SoftwareProductStatusUpdate,
    ) -> SoftwareProduct:
        product = cls.get_product(db, org_id, product_id)
        current = product.lifecycle_state
        target = status_data.lifecycle_state

        if current == ProductLifecycleStateEnum.RETIRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product is RETIRED and permanently immutable; cannot change state",
            )

        # Governed State Machine Rules
        valid_transitions = {
            ProductLifecycleStateEnum.DRAFT: [ProductLifecycleStateEnum.ACTIVE, ProductLifecycleStateEnum.DEPRECATED],
            ProductLifecycleStateEnum.ACTIVE: [ProductLifecycleStateEnum.DEPRECATED, ProductLifecycleStateEnum.RETIRED],
            ProductLifecycleStateEnum.DEPRECATED: [ProductLifecycleStateEnum.ACTIVE, ProductLifecycleStateEnum.RETIRED],
            ProductLifecycleStateEnum.RETIRED: [],
        }

        if target not in valid_transitions.get(current, []):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Illegal lifecycle transition from {current} to {target}",
            )

        product.lifecycle_state = target
        product.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(product)

        cls._log_audit(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            action="supplychain.product.status_change",
            resource_type="software_product",
            resource_id=product.id,
            details={"from_state": current, "to_state": target, "notes": status_data.notes},
        )
        return product

    @classmethod
    def delete_product(cls, db: Session, org_id: int, user_id: int, product_id: int) -> None:
        product = cls.get_product(db, org_id, product_id)
        if product.lifecycle_state == ProductLifecycleStateEnum.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete an ACTIVE product. Transition to DEPRECATED or RETIRED first.",
            )

        db.delete(product)
        db.commit()

        cls._log_audit(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            action="supplychain.product.delete",
            resource_type="software_product",
            resource_id=product_id,
            details={"product_code": product.product_code},
        )

    # ─── 4. SBOM Ingestion & Management ───────────────────────────────────────

    @classmethod
    def ingest_sbom(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        product_id: int,
        data: SBOMDocumentCreate,
    ) -> SBOMDocument:
        product = cls.get_product(db, org_id, product_id)
        if product.lifecycle_state == ProductLifecycleStateEnum.RETIRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot ingest SBOM for a RETIRED product",
            )

        # Validate SHA-256 length and hex
        digest = data.sha256_hash.strip().lower()
        if len(digest) != 64 or not all(c in "0123456789abcdef" for c in digest):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="sha256_hash must be a valid 64-character hexadecimal digest",
            )

        # Check duplicate SBOM code
        existing = db.query(SBOMDocument).filter(
            SBOMDocument.organization_id == org_id,
            SBOMDocument.sbom_code == data.sbom_code.strip(),
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SBOM with code '{data.sbom_code}' already exists in this organization",
            )

        # Supersede existing ACTIVE SBOMs for this product
        db.query(SBOMDocument).filter(
            SBOMDocument.organization_id == org_id,
            SBOMDocument.software_product_id == product_id,
            SBOMDocument.status == SBOMStatusEnum.ACTIVE,
        ).update({"status": SBOMStatusEnum.SUPERSEDED, "updated_at": datetime.now(timezone.utc)})

        sbom = SBOMDocument(
            organization_id=org_id,
            software_product_id=product_id,
            created_by_id=user_id,
            sbom_code=data.sbom_code.strip().upper(),
            version=data.version.strip(),
            format_standard=data.format_standard,
            spec_version=data.spec_version.strip(),
            sha256_hash=digest,
            author_name=data.author_name.strip() if data.author_name else None,
            tool_name=data.tool_name.strip() if data.tool_name else None,
            status=SBOMStatusEnum.ACTIVE,
            component_count=0,
        )
        db.add(sbom)
        db.commit()
        db.refresh(sbom)

        cls._log_audit(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            action="supplychain.sbom.ingest",
            resource_type="sbom_document",
            resource_id=sbom.id,
            details={"sbom_code": sbom.sbom_code, "sha256_hash": sbom.sha256_hash},
        )
        return sbom

    @classmethod
    def get_sbom(cls, db: Session, org_id: int, sbom_id: int) -> SBOMDocument:
        sbom = db.query(SBOMDocument).filter(
            SBOMDocument.id == sbom_id,
            SBOMDocument.organization_id == org_id,
        ).first()
        if not sbom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SBOM #{sbom_id} not found in this organization",
            )
        return sbom

    @classmethod
    def list_sboms(
        cls, db: Session, org_id: int, product_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> List[SBOMDocument]:
        query = db.query(SBOMDocument).filter(SBOMDocument.organization_id == org_id)
        if product_id:
            query = query.filter(SBOMDocument.software_product_id == product_id)
        return query.order_by(SBOMDocument.created_at.desc()).offset(skip).limit(limit).all()

    # ─── 5. Component & Vulnerability Linking ─────────────────────────────────

    @classmethod
    def add_component_to_sbom(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        sbom_id: int,
        data: SoftwareComponentCreate,
    ) -> SoftwareComponent:
        sbom = cls.get_sbom(db, org_id, sbom_id)

        # Check license policy for prohibited status
        policy = db.query(LicenseCompliancePolicy).filter(
            LicenseCompliancePolicy.organization_id == org_id,
            LicenseCompliancePolicy.license_identifier == data.declared_license.strip(),
        ).first()
        is_prohibited = policy.is_prohibited if policy else (data.license_category == LicenseCategoryEnum.PROHIBITED)

        # Initial metrics calculation
        lrisk = cls.calculate_license_risk_points(data.license_category)
        depth_mult = cls.calculate_depth_penalty(data.dependency_depth)
        cri = cls.calculate_component_risk_index(0.0, lrisk, depth_mult, False)

        component = SoftwareComponent(
            organization_id=org_id,
            sbom_document_id=sbom_id,
            component_name=data.component_name.strip(),
            version=data.version.strip(),
            purl=data.purl.strip(),
            ecosystem=data.ecosystem,
            dependency_depth=max(1, data.dependency_depth),
            supplier_name=data.supplier_name.strip() if data.supplier_name else None,
            declared_license=data.declared_license.strip(),
            license_category=data.license_category,
            is_license_prohibited=is_prohibited,
            component_risk_index=cri,
            max_vulnerability_score=0.0,
            vulnerabilities_count=0,
            is_exempted=False,
        )
        db.add(component)
        sbom.component_count += 1
        db.commit()
        db.refresh(component)

        # Recalculate product exposure index
        cls.recalculate_product_metrics(db, sbom.software_product_id)

        cls._log_audit(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            action="supplychain.component.create",
            resource_type="software_component",
            resource_id=component.id,
            details={"component_name": component.component_name, "purl": component.purl},
        )
        return component

    @classmethod
    def get_component(cls, db: Session, org_id: int, component_id: int) -> SoftwareComponent:
        comp = db.query(SoftwareComponent).filter(
            SoftwareComponent.id == component_id,
            SoftwareComponent.organization_id == org_id,
        ).first()
        if not comp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Software component #{component_id} not found in this organization",
            )
        return comp

    @classmethod
    def list_components(
        cls, db: Session, org_id: int, sbom_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> List[SoftwareComponent]:
        query = db.query(SoftwareComponent).filter(SoftwareComponent.organization_id == org_id)
        if sbom_id:
            query = query.filter(SoftwareComponent.sbom_document_id == sbom_id)
        return query.order_by(SoftwareComponent.component_risk_index.desc()).offset(skip).limit(limit).all()

    @classmethod
    def add_vulnerability_link(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        component_id: int,
        data: ComponentVulnerabilityLinkCreate,
    ) -> ComponentVulnerabilityLink:
        comp = cls.get_component(db, org_id, component_id)

        cls.validate_cross_module_lineage(
            db,
            org_id,
            vulnerability_id=data.vulnerability_id,
            remediation_plan_id=data.remediation_plan_id,
        )

        link = ComponentVulnerabilityLink(
            organization_id=org_id,
            component_id=component_id,
            vulnerability_id=data.vulnerability_id,
            cve_identifier=data.cve_identifier.strip().upper(),
            severity_score=max(0.0, min(10.0, data.severity_score)),
            is_exploitable=data.is_exploitable,
            is_reachable=data.is_reachable,
            fix_version=data.fix_version.strip() if data.fix_version else None,
            remediation_plan_id=data.remediation_plan_id,
        )
        db.add(link)
        db.commit()
        db.refresh(link)

        # Recalculate component and product risk
        cls.recalculate_component_metrics(db, component_id)
        return link

    @classmethod
    def recalculate_component_metrics(cls, db: Session, component_id: int) -> SoftwareComponent:
        comp = db.query(SoftwareComponent).filter(SoftwareComponent.id == component_id).first()
        if not comp:
            return None

        links = db.query(ComponentVulnerabilityLink).filter(
            ComponentVulnerabilityLink.component_id == component_id
        ).all()

        scores = [float(l.severity_score) for l in links]
        is_any_exploitable = any(l.is_exploitable for l in links)
        vscore = cls.calculate_vulnerability_score(scores, is_any_exploitable)
        lrisk = cls.calculate_license_risk_points(comp.license_category)
        depth_mult = cls.calculate_depth_penalty(comp.dependency_depth)

        cri = cls.calculate_component_risk_index(vscore, lrisk, depth_mult, comp.is_exempted)

        comp.vulnerabilities_count = len(links)
        comp.max_vulnerability_score = max(scores) if scores else 0.0
        comp.component_risk_index = cri
        comp.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(comp)

        # Propagate up to product
        if comp.sbom_document and comp.sbom_document.software_product_id:
            cls.recalculate_product_metrics(db, comp.sbom_document.software_product_id)

        return comp

    @classmethod
    def recalculate_product_metrics(cls, db: Session, product_id: int) -> SoftwareProduct:
        product = db.query(SoftwareProduct).filter(SoftwareProduct.id == product_id).first()
        if not product:
            return None

        # Gather components from the latest ACTIVE SBOM
        active_sbom = db.query(SBOMDocument).filter(
            SBOMDocument.software_product_id == product_id,
            SBOMDocument.status == SBOMStatusEnum.ACTIVE,
        ).first()

        if not active_sbom:
            product.supply_chain_exposure_index = 0.0
            product.total_components_count = 0
            product.vulnerable_components_count = 0
            product.policy_violations_count = 0
            db.commit()
            return product

        components = db.query(SoftwareComponent).filter(
            SoftwareComponent.sbom_document_id == active_sbom.id
        ).all()

        cri_list = [float(c.component_risk_index) for c in components]
        scei = cls.calculate_supply_chain_exposure_index(cri_list)

        product.supply_chain_exposure_index = scei
        product.total_components_count = len(components)
        product.vulnerable_components_count = sum(1 for c in components if c.vulnerabilities_count > 0)
        product.policy_violations_count = sum(1 for c in components if c.is_license_prohibited)
        product.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(product)
        return product

    # ─── 6. License Policies CRUD ─────────────────────────────────────────────

    @classmethod
    def create_license_policy(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        data: LicenseCompliancePolicyCreate,
    ) -> LicenseCompliancePolicy:
        existing = db.query(LicenseCompliancePolicy).filter(
            LicenseCompliancePolicy.organization_id == org_id,
            LicenseCompliancePolicy.license_identifier == data.license_identifier.strip(),
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"License policy for '{data.license_identifier}' already exists in this organization",
            )

        policy = LicenseCompliancePolicy(
            organization_id=org_id,
            license_identifier=data.license_identifier.strip(),
            name=data.name.strip(),
            category=data.category,
            is_prohibited=data.is_prohibited,
            risk_penalty_points=max(0.0, min(30.0, data.risk_penalty_points)),
            description=data.description.strip() if data.description else None,
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
        return policy

    @classmethod
    def list_license_policies(cls, db: Session, org_id: int) -> List[LicenseCompliancePolicy]:
        return db.query(LicenseCompliancePolicy).filter(
            LicenseCompliancePolicy.organization_id == org_id
        ).order_by(LicenseCompliancePolicy.license_identifier.asc()).all()

    # ─── 7. Four-Eyes Exemption Governance ────────────────────────────────────

    @classmethod
    def request_exemption(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        data: SupplyChainExemptionCreate,
    ) -> SupplyChainExemption:
        cls.get_product(db, org_id, data.software_product_id)
        comp = cls.get_component(db, org_id, data.component_id)

        # Check duplicate exemption code
        existing = db.query(SupplyChainExemption).filter(
            SupplyChainExemption.organization_id == org_id,
            SupplyChainExemption.exemption_code == data.exemption_code.strip(),
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Exemption with code '{data.exemption_code}' already exists in this organization",
            )

        exemption = SupplyChainExemption(
            organization_id=org_id,
            requested_by_id=user_id,
            exemption_code=data.exemption_code.strip().upper(),
            software_product_id=data.software_product_id,
            component_id=data.component_id,
            reason=data.reason.strip(),
            compensating_controls=data.compensating_controls.strip(),
            valid_until=data.valid_until,
            approval_status=ExemptionApprovalStatusEnum.PENDING,
        )
        db.add(exemption)
        db.commit()
        db.refresh(exemption)

        cls._log_audit(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            action="supplychain.exemption.request",
            resource_type="supply_chain_exemption",
            resource_id=exemption.id,
            details={"exemption_code": exemption.exemption_code, "component_id": exemption.component_id},
        )
        return exemption

    @classmethod
    def get_exemption(cls, db: Session, org_id: int, exemption_id: int) -> SupplyChainExemption:
        exemption = db.query(SupplyChainExemption).filter(
            SupplyChainExemption.id == exemption_id,
            SupplyChainExemption.organization_id == org_id,
        ).first()
        if not exemption:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Supply chain exemption #{exemption_id} not found in this organization",
            )
        return exemption

    @classmethod
    def list_exemptions(
        cls,
        db: Session,
        org_id: int,
        product_id: Optional[int] = None,
        status_filter: Optional[ExemptionApprovalStatusEnum] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SupplyChainExemption]:
        query = db.query(SupplyChainExemption).filter(SupplyChainExemption.organization_id == org_id)
        if product_id:
            query = query.filter(SupplyChainExemption.software_product_id == product_id)
        if status_filter:
            query = query.filter(SupplyChainExemption.approval_status == status_filter)
        return query.order_by(SupplyChainExemption.created_at.desc()).offset(skip).limit(limit).all()

    @classmethod
    def review_exemption(
        cls,
        db: Session,
        org_id: int,
        user_id: int,
        exemption_id: int,
        data: SupplyChainExemptionReviewRequest,
    ) -> SupplyChainExemption:
        exemption = cls.get_exemption(db, org_id, exemption_id)

        # Finalized Replay Lockout
        if exemption.approval_status in (ExemptionApprovalStatusEnum.APPROVED, ExemptionApprovalStatusEnum.REJECTED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Exemption #{exemption_id} has already reached finalized status ({exemption.approval_status})",
            )

        # Four-Eyes Principle: Creator cannot self-approve
        if exemption.requested_by_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Segregation of Duties Violation: You cannot review or approve an exemption you requested",
            )

        exemption.approval_status = data.decision
        exemption.reviewer_notes = data.reviewer_notes.strip()
        exemption.reviewed_by_id = user_id
        exemption.reviewed_at = datetime.now(timezone.utc)
        exemption.updated_at = datetime.now(timezone.utc)

        # If approved, flag component as exempted and recalculate
        if data.decision == ExemptionApprovalStatusEnum.APPROVED:
            comp = db.query(SoftwareComponent).filter(SoftwareComponent.id == exemption.component_id).first()
            if comp:
                comp.is_exempted = True

        db.commit()
        db.refresh(exemption)

        # Recalculate component risk with exemption factor
        cls.recalculate_component_metrics(db, exemption.component_id)

        cls._log_audit(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            action="supplychain.exemption.review",
            resource_type="supply_chain_exemption",
            resource_id=exemption.id,
            details={"decision": data.decision, "reviewer_notes": data.reviewer_notes},
        )
        return exemption

    # ─── 8. Executive Posture Telemetry ───────────────────────────────────────

    @classmethod
    def get_posture_summary(cls, db: Session, org_id: int) -> SupplyChainPostureSummaryResponse:
        products = db.query(SoftwareProduct).filter(SoftwareProduct.organization_id == org_id).all()
        components = db.query(SoftwareComponent).filter(SoftwareComponent.organization_id == org_id).all()
        sboms = db.query(SBOMDocument).filter(SBOMDocument.organization_id == org_id).all()
        exemptions = db.query(SupplyChainExemption).filter(SupplyChainExemption.organization_id == org_id).all()

        total_products = len(products)
        active_products = sum(1 for p in products if p.lifecycle_state == ProductLifecycleStateEnum.ACTIVE)
        total_components = len(components)
        vulnerable_comps = sum(1 for c in components if c.vulnerabilities_count > 0)
        critical_comps = sum(1 for c in components if float(c.component_risk_index) >= 75.0)
        prohibited_violations = sum(1 for c in components if c.is_license_prohibited)
        pending_exemptions = sum(1 for e in exemptions if e.approval_status == ExemptionApprovalStatusEnum.PENDING)

        avg_scei = (
            sum(float(p.supply_chain_exposure_index) for p in products) / total_products
            if total_products > 0
            else 0.0
        )

        crit_dist = {}
        for p in products:
            tier = p.criticality_tier.value
            crit_dist[tier] = crit_dist.get(tier, 0) + 1

        lic_dist = {}
        for c in components:
            cat = c.license_category.value
            lic_dist[cat] = lic_dist.get(cat, 0) + 1

        risk_dist = {}
        for c in components:
            band = cls.get_risk_band(float(c.component_risk_index)).value
            risk_dist[band] = risk_dist.get(band, 0) + 1

        return SupplyChainPostureSummaryResponse(
            total_software_products=total_products,
            active_products_count=active_products,
            total_sboms_indexed=len(sboms),
            total_components_cataloged=total_components,
            vulnerable_components_count=vulnerable_comps,
            critical_risk_components_count=critical_comps,
            prohibited_license_violations_count=prohibited_violations,
            pending_exemptions_count=pending_exemptions,
            average_supply_chain_exposure_index=round(avg_scei, 2),
            criticality_distribution=crit_dist,
            license_category_distribution=lic_dist,
            risk_band_distribution=risk_dist,
        )

    # ─── 9. Live Calculation Previews ─────────────────────────────────────────

    @classmethod
    def calculate_component_preview(
        cls, payload: ComponentCalculatePreviewRequest
    ) -> ComponentCalculatePreviewResponse:
        vscore = cls.calculate_vulnerability_score(
            payload.cvss_scores, payload.is_any_exploitable
        )
        depth_mult = cls.calculate_depth_penalty(payload.dependency_depth)
        lrisk = cls.calculate_license_risk_points(payload.license_category)
        cri = cls.calculate_component_risk_index(
            vscore, lrisk, depth_mult, payload.is_exempted
        )
        risk_band = cls.get_risk_band(cri)
        return ComponentCalculatePreviewResponse(
            vulnerability_score=vscore,
            depth_penalty_multiplier=depth_mult,
            license_risk_points=lrisk,
            component_risk_index=cri,
            risk_band=risk_band,
        )

    @classmethod
    def calculate_product_preview(
        cls, payload: ProductCalculatePreviewRequest
    ) -> ProductCalculatePreviewResponse:
        cri_list = payload.component_risk_indices
        scei = cls.calculate_supply_chain_exposure_index(cri_list)
        max_cri = max(cri_list) if cri_list else 0.0
        avg_cri = (sum(cri_list) / len(cri_list)) if cri_list else 0.0
        critical_count = sum(1 for c in cri_list if c >= 75.0)
        risk_band = cls.get_risk_band(scei)
        return ProductCalculatePreviewResponse(
            supply_chain_exposure_index=scei,
            max_component_risk=round(max_cri, 2),
            average_component_risk=round(avg_cri, 2),
            critical_components_count=critical_count,
            risk_band=risk_band,
        )
