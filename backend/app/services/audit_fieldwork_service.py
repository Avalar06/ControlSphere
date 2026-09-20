import hashlib
import json
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.audit_engagement import (
    Audit,
    AuditFindingLink,
    AuditProcedure,
    AuditProcedureEvidence,
    AuditScopeControl,
    ProcedureResultEnum,
    AuditPBCRequest,
    AuditSamplePopulation,
    AuditSampleItem,
    AuditWorkpaperReview,
    PBCStatusEnum,
    PBCPriorityEnum,
    SamplingMethodEnum,
    SampleResultEnum,
    WorkpaperStatusEnum,
)
from app.models.control import OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceReview, EvidenceStatusEnum, ReviewDecisionEnum
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum, FindingTypeEnum
from app.models.user import User
from app.schemas.audit_fieldwork import (
    AuditPBCRequestCreate,
    AuditPBCRequestUpdate,
    AuditPBCRequestFulfill,
    AuditPBCRequestReview,
    AuditSamplePopulationCreate,
    AuditSampleGenerateRequest,
    AuditSampleItemUpdate,
    AuditSampleEscalateFinding,
    AuditWorkpaperSubmit,
    AuditWorkpaperApprove,
    AuditWorkpaperRequestChanges,
)
from app.services.audit_sampling_service import AuditSamplingService
from app.services.audit_service import AuditService
from app.services.finding_service import FindingService


class AuditFieldworkService:
    """
    Authoritative Domain Service for Audit Fieldwork Governance (Batch 1):
    - PBC (Provided By Client) Request Management
    - Statistical, Systematic, and Stratified Audit Sampling (AU-C 530 / PCAOB AS 2315)
    - Workpaper Four-Eyes Signoff & Tamper-Evident SHA-256 Digest
    - Sample Exception -> Finding Escalation Bridge
    """

    @staticmethod
    def _log_action(
        db: Session,
        organization_id: int,
        user_id: Optional[int],
        action: str,
        entity_type: str,
        entity_id: Any,
        new_values: Optional[Dict[str, Any]] = None,
    ) -> None:
        user = db.query(User).filter(User.id == user_id).first() if user_id else None
        actor_email = user.email if user else "system@control-sphere.internal"
        AuditService.log(
            db=db,
            organization_id=organization_id,
            action=action,
            resource_type=entity_type,
            actor_email=actor_email,
            actor_id=user_id,
            resource_id=str(entity_id) if entity_id is not None else None,
            details=new_values or {},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # PBC REQUESTS
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def create_pbc_request(
        db: Session,
        organization_id: int,
        audit_id: int,
        obj_in: AuditPBCRequestCreate,
        creator_id: Optional[int],
    ) -> AuditPBCRequest:
        # Validate audit belongs to organization
        audit = db.query(Audit).filter(
            Audit.id == audit_id,
            Audit.organization_id == organization_id
        ).first()
        if not audit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit engagement not found.")

        # Validate control belongs to organization
        control = db.query(OrganizationControl).filter(
            OrganizationControl.id == obj_in.organization_control_id,
            OrganizationControl.organization_id == organization_id
        ).first()
        if not control:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization control not found.")

        # Validate procedure if specified
        if obj_in.procedure_id:
            proc = db.query(AuditProcedure).filter(
                AuditProcedure.id == obj_in.procedure_id,
                AuditProcedure.audit_id == audit_id,
                AuditProcedure.organization_id == organization_id
            ).first()
            if not proc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit procedure not found.")

        # Validate assigned user if specified
        if obj_in.assigned_to_id:
            assigned_user = db.query(User).filter(
                User.id == obj_in.assigned_to_id,
                User.organization_id == organization_id,
                User.is_active == True
            ).first()
            if not assigned_user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user is invalid or inactive.")

        # Auto-generate request identifier if omitted
        identifier = obj_in.request_identifier
        if not identifier:
            count = db.query(AuditPBCRequest).filter(
                AuditPBCRequest.organization_id == organization_id,
                AuditPBCRequest.audit_id == audit_id
            ).count() + 1
            identifier = f"PBC-{audit_id}-{count:03d}"

        # Ensure uniqueness within organization
        existing = db.query(AuditPBCRequest).filter(
            AuditPBCRequest.organization_id == organization_id,
            AuditPBCRequest.request_identifier == identifier
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"PBC request identifier '{identifier}' already exists in this organization."
            )

        pbc = AuditPBCRequest(
            organization_id=organization_id,
            audit_id=audit_id,
            procedure_id=obj_in.procedure_id,
            organization_control_id=obj_in.organization_control_id,
            request_identifier=identifier,
            title=obj_in.title.strip(),
            description=obj_in.description.strip(),
            status=PBCStatusEnum.REQUESTED,
            priority=obj_in.priority,
            assigned_to_id=obj_in.assigned_to_id,
            due_date=obj_in.due_date,
            created_by_id=creator_id,
        )
        db.add(pbc)
        db.commit()
        db.refresh(pbc)

        AuditFieldworkService._log_action(
            db=db,
            organization_id=organization_id,
            user_id=creator_id,
            action="AUDIT_PBC_CREATED",
            entity_type="AuditPBCRequest",
            entity_id=pbc.id,
            new_values={
                "request_identifier": pbc.request_identifier,
                "title": pbc.title,
                "audit_id": audit_id,
                "organization_control_id": obj_in.organization_control_id,
                "due_date": obj_in.due_date.isoformat(),
            }
        )
        return pbc

    @staticmethod
    def list_pbc_requests(
        db: Session,
        organization_id: int,
        audit_id: int,
        procedure_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
        status_filter: Optional[PBCStatusEnum] = None,
    ) -> List[AuditPBCRequest]:
        query = db.query(AuditPBCRequest).filter(
            AuditPBCRequest.organization_id == organization_id,
            AuditPBCRequest.audit_id == audit_id
        ).options(
            joinedload(AuditPBCRequest.assigned_to),
            joinedload(AuditPBCRequest.reviewed_by),
            joinedload(AuditPBCRequest.organization_control),
            joinedload(AuditPBCRequest.fulfilled_evidence),
        )
        if procedure_id:
            query = query.filter(AuditPBCRequest.procedure_id == procedure_id)
        if assigned_to_id:
            query = query.filter(AuditPBCRequest.assigned_to_id == assigned_to_id)
        if status_filter:
            query = query.filter(AuditPBCRequest.status == status_filter)

        return query.order_by(AuditPBCRequest.created_at.desc()).all()

    @staticmethod
    def get_pbc_request(
        db: Session,
        organization_id: int,
        audit_id: int,
        pbc_id: int,
    ) -> AuditPBCRequest:
        pbc = db.query(AuditPBCRequest).filter(
            AuditPBCRequest.id == pbc_id,
            AuditPBCRequest.audit_id == audit_id,
            AuditPBCRequest.organization_id == organization_id
        ).options(
            joinedload(AuditPBCRequest.assigned_to),
            joinedload(AuditPBCRequest.reviewed_by),
            joinedload(AuditPBCRequest.organization_control),
            joinedload(AuditPBCRequest.fulfilled_evidence),
        ).first()
        if not pbc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PBC request not found.")
        return pbc

    @staticmethod
    def update_pbc_request(
        db: Session,
        organization_id: int,
        audit_id: int,
        pbc_id: int,
        obj_in: AuditPBCRequestUpdate,
    ) -> AuditPBCRequest:
        pbc = AuditFieldworkService.get_pbc_request(db, organization_id, audit_id, pbc_id)
        if pbc.status == PBCStatusEnum.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify a PBC request that has already been accepted."
            )

        if obj_in.title is not None:
            pbc.title = obj_in.title.strip()
        if obj_in.description is not None:
            pbc.description = obj_in.description.strip()
        if obj_in.assigned_to_id is not None:
            user = db.query(User).filter(
                User.id == obj_in.assigned_to_id,
                User.organization_id == organization_id,
                User.is_active == True
            ).first()
            if not user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned user is invalid or inactive.")
            pbc.assigned_to_id = obj_in.assigned_to_id
        if obj_in.priority is not None:
            pbc.priority = obj_in.priority
        if obj_in.due_date is not None:
            pbc.due_date = obj_in.due_date

        db.commit()
        db.refresh(pbc)
        return pbc

    @staticmethod
    def fulfill_pbc_request(
        db: Session,
        organization_id: int,
        audit_id: int,
        pbc_id: int,
        user_id: int,
        obj_in: AuditPBCRequestFulfill,
    ) -> AuditPBCRequest:
        # Acquire row-level lock for concurrency safety
        pbc = db.query(AuditPBCRequest).filter(
            AuditPBCRequest.id == pbc_id,
            AuditPBCRequest.audit_id == audit_id,
            AuditPBCRequest.organization_id == organization_id
        ).with_for_update().first()
        if not pbc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PBC request not found.")

        if pbc.status not in (PBCStatusEnum.REQUESTED, PBCStatusEnum.REJECTED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot fulfill PBC request in status '{pbc.status.value}'. Must be REQUESTED or REJECTED."
            )

        if not obj_in.evidence_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Must provide an evidence_id from the authoritative Evidence engine."
            )

        # Validate authoritative EvidenceItem
        evidence = db.query(EvidenceItem).filter(
            EvidenceItem.id == obj_in.evidence_id,
            EvidenceItem.organization_id == organization_id
        ).first()
        if not evidence:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authoritative evidence item not found.")

        pbc.fulfilled_evidence_id = evidence.id
        pbc.submission_notes = obj_in.submission_notes
        pbc.submitted_at = datetime.now(timezone.utc)
        pbc.status = PBCStatusEnum.SUBMITTED
        pbc.rejection_reason = None  # Clear prior rejection feedback upon resubmission

        # Auto-link to procedure evidence junction if procedure is defined
        if pbc.procedure_id:
            existing_link = db.query(AuditProcedureEvidence).filter(
                AuditProcedureEvidence.procedure_id == pbc.procedure_id,
                AuditProcedureEvidence.evidence_id == evidence.id
            ).first()
            if not existing_link:
                link = AuditProcedureEvidence(
                    organization_id=organization_id,
                    procedure_id=pbc.procedure_id,
                    evidence_id=evidence.id,
                    link_notes=f"Attached via PBC request {pbc.request_identifier}",
                    created_by_id=user_id
                )
                db.add(link)

        db.commit()
        db.refresh(pbc)

        AuditFieldworkService._log_action(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="AUDIT_PBC_SUBMITTED",
            entity_type="AuditPBCRequest",
            entity_id=pbc.id,
            new_values={
                "fulfilled_evidence_id": evidence.id,
                "status": "SUBMITTED",
                "submitted_at": pbc.submitted_at.isoformat(),
            }
        )
        return pbc

    @staticmethod
    def review_pbc_request(
        db: Session,
        organization_id: int,
        audit_id: int,
        pbc_id: int,
        reviewer_id: int,
        obj_in: AuditPBCRequestReview,
    ) -> AuditPBCRequest:
        pbc = db.query(AuditPBCRequest).filter(
            AuditPBCRequest.id == pbc_id,
            AuditPBCRequest.audit_id == audit_id,
            AuditPBCRequest.organization_id == organization_id
        ).with_for_update().first()
        if not pbc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PBC request not found.")

        if pbc.status != PBCStatusEnum.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot review PBC request in status '{pbc.status.value}'. Must be in SUBMITTED state."
            )

        # STRICT FOUR-EYES: Assigned auditee cannot accept their own submission
        if pbc.assigned_to_id == reviewer_id and obj_in.decision.upper() == "ACCEPT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Four-Eyes Governance Violation: The auditee assigned to this request cannot approve/accept their own submission."
            )

        decision = obj_in.decision.upper()
        now = datetime.now(timezone.utc)

        if decision == "ACCEPT":
            pbc.status = PBCStatusEnum.ACCEPTED
            pbc.reviewed_by_id = reviewer_id
            pbc.reviewed_at = now
            pbc.rejection_reason = None

            # Create an authoritative EvidenceReview record
            if pbc.fulfilled_evidence_id:
                ev_review = EvidenceReview(
                    organization_id=organization_id,
                    evidence_id=pbc.fulfilled_evidence_id,
                    reviewer_id=reviewer_id,
                    decision=ReviewDecisionEnum.ACCEPT,
                    review_notes=obj_in.review_notes or f"Accepted via PBC request {pbc.request_identifier}",
                    reviewed_at=now
                )
                db.add(ev_review)

            action = "AUDIT_PBC_ACCEPTED"

        elif decision == "REJECT":
            if not obj_in.rejection_reason or len(obj_in.rejection_reason.strip()) < 5:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="A detailed rejection_reason is required when rejecting a PBC submission."
                )
            pbc.status = PBCStatusEnum.REJECTED
            pbc.reviewed_by_id = reviewer_id
            pbc.reviewed_at = now
            pbc.rejection_reason = obj_in.rejection_reason.strip()

            if pbc.fulfilled_evidence_id:
                ev_review = EvidenceReview(
                    organization_id=organization_id,
                    evidence_id=pbc.fulfilled_evidence_id,
                    reviewer_id=reviewer_id,
                    decision=ReviewDecisionEnum.REJECT,
                    review_notes=obj_in.review_notes,
                    rejection_reason=pbc.rejection_reason,
                    reviewed_at=now
                )
                db.add(ev_review)

            action = "AUDIT_PBC_REJECTED"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid decision. Must be 'ACCEPT' or 'REJECT'."
            )

        db.commit()
        db.refresh(pbc)

        AuditFieldworkService._log_action(
            db=db,
            organization_id=organization_id,
            user_id=reviewer_id,
            action=action,
            entity_type="AuditPBCRequest",
            entity_id=pbc.id,
            new_values={
                "status": pbc.status.value,
                "reviewed_by_id": reviewer_id,
                "reviewed_at": now.isoformat(),
                "rejection_reason": pbc.rejection_reason,
            }
        )
        return pbc

    # ─────────────────────────────────────────────────────────────────────────
    # SAMPLING POPULATION & DETERMINISTIC EXTRACTION
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def create_population(
        db: Session,
        organization_id: int,
        audit_id: int,
        procedure_id: int,
        obj_in: AuditSamplePopulationCreate,
        creator_id: Optional[int],
    ) -> AuditSamplePopulation:
        # Validate procedure
        proc = db.query(AuditProcedure).filter(
            AuditProcedure.id == procedure_id,
            AuditProcedure.audit_id == audit_id,
            AuditProcedure.organization_id == organization_id
        ).first()
        if not proc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit procedure not found.")

        # Compute next version number for this procedure
        highest_v = db.query(AuditSamplePopulation).filter(
            AuditSamplePopulation.procedure_id == procedure_id
        ).order_by(AuditSamplePopulation.version_number.desc()).first()
        next_v = (highest_v.version_number + 1) if highest_v else 1

        # Format items canonically
        raw_items = [
            {"source_record_id": it.source_record_id, "attributes": it.attributes}
            for it in obj_in.items
        ]
        canonical_items = AuditSamplingService.canonical_sort_population(raw_items)
        digest = AuditSamplingService.compute_population_digest(canonical_items)

        pop = AuditSamplePopulation(
            organization_id=organization_id,
            audit_id=audit_id,
            procedure_id=procedure_id,
            population_name=obj_in.population_name.strip(),
            description=obj_in.description.strip() if obj_in.description else None,
            population_source=obj_in.population_source.strip(),
            total_count=len(canonical_items),
            version_number=next_v,
            is_frozen=False,
            population_digest_sha256=digest,
            population_data_json=json.dumps(canonical_items),
            sampling_method=SamplingMethodEnum.RANDOM,
            sample_size=min(25, len(canonical_items)),
            samples_generated=False,
            created_by_id=creator_id,
        )
        db.add(pop)
        db.commit()
        db.refresh(pop)

        AuditFieldworkService._log_action(
            db=db,
            organization_id=organization_id,
            user_id=creator_id,
            action="AUDIT_POPULATION_CREATED",
            entity_type="AuditSamplePopulation",
            entity_id=pop.id,
            new_values={
                "procedure_id": procedure_id,
                "version_number": next_v,
                "total_count": pop.total_count,
                "population_digest_sha256": digest,
            }
        )
        return pop

    @staticmethod
    def freeze_population(
        db: Session,
        organization_id: int,
        audit_id: int,
        procedure_id: int,
        population_id: int,
        user_id: int,
    ) -> AuditSamplePopulation:
        pop = db.query(AuditSamplePopulation).filter(
            AuditSamplePopulation.id == population_id,
            AuditSamplePopulation.procedure_id == procedure_id,
            AuditSamplePopulation.organization_id == organization_id
        ).with_for_update().first()
        if not pop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample population not found.")

        if pop.is_frozen:
            return pop  # Idempotent return

        items = json.loads(pop.population_data_json or "[]")
        digest = AuditSamplingService.compute_population_digest(items)
        now = datetime.now(timezone.utc)

        pop.is_frozen = True
        pop.frozen_at = now
        pop.frozen_by_id = user_id
        pop.population_digest_sha256 = digest

        db.commit()
        db.refresh(pop)

        AuditFieldworkService._log_action(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="AUDIT_POPULATION_FROZEN",
            entity_type="AuditSamplePopulation",
            entity_id=pop.id,
            new_values={
                "is_frozen": True,
                "frozen_at": now.isoformat(),
                "population_digest_sha256": digest,
            }
        )
        return pop

    @staticmethod
    def generate_samples(
        db: Session,
        organization_id: int,
        audit_id: int,
        procedure_id: int,
        population_id: int,
        user_id: int,
        obj_in: AuditSampleGenerateRequest,
    ) -> AuditSamplePopulation:
        pop = db.query(AuditSamplePopulation).filter(
            AuditSamplePopulation.id == population_id,
            AuditSamplePopulation.procedure_id == procedure_id,
            AuditSamplePopulation.organization_id == organization_id
        ).with_for_update().first()
        if not pop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample population not found.")

        # HARD INVARIANT: Population must be frozen before sample extraction
        if not pop.is_frozen:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Population must be frozen before generating samples. Freeze the snapshot first."
            )

        # HARD INVARIANT: Idempotency / No silent overwrite of generated samples
        if pop.samples_generated:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Samples have already been generated for this population snapshot. Create a new population version to regenerate."
            )

        if obj_in.sample_size <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Sample size must be greater than zero."
            )
        if obj_in.sample_size > pop.total_count:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Sample size ({obj_in.sample_size}) cannot exceed population count ({pop.total_count})."
            )

        now = datetime.now(timezone.utc)
        items = json.loads(pop.population_data_json or "[]")

        # Derive server-authoritative seed
        seed_hex = AuditSamplingService.generate_seed(
            organization_id=organization_id,
            audit_id=audit_id,
            procedure_id=procedure_id,
            population_id=population_id,
            total_count=pop.total_count,
            sample_size=obj_in.sample_size,
            created_at=pop.created_at
        )

        try:
            selected_items = AuditSamplingService.execute_sampling(
                items=items,
                sampling_method=obj_in.sampling_method.value,
                sample_size=obj_in.sample_size,
                seed_hex=seed_hex,
                strata_attribute=obj_in.strata_attribute
            )
        except ValueError as ex:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ex))

        # Persist AuditSampleItem records
        for idx, it in enumerate(selected_items, start=1):
            sample_record = AuditSampleItem(
                organization_id=organization_id,
                population_id=pop.id,
                item_index=idx,
                source_record_id=str(it["source_record_id"]),
                item_attributes_json=json.dumps(it.get("attributes", {})),
                test_result=SampleResultEnum.PENDING,
            )
            db.add(sample_record)

        # Update population metadata
        pop.sampling_method = obj_in.sampling_method
        pop.sampling_seed = seed_hex
        pop.sample_size = obj_in.sample_size
        pop.sample_parameters_json = json.dumps({
            "method": obj_in.sampling_method.value,
            "sample_size": obj_in.sample_size,
            "strata_attribute": obj_in.strata_attribute,
        })
        pop.samples_generated = True
        pop.generated_at = now

        # Update procedure to reflect sampling active
        proc = db.query(AuditProcedure).filter(AuditProcedure.id == procedure_id).first()
        if proc:
            proc.has_sampling = True

        db.commit()
        db.refresh(pop)

        AuditFieldworkService._log_action(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="AUDIT_SAMPLE_GENERATED",
            entity_type="AuditSamplePopulation",
            entity_id=pop.id,
            new_values={
                "sampling_method": obj_in.sampling_method.value,
                "sample_size": obj_in.sample_size,
                "sampling_seed": seed_hex,
                "generated_at": now.isoformat(),
            }
        )
        return pop

    @staticmethod
    def get_population_with_samples(
        db: Session,
        organization_id: int,
        audit_id: int,
        procedure_id: int,
    ) -> Optional[AuditSamplePopulation]:
        return db.query(AuditSamplePopulation).filter(
            AuditSamplePopulation.procedure_id == procedure_id,
            AuditSamplePopulation.organization_id == organization_id
        ).order_by(AuditSamplePopulation.version_number.desc()).options(
            joinedload(AuditSamplePopulation.sample_items)
        ).first()

    @staticmethod
    def update_sample_item(
        db: Session,
        organization_id: int,
        audit_id: int,
        procedure_id: int,
        sample_id: int,
        user_id: int,
        obj_in: AuditSampleItemUpdate,
    ) -> AuditSampleItem:
        # Check if procedure workpaper is already approved/sealed
        proc = db.query(AuditProcedure).filter(
            AuditProcedure.id == procedure_id,
            AuditProcedure.audit_id == audit_id,
            AuditProcedure.organization_id == organization_id
        ).first()
        if not proc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found.")
        if proc.workpaper_status == "REVIEWED_APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify sample items after workpaper has been approved and sealed."
            )

        item = db.query(AuditSampleItem).join(AuditSamplePopulation).filter(
            AuditSampleItem.id == sample_id,
            AuditSampleItem.organization_id == organization_id,
            AuditSamplePopulation.procedure_id == procedure_id
        ).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample item not found.")

        if item.deficiency_finding_id and obj_in.test_result not in (SampleResultEnum.FAIL, SampleResultEnum.EXCEPTION):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change test result to '{obj_in.test_result.value}' for sample item already escalated to Finding ID {item.deficiency_finding_id}."
            )

        item.test_result = obj_in.test_result
        if obj_in.testing_notes is not None:
            item.testing_notes = obj_in.testing_notes.strip()
        if obj_in.evidence_item_id is not None:
            ev = db.query(EvidenceItem).filter(
                EvidenceItem.id == obj_in.evidence_item_id,
                EvidenceItem.organization_id == organization_id
            ).first()
            if not ev:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence item not found.")
            item.evidence_item_id = ev.id

        item.tested_by_id = user_id
        item.tested_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(item)

        AuditFieldworkService._log_action(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="AUDIT_SAMPLE_TESTED",
            entity_type="AuditSampleItem",
            entity_id=item.id,
            new_values={
                "test_result": item.test_result.value,
                "tested_by_id": user_id,
            }
        )
        return item

    # ─────────────────────────────────────────────────────────────────────────
    # SAMPLE DEFICIENCY -> FINDING ESCALATION BRIDGE
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def escalate_sample_deficiency(
        db: Session,
        organization_id: int,
        audit_id: int,
        procedure_id: int,
        sample_id: int,
        user_id: int,
        obj_in: AuditSampleEscalateFinding,
    ) -> Finding:
        item = db.query(AuditSampleItem).join(AuditSamplePopulation).filter(
            AuditSampleItem.id == sample_id,
            AuditSampleItem.organization_id == organization_id,
            AuditSamplePopulation.procedure_id == procedure_id
        ).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample item not found.")

        # Hard Idempotency Invariant: Prevent duplicate finding creation
        if item.deficiency_finding_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This sample item has already been escalated to Finding ID {item.deficiency_finding_id}."
            )

        if item.test_result not in (SampleResultEnum.FAIL, SampleResultEnum.EXCEPTION):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot escalate sample item with test result '{item.test_result.value}'. Must be FAIL or EXCEPTION."
            )

        proc = db.query(AuditProcedure).filter(AuditProcedure.id == procedure_id).first()
        if not proc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found.")
        if proc.workpaper_status == "REVIEWED_APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot escalate sample items after workpaper has been approved and sealed."
            )

        # Resolve authoritative OrganizationControl ID
        ctrl_id = proc.organization_control_id
        if not ctrl_id:
            # Check scope controls for a single in-scope control fallback
            scope_ctrl = db.query(AuditScopeControl).filter(
                AuditScopeControl.audit_id == audit_id,
                AuditScopeControl.organization_id == organization_id
            ).first()
            if scope_ctrl:
                ctrl_id = scope_ctrl.organization_control_id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot escalate deficiency: Procedure is not linked to an OrganizationControl and no controls are in scope."
                )

        # Validate severity
        severity_enum = FindingSeverityEnum.HIGH
        if obj_in.severity:
            try:
                severity_enum = FindingSeverityEnum[obj_in.severity.upper()]
            except KeyError:
                severity_enum = FindingSeverityEnum.HIGH

        title = obj_in.title or f"Audit Deficiency: {proc.title} [Sample {item.source_record_id}]"
        desc = (
            obj_in.description
            or f"Sample item {item.source_record_id} failed audit fieldwork testing. Testing notes: {item.testing_notes or 'None provided.'}"
        )

        # Instantiate authoritative Phase 4 Finding
        finding = Finding(
            organization_id=organization_id,
            organization_control_id=ctrl_id,
            title=title,
            description=desc,
            finding_type=FindingTypeEnum.CONTROL_GAP,
            severity=severity_enum,
            status=FindingStatusEnum.OPEN,
            recommendation="Remediate control breakdown identified during audit sampling fieldwork.",
            owner_id=user_id,
            created_by_id=user_id,
        )
        db.add(finding)
        db.flush()

        # Link finding to audit engagement
        link = AuditFindingLink(
            organization_id=organization_id,
            audit_id=audit_id,
            finding_id=finding.id,
            source_procedure_id=procedure_id,
            link_notes=f"Escalated from Sample Item {item.id} ({item.source_record_id})"
        )
        db.add(link)

        # Attach finding ID to sample item
        item.deficiency_finding_id = finding.id

        db.commit()
        db.refresh(finding)

        AuditFieldworkService._log_action(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="AUDIT_FINDING_ESCALATED",
            entity_type="Finding",
            entity_id=finding.id,
            new_values={
                "audit_id": audit_id,
                "procedure_id": procedure_id,
                "sample_item_id": item.id,
                "severity": severity_enum.value,
            }
        )
        return finding

    # ─────────────────────────────────────────────────────────────────────────
    # WORKPAPER FOUR-EYES GOVERNANCE & DIGEST SEALING
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def get_workpaper(
        db: Session,
        organization_id: int,
        audit_id: int,
        procedure_id: int,
    ) -> Optional[AuditWorkpaperReview]:
        return db.query(AuditWorkpaperReview).filter(
            AuditWorkpaperReview.procedure_id == procedure_id,
            AuditWorkpaperReview.organization_id == organization_id
        ).order_by(AuditWorkpaperReview.version_number.desc()).options(
            joinedload(AuditWorkpaperReview.prepared_by),
            joinedload(AuditWorkpaperReview.reviewed_by)
        ).first()

    @staticmethod
    def submit_workpaper(
        db: Session,
        organization_id: int,
        audit_id: int,
        procedure_id: int,
        user_id: int,
        obj_in: AuditWorkpaperSubmit,
    ) -> AuditWorkpaperReview:
        proc = db.query(AuditProcedure).filter(
            AuditProcedure.id == procedure_id,
            AuditProcedure.audit_id == audit_id,
            AuditProcedure.organization_id == organization_id
        ).first()
        if not proc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found.")

        # Check existing workpaper
        workpaper = db.query(AuditWorkpaperReview).filter(
            AuditWorkpaperReview.procedure_id == procedure_id,
            AuditWorkpaperReview.organization_id == organization_id
        ).order_by(AuditWorkpaperReview.version_number.desc()).first()

        now = datetime.now(timezone.utc)

        if workpaper and workpaper.status == WorkpaperStatusEnum.REVIEWED_APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This workpaper is already APPROVED and sealed. It cannot be re-submitted."
            )

        if not workpaper or workpaper.status == WorkpaperStatusEnum.CHANGES_REQUESTED:
            # If prior was rejected with changes requested, increment version or update draft
            next_v = (workpaper.version_number + 1) if (workpaper and workpaper.status == WorkpaperStatusEnum.CHANGES_REQUESTED) else 1
            workpaper = AuditWorkpaperReview(
                organization_id=organization_id,
                audit_id=audit_id,
                procedure_id=procedure_id,
                version_number=next_v,
                status=WorkpaperStatusEnum.SUBMITTED_FOR_REVIEW,
                testing_summary=obj_in.testing_summary.strip(),
                conclusion=obj_in.conclusion.strip(),
                prepared_by_id=user_id,
                prepared_at=now,
            )
            db.add(workpaper)
        else:
            # Update current draft
            workpaper.testing_summary = obj_in.testing_summary.strip()
            workpaper.conclusion = obj_in.conclusion.strip()
            workpaper.status = WorkpaperStatusEnum.SUBMITTED_FOR_REVIEW
            workpaper.prepared_by_id = user_id
            workpaper.prepared_at = now
            workpaper.rejection_reason = None

        proc.workpaper_status = "SUBMITTED_FOR_REVIEW"

        db.commit()
        db.refresh(workpaper)

        AuditFieldworkService._log_action(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            action="AUDIT_WORKPAPER_SUBMIT",
            entity_type="AuditWorkpaperReview",
            entity_id=workpaper.id,
            new_values={
                "procedure_id": procedure_id,
                "version_number": workpaper.version_number,
                "prepared_by_id": user_id,
                "status": "SUBMITTED_FOR_REVIEW",
            }
        )
        return workpaper

    @staticmethod
    def approve_workpaper(
        db: Session,
        organization_id: int,
        audit_id: int,
        procedure_id: int,
        reviewer_id: int,
        obj_in: AuditWorkpaperApprove,
    ) -> AuditWorkpaperReview:
        workpaper = db.query(AuditWorkpaperReview).filter(
            AuditWorkpaperReview.procedure_id == procedure_id,
            AuditWorkpaperReview.organization_id == organization_id
        ).order_by(AuditWorkpaperReview.version_number.desc()).with_for_update().first()
        if not workpaper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No workpaper found to approve.")

        if workpaper.status != WorkpaperStatusEnum.SUBMITTED_FOR_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve workpaper in status '{workpaper.status.value}'. Must be SUBMITTED_FOR_REVIEW."
            )

        # STRICT FOUR-EYES INVARIANT: Preparer cannot approve their own workpaper
        if workpaper.prepared_by_id == reviewer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Four-Eyes Governance Violation: The auditor who prepared this workpaper cannot approve it. An independent reviewer is required."
            )

        now = datetime.now(timezone.utc)
        workpaper.status = WorkpaperStatusEnum.REVIEWED_APPROVED
        workpaper.reviewed_by_id = reviewer_id
        workpaper.reviewed_at = now
        if obj_in.review_notes:
            workpaper.review_notes = obj_in.review_notes.strip()

        # Compute sample telemetry for digest
        sample_items = db.query(AuditSampleItem).join(AuditSamplePopulation).filter(
            AuditSamplePopulation.procedure_id == procedure_id
        ).all()
        total_samples = len(sample_items)
        fail_count = sum(1 for s in sample_items if s.test_result in (SampleResultEnum.FAIL, SampleResultEnum.EXCEPTION))
        pass_count = sum(1 for s in sample_items if s.test_result == SampleResultEnum.PASS)
        exception_rate = round(fail_count / total_samples * 100, 2) if total_samples > 0 else 0.0

        # Build canonical payload for tamper-evident digest
        digest_payload = {
            "organization_id": organization_id,
            "audit_id": audit_id,
            "procedure_id": procedure_id,
            "version_number": workpaper.version_number,
            "prepared_by_id": workpaper.prepared_by_id,
            "prepared_at": workpaper.prepared_at.isoformat(),
            "reviewed_by_id": reviewer_id,
            "reviewed_at": now.isoformat(),
            "testing_summary": workpaper.testing_summary,
            "conclusion": workpaper.conclusion,
            "sample_summary": {
                "total_samples": total_samples,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "exception_rate": exception_rate,
            }
        }
        canonical_bytes = json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        workpaper.workpaper_hash_sha256 = hashlib.sha256(canonical_bytes).hexdigest()

        # Update procedure status
        proc = db.query(AuditProcedure).filter(AuditProcedure.id == procedure_id).first()
        if proc:
            proc.workpaper_status = "REVIEWED_APPROVED"
            # If procedure result is not yet conclusive, update it
            if fail_count > 0:
                proc.result = ProcedureResultEnum.FAILED
            elif total_samples > 0 and pass_count == total_samples:
                proc.result = ProcedureResultEnum.PASSED

        db.commit()
        db.refresh(workpaper)

        AuditFieldworkService._log_action(
            db=db,
            organization_id=organization_id,
            user_id=reviewer_id,
            action="AUDIT_WORKPAPER_APPROVED",
            entity_type="AuditWorkpaperReview",
            entity_id=workpaper.id,
            new_values={
                "status": "REVIEWED_APPROVED",
                "reviewed_by_id": reviewer_id,
                "workpaper_hash_sha256": workpaper.workpaper_hash_sha256,
            }
        )
        return workpaper

    @staticmethod
    def request_changes_workpaper(
        db: Session,
        organization_id: int,
        audit_id: int,
        procedure_id: int,
        reviewer_id: int,
        obj_in: AuditWorkpaperRequestChanges,
    ) -> AuditWorkpaperReview:
        workpaper = db.query(AuditWorkpaperReview).filter(
            AuditWorkpaperReview.procedure_id == procedure_id,
            AuditWorkpaperReview.organization_id == organization_id
        ).order_by(AuditWorkpaperReview.version_number.desc()).with_for_update().first()
        if not workpaper:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No workpaper found.")

        if workpaper.status != WorkpaperStatusEnum.SUBMITTED_FOR_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot request changes on workpaper in status '{workpaper.status.value}'. Must be SUBMITTED_FOR_REVIEW."
            )

        # Four-Eyes Invariant
        if workpaper.prepared_by_id == reviewer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Four-Eyes Governance Violation: Preparer cannot perform review actions on their own workpaper."
            )

        now = datetime.now(timezone.utc)
        workpaper.status = WorkpaperStatusEnum.CHANGES_REQUESTED
        workpaper.reviewed_by_id = reviewer_id
        workpaper.reviewed_at = now
        workpaper.rejection_reason = obj_in.rejection_reason.strip()

        proc = db.query(AuditProcedure).filter(AuditProcedure.id == procedure_id).first()
        if proc:
            proc.workpaper_status = "CHANGES_REQUESTED"

        db.commit()
        db.refresh(workpaper)

        AuditFieldworkService._log_action(
            db=db,
            organization_id=organization_id,
            user_id=reviewer_id,
            action="AUDIT_WORKPAPER_CHANGES_REQUESTED",
            entity_type="AuditWorkpaperReview",
            entity_id=workpaper.id,
            new_values={
                "status": "CHANGES_REQUESTED",
                "rejection_reason": workpaper.rejection_reason,
            }
        )
        return workpaper
