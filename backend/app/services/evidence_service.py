from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.core.file_security import (
    compute_sha256,
    generate_secure_storage_key,
    sanitize_filename,
    validate_extension,
    validate_file_size,
    verify_content_type,
)
from app.models.control import OrganizationControl
from app.models.evidence import (
    EvidenceItem,
    EvidenceRequirement,
    EvidenceReview,
    EvidenceStatusEnum,
    EvidenceTypeEnum,
    ReviewDecisionEnum,
)
from app.models.framework import FrameworkSubcategory
from app.schemas.evidence import (
    EvidenceRequirementCreate,
    EvidenceRequirementUpdate,
    EvidenceReviewCreate,
)
from app.storage.local import get_storage_provider


class EvidenceService:
    # ----------------------------------------------------------------
    # Evidence Requirements
    # ----------------------------------------------------------------
    @staticmethod
    def list_requirements(
        db: Session,
        organization_id: int,
        organization_control_id: Optional[int] = None,
        is_required: Optional[bool] = None,
        evidence_type: Optional[EvidenceTypeEnum] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(EvidenceRequirement)
            .filter(EvidenceRequirement.organization_id == organization_id)
            .options(joinedload(EvidenceRequirement.created_by))
        )

        if organization_control_id:
            query = query.filter(EvidenceRequirement.organization_control_id == organization_control_id)
        if is_required is not None:
            query = query.filter(EvidenceRequirement.is_required == is_required)
        if evidence_type:
            query = query.filter(EvidenceRequirement.evidence_type == evidence_type)
        if search:
            query = query.filter(
                (EvidenceRequirement.title.ilike(f"%{search}%"))
                | (EvidenceRequirement.description.ilike(f"%{search}%"))
            )

        reqs = query.order_by(EvidenceRequirement.created_at.asc()).offset(skip).limit(limit).all()

        results = []
        for r in reqs:
            total_items = (
                db.query(EvidenceItem)
                .filter(
                    EvidenceItem.organization_id == organization_id,
                    EvidenceItem.evidence_requirement_id == r.id,
                )
                .count()
            )
            accepted_items = (
                db.query(EvidenceItem)
                .filter(
                    EvidenceItem.organization_id == organization_id,
                    EvidenceItem.evidence_requirement_id == r.id,
                    EvidenceItem.status == EvidenceStatusEnum.ACCEPTED,
                )
                .count()
            )

            results.append({
                "id": r.id,
                "organization_id": r.organization_id,
                "organization_control_id": r.organization_control_id,
                "title": r.title,
                "description": r.description,
                "evidence_type": r.evidence_type,
                "is_required": r.is_required,
                "guidance": r.guidance,
                "created_by_id": r.created_by_id,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "created_by": r.created_by,
                "items_count": total_items,
                "accepted_items_count": accepted_items,
            })

        return results

    @staticmethod
    def get_requirement_by_id(
        db: Session, requirement_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        r = (
            db.query(EvidenceRequirement)
            .filter(
                EvidenceRequirement.id == requirement_id,
                EvidenceRequirement.organization_id == organization_id,
            )
            .options(joinedload(EvidenceRequirement.created_by))
            .first()
        )
        if not r:
            return None

        total_items = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.organization_id == organization_id,
                EvidenceItem.evidence_requirement_id == r.id,
            )
            .count()
        )
        accepted_items = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.organization_id == organization_id,
                EvidenceItem.evidence_requirement_id == r.id,
                EvidenceItem.status == EvidenceStatusEnum.ACCEPTED,
            )
            .count()
        )

        return {
            "id": r.id,
            "organization_id": r.organization_id,
            "organization_control_id": r.organization_control_id,
            "title": r.title,
            "description": r.description,
            "evidence_type": r.evidence_type,
            "is_required": r.is_required,
            "guidance": r.guidance,
            "created_by_id": r.created_by_id,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "created_by": r.created_by,
            "items_count": total_items,
            "accepted_items_count": accepted_items,
        }

    @staticmethod
    def create_requirement(
        db: Session, obj_in: EvidenceRequirementCreate, organization_id: int, created_by_id: Optional[int]
    ) -> EvidenceRequirement:
        # Verify control exists and belongs to organization
        ctrl = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == obj_in.organization_control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .first()
        )
        if not ctrl:
            raise ValueError(f"Organization control ID {obj_in.organization_control_id} not found in your tenant.")

        req = EvidenceRequirement(
            organization_id=organization_id,
            organization_control_id=obj_in.organization_control_id,
            title=obj_in.title,
            description=obj_in.description,
            evidence_type=obj_in.evidence_type,
            is_required=obj_in.is_required,
            guidance=obj_in.guidance,
            created_by_id=created_by_id,
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def update_requirement(
        db: Session, requirement_id: int, organization_id: int, obj_in: EvidenceRequirementUpdate
    ) -> Optional[EvidenceRequirement]:
        req = (
            db.query(EvidenceRequirement)
            .filter(
                EvidenceRequirement.id == requirement_id,
                EvidenceRequirement.organization_id == organization_id,
            )
            .first()
        )
        if not req:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(req, field, value)

        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def delete_requirement(
        db: Session, requirement_id: int, organization_id: int
    ) -> bool:
        req = (
            db.query(EvidenceRequirement)
            .filter(
                EvidenceRequirement.id == requirement_id,
                EvidenceRequirement.organization_id == organization_id,
            )
            .first()
        )
        if not req:
            return False

        db.delete(req)
        db.commit()
        return True

    # ----------------------------------------------------------------
    # Evidence Items & Upload
    # ----------------------------------------------------------------
    @staticmethod
    def list_evidence(
        db: Session,
        organization_id: int,
        organization_control_id: Optional[int] = None,
        evidence_requirement_id: Optional[int] = None,
        status: Optional[EvidenceStatusEnum] = None,
        uploaded_by_id: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = (
            db.query(EvidenceItem)
            .filter(EvidenceItem.organization_id == organization_id)
            .options(
                joinedload(EvidenceItem.uploaded_by),
                joinedload(EvidenceItem.requirement),
                joinedload(EvidenceItem.organization_control).joinedload(OrganizationControl.subcategory),
                joinedload(EvidenceItem.reviews).joinedload(EvidenceReview.reviewer),
            )
        )

        if organization_control_id:
            query = query.filter(EvidenceItem.organization_control_id == organization_control_id)
        if evidence_requirement_id:
            query = query.filter(EvidenceItem.evidence_requirement_id == evidence_requirement_id)
        if status:
            query = query.filter(EvidenceItem.status == status)
        if uploaded_by_id:
            query = query.filter(EvidenceItem.uploaded_by_id == uploaded_by_id)
        if search:
            query = query.filter(
                (EvidenceItem.title.ilike(f"%{search}%"))
                | (EvidenceItem.description.ilike(f"%{search}%"))
                | (EvidenceItem.original_filename.ilike(f"%{search}%"))
            )

        items = query.order_by(EvidenceItem.created_at.desc()).offset(skip).limit(limit).all()

        results = []
        for it in items:
            latest_review = it.reviews[0] if it.reviews else None
            ctrl_id = it.organization_control.subcategory.identifier if it.organization_control and it.organization_control.subcategory else None
            ctrl_title = it.organization_control.subcategory.title if it.organization_control and it.organization_control.subcategory else None
            req_title = it.requirement.title if it.requirement else None

            results.append({
                "id": it.id,
                "organization_id": it.organization_id,
                "organization_control_id": it.organization_control_id,
                "evidence_requirement_id": it.evidence_requirement_id,
                "uploaded_by_id": it.uploaded_by_id,
                "title": it.title,
                "description": it.description,
                "original_filename": it.original_filename,
                "stored_filename": it.stored_filename,
                "file_extension": it.file_extension,
                "content_type": it.content_type,
                "file_size": it.file_size,
                "sha256_hash": it.sha256_hash,
                "status": it.status,
                "superseded_by_id": it.superseded_by_id,
                "created_at": it.created_at,
                "updated_at": it.updated_at,
                "uploaded_by": it.uploaded_by,
                "requirement_title": req_title,
                "control_identifier": ctrl_id,
                "control_title": ctrl_title,
                "latest_review": latest_review,
            })

        return results

    @staticmethod
    def get_evidence_by_id(
        db: Session, evidence_id: int, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        it = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == evidence_id,
                EvidenceItem.organization_id == organization_id,
            )
            .options(
                joinedload(EvidenceItem.uploaded_by),
                joinedload(EvidenceItem.requirement),
                joinedload(EvidenceItem.organization_control).joinedload(OrganizationControl.subcategory),
                joinedload(EvidenceItem.reviews).joinedload(EvidenceReview.reviewer),
            )
            .first()
        )
        if not it:
            return None

        latest_review = it.reviews[0] if it.reviews else None
        ctrl_id = it.organization_control.subcategory.identifier if it.organization_control and it.organization_control.subcategory else None
        ctrl_title = it.organization_control.subcategory.title if it.organization_control and it.organization_control.subcategory else None
        req_title = it.requirement.title if it.requirement else None

        return {
            "id": it.id,
            "organization_id": it.organization_id,
            "organization_control_id": it.organization_control_id,
            "evidence_requirement_id": it.evidence_requirement_id,
            "uploaded_by_id": it.uploaded_by_id,
            "title": it.title,
            "description": it.description,
            "original_filename": it.original_filename,
            "stored_filename": it.stored_filename,
            "file_extension": it.file_extension,
            "content_type": it.content_type,
            "file_size": it.file_size,
            "sha256_hash": it.sha256_hash,
            "status": it.status,
            "superseded_by_id": it.superseded_by_id,
            "created_at": it.created_at,
            "updated_at": it.updated_at,
            "uploaded_by": it.uploaded_by,
            "requirement_title": req_title,
            "control_identifier": ctrl_id,
            "control_title": ctrl_title,
            "latest_review": latest_review,
            "reviews": it.reviews,
        }

    @staticmethod
    def upload_evidence(
        db: Session,
        organization_id: int,
        organization_control_id: int,
        evidence_requirement_id: Optional[int],
        title: str,
        description: Optional[str],
        file_bytes: bytes,
        original_filename: str,
        declared_content_type: str,
        uploaded_by_id: Optional[int],
    ) -> EvidenceItem:
        # 1. Validate organization control exists
        ctrl = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.id == organization_control_id,
                OrganizationControl.organization_id == organization_id,
            )
            .first()
        )
        if not ctrl:
            raise ValueError(f"Organization control ID {organization_control_id} not found in your tenant.")

        # 2. Validate requirement if provided
        if evidence_requirement_id is not None:
            req = (
                db.query(EvidenceRequirement)
                .filter(
                    EvidenceRequirement.id == evidence_requirement_id,
                    EvidenceRequirement.organization_id == organization_id,
                )
                .first()
            )
            if not req:
                raise ValueError(f"Evidence requirement ID {evidence_requirement_id} not found in your tenant.")

        # 3. Security validations on untrusted file input
        file_size = len(file_bytes)
        validate_file_size(file_size)

        sanitized_name = sanitize_filename(original_filename)
        ext = validate_extension(sanitized_name)
        canonical_content_type = verify_content_type(file_bytes, ext, declared_content_type)
        sha256_hash = compute_sha256(file_bytes)

        # 4. Generate random storage key & persist via storage provider
        storage_key, stored_filename = generate_secure_storage_key(organization_id, ext)
        storage_provider = get_storage_provider()
        storage_provider.save(file_bytes, storage_key)

        # 5. Create database record
        item = EvidenceItem(
            organization_id=organization_id,
            organization_control_id=organization_control_id,
            evidence_requirement_id=evidence_requirement_id,
            uploaded_by_id=uploaded_by_id,
            title=title.strip() or sanitized_name,
            description=description,
            original_filename=sanitized_name,
            stored_filename=stored_filename,
            file_extension=ext,
            content_type=canonical_content_type,
            file_size=file_size,
            sha256_hash=sha256_hash,
            storage_key=storage_key,
            status=EvidenceStatusEnum.UPLOADED,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_evidence_metadata(
        db: Session,
        evidence_id: int,
        organization_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[EvidenceItem]:
        item = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == evidence_id,
                EvidenceItem.organization_id == organization_id,
            )
            .first()
        )
        if not item:
            return None

        if item.status == EvidenceStatusEnum.SUPERSEDED:
            raise ValueError("Cannot edit metadata of superseded historical evidence.")

        if title is not None:
            item.title = title.strip()
        if description is not None:
            item.description = description

        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def submit_for_review(
        db: Session, evidence_id: int, organization_id: int
    ) -> Optional[EvidenceItem]:
        item = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == evidence_id,
                EvidenceItem.organization_id == organization_id,
            )
            .first()
        )
        if not item:
            return None

        if item.status in [EvidenceStatusEnum.SUPERSEDED, EvidenceStatusEnum.ACCEPTED]:
            raise ValueError(f"Evidence in status '{item.status.value}' cannot be submitted for review.")

        item.status = EvidenceStatusEnum.UNDER_REVIEW
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def review_evidence(
        db: Session,
        evidence_id: int,
        organization_id: int,
        review_in: EvidenceReviewCreate,
        reviewer_id: Optional[int],
    ) -> Tuple[EvidenceItem, EvidenceReview]:
        item = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == evidence_id,
                EvidenceItem.organization_id == organization_id,
            )
            .first()
        )
        if not item:
            raise ValueError("Evidence item not found in your organization.")

        if item.status == EvidenceStatusEnum.SUPERSEDED:
            raise ValueError("Cannot review superseded historical evidence.")

        if review_in.decision == ReviewDecisionEnum.REJECT and not review_in.rejection_reason:
            raise ValueError("Rejection reason is required when rejecting an evidence item.")

        # Create review record
        rev = EvidenceReview(
            organization_id=organization_id,
            evidence_id=item.id,
            reviewer_id=reviewer_id,
            decision=review_in.decision,
            review_notes=review_in.review_notes,
            rejection_reason=review_in.rejection_reason if review_in.decision == ReviewDecisionEnum.REJECT else None,
        )
        db.add(rev)

        # Update evidence item status
        if review_in.decision == ReviewDecisionEnum.ACCEPT:
            item.status = EvidenceStatusEnum.ACCEPTED
        else:
            item.status = EvidenceStatusEnum.REJECTED

        db.add(item)
        db.commit()
        db.refresh(item)
        db.refresh(rev)
        return item, rev

    @staticmethod
    def supersede_evidence(
        db: Session,
        old_evidence_id: int,
        new_evidence_id: int,
        organization_id: int,
    ) -> EvidenceItem:
        old_item = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == old_evidence_id,
                EvidenceItem.organization_id == organization_id,
            )
            .first()
        )
        if not old_item:
            raise ValueError("Previous evidence item not found in your organization.")

        new_item = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == new_evidence_id,
                EvidenceItem.organization_id == organization_id,
            )
            .first()
        )
        if not new_item:
            raise ValueError("Replacement evidence item not found in your organization.")

        old_item.status = EvidenceStatusEnum.SUPERSEDED
        old_item.superseded_by_id = new_item.id
        db.add(old_item)
        db.commit()
        db.refresh(old_item)
        return old_item

    @staticmethod
    def get_evidence_file_for_download(
        db: Session, evidence_id: int, organization_id: int
    ) -> Tuple[bytes, str, str, int]:
        """Retrieve binary file data and verified metadata for secure download."""
        item = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == evidence_id,
                EvidenceItem.organization_id == organization_id,
            )
            .first()
        )
        if not item:
            raise ValueError("Evidence item not found in your organization.")

        storage_provider = get_storage_provider()
        file_bytes = storage_provider.get(item.storage_key)

        return file_bytes, item.original_filename, item.content_type, item.file_size

    # ----------------------------------------------------------------
    # Assurance Metrics & Calculations
    # ----------------------------------------------------------------
    @staticmethod
    def calculate_control_evidence_metrics(
        db: Session, organization_control_id: int, organization_id: int
    ) -> Dict[str, Any]:
        reqs = (
            db.query(EvidenceRequirement)
            .filter(
                EvidenceRequirement.organization_control_id == organization_control_id,
                EvidenceRequirement.organization_id == organization_id,
            )
            .all()
        )

        total_reqs = len(reqs)
        required_reqs = sum(1 for r in reqs if r.is_required)

        items = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.organization_control_id == organization_control_id,
                EvidenceItem.organization_id == organization_id,
            )
            .all()
        )

        total_submitted = len(items)
        accepted_count = sum(1 for i in items if i.status == EvidenceStatusEnum.ACCEPTED)
        rejected_count = sum(1 for i in items if i.status == EvidenceStatusEnum.REJECTED)
        pending_count = sum(1 for i in items if i.status in [EvidenceStatusEnum.UPLOADED, EvidenceStatusEnum.UNDER_REVIEW])
        superseded_count = sum(1 for i in items if i.status == EvidenceStatusEnum.SUPERSEDED)

        # Evidence Coverage Formula:
        # If mandatory requirements exist, coverage = (accepted required evidence requirements / total mandatory requirements) * 100
        if required_reqs > 0:
            # Check how many distinct mandatory requirements have at least 1 ACCEPTED evidence item
            accepted_req_ids = set(
                row[0]
                for row in db.query(EvidenceItem.evidence_requirement_id)
                .filter(
                    EvidenceItem.organization_control_id == organization_control_id,
                    EvidenceItem.organization_id == organization_id,
                    EvidenceItem.status == EvidenceStatusEnum.ACCEPTED,
                    EvidenceItem.evidence_requirement_id.isnot(None),
                )
                .all()
            )
            satisfied_mandatory = sum(1 for r in reqs if r.is_required and r.id in accepted_req_ids)
            coverage_pct = round((satisfied_mandatory / required_reqs) * 100.0, 1)
        elif total_reqs > 0:
            coverage_pct = 100.0 if accepted_count > 0 else 0.0
        else:
            coverage_pct = 0.0

        return {
            "organization_control_id": organization_control_id,
            "total_requirements": total_reqs,
            "required_count": required_reqs,
            "submitted_count": total_submitted,
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "pending_count": pending_count,
            "superseded_count": superseded_count,
            "evidence_coverage_pct": coverage_pct,
        }

    @staticmethod
    def calculate_organization_evidence_stats(
        db: Session, organization_id: int
    ) -> Dict[str, Any]:
        items = (
            db.query(EvidenceItem)
            .filter(EvidenceItem.organization_id == organization_id)
            .all()
        )

        total_items = len(items)
        accepted = sum(1 for i in items if i.status == EvidenceStatusEnum.ACCEPTED)
        pending = sum(1 for i in items if i.status in [EvidenceStatusEnum.UPLOADED, EvidenceStatusEnum.UNDER_REVIEW])
        rejected = sum(1 for i in items if i.status == EvidenceStatusEnum.REJECTED)
        uploaded = sum(1 for i in items if i.status == EvidenceStatusEnum.UPLOADED)
        superseded = sum(1 for i in items if i.status == EvidenceStatusEnum.SUPERSEDED)

        # Mandatory requirements across all controls
        mandatory_reqs = (
            db.query(EvidenceRequirement)
            .filter(
                EvidenceRequirement.organization_id == organization_id,
                EvidenceRequirement.is_required == True,
            )
            .all()
        )

        total_mandatory = len(mandatory_reqs)
        if total_mandatory > 0:
            accepted_req_ids = set(
                row[0]
                for row in db.query(EvidenceItem.evidence_requirement_id)
                .filter(
                    EvidenceItem.organization_id == organization_id,
                    EvidenceItem.status == EvidenceStatusEnum.ACCEPTED,
                    EvidenceItem.evidence_requirement_id.isnot(None),
                )
                .all()
            )
            satisfied_mandatory = sum(1 for r in mandatory_reqs if r.id in accepted_req_ids)
            overall_coverage = round((satisfied_mandatory / total_mandatory) * 100.0, 1)
        else:
            overall_coverage = 0.0

        # Controls with mandatory requirements but 0 accepted evidence
        missing_evidence_controls = 0
        if total_mandatory > 0:
            controls_with_mandatory = set(r.organization_control_id for r in mandatory_reqs)
            for c_id in controls_with_mandatory:
                c_reqs = [r for r in mandatory_reqs if r.organization_control_id == c_id]
                c_accepted = (
                    db.query(EvidenceItem)
                    .filter(
                        EvidenceItem.organization_control_id == c_id,
                        EvidenceItem.organization_id == organization_id,
                        EvidenceItem.status == EvidenceStatusEnum.ACCEPTED,
                    )
                    .count()
                )
                if c_accepted == 0:
                    missing_evidence_controls += 1

        return {
            "total_evidence_items": total_items,
            "accepted_count": accepted,
            "pending_review_count": pending,
            "rejected_count": rejected,
            "uploaded_count": uploaded,
            "superseded_count": superseded,
            "overall_coverage_pct": overall_coverage,
            "controls_missing_required_evidence": missing_evidence_controls,
        }