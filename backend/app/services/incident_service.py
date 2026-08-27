from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.incident import (
    DisclosureStatusEnum,
    DisclosureTriggerTypeEnum,
    IncidentCategoryEnum,
    IncidentControlLink,
    IncidentControlRelationshipEnum,
    IncidentRegulatoryDisclosure,
    IncidentSeverityEnum,
    IncidentStatusEnum,
    IncidentTimelineEvent,
    IncidentVendorLink,
    RegulatorEnum,
    RootCauseClassificationEnum,
    SecurityIncident,
    TimelineEventSourceEnum,
    TimelineEventTypeEnum,
)
from app.models.control import OrganizationControl
from app.models.tprm import Vendor, VendorEngagement
from app.models.user import User
from app.services.audit_service import AuditService


class IncidentService:
    """Authoritative Domain Engine for Phase 10 Security Incident Management & Regulatory Disclosure."""

    # ─── 1. CANONICAL LIFECYCLE TRANSITION STATE MACHINE ─────────────────────

    LEGAL_TRANSITIONS = {
        IncidentStatusEnum.DECLARED: [IncidentStatusEnum.TRIAGED],
        IncidentStatusEnum.TRIAGED: [IncidentStatusEnum.CONTAINED],
        IncidentStatusEnum.CONTAINED: [IncidentStatusEnum.ERADICATED],
        IncidentStatusEnum.ERADICATED: [IncidentStatusEnum.RECOVERED],
        IncidentStatusEnum.RECOVERED: [IncidentStatusEnum.CONTAINED, IncidentStatusEnum.POST_MORTEM],
        IncidentStatusEnum.POST_MORTEM: [IncidentStatusEnum.CLOSED],
        IncidentStatusEnum.CLOSED: [],  # Terminal immutability
    }

    @classmethod
    def _get_actor_email(cls, db: Session, user_id: Optional[int]) -> str:
        """Helper to resolve actor email for audit logging."""
        if not user_id:
            return "system@controlsphere.internal"
        user = db.query(User).filter(User.id == user_id).first()
        return user.email if user else "system@controlsphere.internal"

    @classmethod
    def validate_lifecycle_transition(
        cls,
        current_status: IncidentStatusEnum,
        target_status: IncidentStatusEnum,
    ) -> None:
        """Enforces canonical progressive lifecycle state transitions and terminal immutability."""
        if current_status == IncidentStatusEnum.CLOSED:
            raise ValueError("Invalid transition: Closed incidents are permanently immutable.")

        allowed = cls.LEGAL_TRANSITIONS.get(current_status, [])
        if target_status not in allowed:
            raise ValueError(
                f"Invalid incident lifecycle transition: '{current_status.value}' -> '{target_status.value}'. "
                f"Allowed transitions from '{current_status.value}' are: {[s.value for s in allowed]}."
            )

    # ─── 2. DETERMINISTIC REGULATORY DEADLINE ENGINE ─────────────────────────

    @classmethod
    def add_business_days(cls, start_dt: datetime, n_days: int) -> datetime:
        """Adds n business days (Monday-Friday) to a UTC datetime."""
        cur = start_dt
        added = 0
        while added < n_days:
            cur += timedelta(days=1)
            # Monday is 0, Sunday is 6
            if cur.weekday() < 5:
                added += 1
        return cur

    @classmethod
    def calculate_regulatory_deadline(
        cls,
        regulator: RegulatorEnum,
        triggered_at: datetime,
        trigger_type: DisclosureTriggerTypeEnum,
        rule_version: str = "1.0",
    ) -> Tuple[datetime, str, str]:
        """
        Calculates server-authoritative regulatory notification deadline in UTC.
        Preserves rule_version and calculation_version for defensible legal audits.
        """
        calc_version = "1.0"

        if regulator == RegulatorEnum.GDPR_DPA:
            # GDPR Article 33: 72 hours from detection/awareness
            deadline = triggered_at + timedelta(hours=72)
        elif regulator == RegulatorEnum.NYDFS:
            # 23 NYCRR 500.17: 72 hours from determination of material cybersecurity event
            deadline = triggered_at + timedelta(hours=72)
        elif regulator == RegulatorEnum.PCI_SSC:
            # PCI-DSS Req 12.10.5: 24 hours from confirmed CDE breach
            deadline = triggered_at + timedelta(hours=24)
        elif regulator == RegulatorEnum.HHS_OCR:
            # HIPAA Breach Notification Rule: 60 calendar days for breaches affecting >= 500 individuals
            deadline = triggered_at + timedelta(days=60)
        elif regulator == RegulatorEnum.SEC_8K:
            # SEC Item 1.05 Form 8-K: 4 business days from materiality determination
            deadline = cls.add_business_days(triggered_at, 4)
            calc_version = "1.0_business_days"
        elif regulator == RegulatorEnum.STATE_AG:
            # US State Breach Notification: Default statutory baseline (30 calendar days)
            deadline = triggered_at + timedelta(days=30)
            calc_version = "1.0_state_default_30d"
        else:
            deadline = triggered_at + timedelta(hours=72)

        return deadline, rule_version, calc_version

    # ─── 3. INCIDENT CREATION & MUTATION ─────────────────────────────────────

    @classmethod
    def create_incident(
        cls,
        db: Session,
        organization_id: int,
        incident_commander_id: int,
        incident_code: str,
        title: str,
        description: str,
        severity: IncidentSeverityEnum,
        category: IncidentCategoryEnum,
        detected_at: datetime,
        declared_at: Optional[datetime] = None,
        business_owner_id: Optional[int] = None,
        affected_record_count: int = 0,
        affected_systems_summary: Optional[str] = None,
        financial_impact_estimate: float = 0.0,
        compliance_drift_alert_id: Optional[int] = None,
    ) -> SecurityIncident:
        """Creates a new SecurityIncident in DECLARED status and logs audit trail."""
        if affected_record_count < 0:
            raise ValueError("Affected record count must be non-negative.")
        if financial_impact_estimate < 0.0:
            raise ValueError("Financial impact estimate must be non-negative.")

        now_utc = datetime.now(timezone.utc)
        dec_at = declared_at or now_utc

        incident = SecurityIncident(
            organization_id=organization_id,
            incident_code=incident_code.strip().upper(),
            title=title.strip(),
            description=description.strip(),
            severity=severity,
            category=category,
            status=IncidentStatusEnum.DECLARED,
            incident_commander_id=incident_commander_id,
            business_owner_id=business_owner_id,
            detected_at=detected_at,
            declared_at=dec_at,
            affected_record_count=affected_record_count,
            affected_systems_summary=affected_systems_summary,
            financial_impact_estimate=financial_impact_estimate,
            compliance_drift_alert_id=compliance_drift_alert_id,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        # Initial Timeline Event
        cls.append_timeline_event(
            db=db,
            incident=incident,
            actor_id=incident_commander_id,
            event_type=TimelineEventTypeEnum.DETECTION,
            event_occurred_at=detected_at,
            description=f"Incident {incident.incident_code} declared: {incident.title}",
            source=TimelineEventSourceEnum.MANUAL_ENTRY,
        )

        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="INCIDENT_DECLARED",
            resource_type="security_incident",
            actor_email=cls._get_actor_email(db, incident_commander_id),
            actor_id=incident_commander_id,
            resource_id=str(incident.id),
            details={
                "incident_code": incident.incident_code,
                "severity": incident.severity.value,
                "category": incident.category.value,
            },
        )

        return incident

    @classmethod
    def update_incident_metadata(
        cls,
        db: Session,
        incident: SecurityIncident,
        user_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        severity: Optional[IncidentSeverityEnum] = None,
        category: Optional[IncidentCategoryEnum] = None,
        business_owner_id: Optional[int] = None,
        affected_record_count: Optional[int] = None,
        affected_systems_summary: Optional[str] = None,
        financial_impact_estimate: Optional[float] = None,
        root_cause_classification: Optional[RootCauseClassificationEnum] = None,
        root_cause_narrative: Optional[str] = None,
        lessons_learned: Optional[str] = None,
    ) -> SecurityIncident:
        """Updates mutable incident metadata. Rejects mutation if CLOSED."""
        if incident.status == IncidentStatusEnum.CLOSED:
            raise ValueError("Closed incidents are permanently immutable.")

        if affected_record_count is not None:
            if affected_record_count < 0:
                raise ValueError("Affected record count must be non-negative.")
            incident.affected_record_count = affected_record_count

        if financial_impact_estimate is not None:
            if financial_impact_estimate < 0.0:
                raise ValueError("Financial impact estimate must be non-negative.")
            incident.financial_impact_estimate = financial_impact_estimate

        if title is not None:
            incident.title = title.strip()
        if description is not None:
            incident.description = description.strip()
        if severity is not None:
            incident.severity = severity
        if category is not None:
            incident.category = category
        if business_owner_id is not None:
            incident.business_owner_id = business_owner_id
        if root_cause_classification is not None:
            incident.root_cause_classification = root_cause_classification
        if root_cause_narrative is not None:
            incident.root_cause_narrative = root_cause_narrative
        if lessons_learned is not None:
            incident.lessons_learned = lessons_learned

        incident.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(incident)

        AuditService.log(
            db=db,
            organization_id=incident.organization_id,
            action="INCIDENT_UPDATED",
            resource_type="security_incident",
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            resource_id=str(incident.id),
            details={"updated_fields": ["title", "severity", "category", "financial_impact"]},
        )
        return incident

    @classmethod
    def set_materiality(
        cls,
        db: Session,
        incident: SecurityIncident,
        user_id: int,
        is_material: bool,
        materiality_notes: Optional[str] = None,
    ) -> SecurityIncident:
        """
        Sets SEC Item 1.05 materiality determination.
        Auto-evaluates SEC_8K disclosure clock when marked material.
        """
        if incident.status == IncidentStatusEnum.CLOSED:
            raise ValueError("Closed incidents are permanently immutable.")

        now_utc = datetime.now(timezone.utc)
        incident.is_material = is_material
        if is_material:
            incident.materiality_determined_at = now_utc
            incident.materiality_determined_by_id = user_id

            # Auto-trigger or update SEC_8K disclosure
            cls.evaluate_regulatory_disclosure(
                db=db,
                incident=incident,
                regulator=RegulatorEnum.SEC_8K,
                triggered_by_id=user_id,
                trigger_type=DisclosureTriggerTypeEnum.MATERIALITY_DETERMINATION,
                triggered_at=now_utc,
            )

        incident.updated_at = now_utc
        db.commit()
        db.refresh(incident)

        cls.append_timeline_event(
            db=db,
            incident=incident,
            actor_id=user_id,
            event_type=TimelineEventTypeEnum.POST_MORTEM_NOTE,
            event_occurred_at=now_utc,
            description=f"Materiality determination set to: {is_material}. Notes: {materiality_notes or 'N/A'}",
        )

        AuditService.log(
            db=db,
            organization_id=incident.organization_id,
            action="INCIDENT_UPDATED",
            resource_type="security_incident",
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            resource_id=str(incident.id),
            details={"is_material": is_material},
        )
        return incident

    # ─── 4. LIFECYCLE TRANSITION & FOUR-EYES CLOSURE ─────────────────────────

    @classmethod
    def transition_lifecycle(
        cls,
        db: Session,
        incident: SecurityIncident,
        target_status: IncidentStatusEnum,
        user_id: int,
        notes: Optional[str] = None,
    ) -> SecurityIncident:
        """Transitions incident lifecycle state and stamps operational timestamps."""
        cls.validate_lifecycle_transition(incident.status, target_status)

        now_utc = datetime.now(timezone.utc)

        if target_status == IncidentStatusEnum.CONTAINED:
            incident.contained_at = now_utc
            event_type = TimelineEventTypeEnum.CONTAINMENT_ACTION
        elif target_status == IncidentStatusEnum.ERADICATED:
            incident.eradicated_at = now_utc
            event_type = TimelineEventTypeEnum.ERADICATION_STEP
        elif target_status == IncidentStatusEnum.RECOVERED:
            incident.recovered_at = now_utc
            event_type = TimelineEventTypeEnum.COMMAND_TRANSFER
        elif target_status == IncidentStatusEnum.POST_MORTEM:
            incident.post_mortem_at = now_utc
            event_type = TimelineEventTypeEnum.POST_MORTEM_NOTE
        elif target_status == IncidentStatusEnum.TRIAGED:
            event_type = TimelineEventTypeEnum.DETECTION
        else:
            event_type = TimelineEventTypeEnum.COMMAND_TRANSFER

        old_status = incident.status
        incident.status = target_status
        incident.updated_at = now_utc
        db.commit()
        db.refresh(incident)

        cls.append_timeline_event(
            db=db,
            incident=incident,
            actor_id=user_id,
            event_type=event_type,
            event_occurred_at=now_utc,
            description=f"Incident transitioned from {old_status.value} to {target_status.value}. Notes: {notes or 'N/A'}",
        )

        AuditService.log(
            db=db,
            organization_id=incident.organization_id,
            action="INCIDENT_STATUS_TRANSITION",
            resource_type="security_incident",
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            resource_id=str(incident.id),
            details={"old_status": old_status.value, "new_status": target_status.value},
        )
        return incident

    @classmethod
    def close_incident(
        cls,
        db: Session,
        incident: SecurityIncident,
        closed_by_id: int,
        closure_notes: str,
        lessons_learned: Optional[str] = None,
        root_cause_classification: Optional[RootCauseClassificationEnum] = None,
        root_cause_narrative: Optional[str] = None,
    ) -> SecurityIncident:
        """
        Closes incident under strict Four-Eyes governance.
        Closing user cannot be the Incident Commander.
        """
        if incident.status != IncidentStatusEnum.POST_MORTEM:
            raise ValueError(
                f"Incident must be in POST_MORTEM status before closing. Current status: '{incident.status.value}'."
            )

        if closed_by_id == incident.incident_commander_id:
            raise ValueError(
                "Separation of duties violation: The Incident Commander cannot close their own incident. "
                "Independent management review is required."
            )

        if not closure_notes or len(closure_notes.strip()) < 10:
            raise ValueError("Mandatory closure notes (minimum 10 characters) are required to close an incident.")

        now_utc = datetime.now(timezone.utc)
        incident.status = IncidentStatusEnum.CLOSED
        incident.closed_by_id = closed_by_id
        incident.closed_at = now_utc
        incident.closure_notes = closure_notes.strip()
        if lessons_learned:
            incident.lessons_learned = lessons_learned.strip()
        if root_cause_classification:
            incident.root_cause_classification = root_cause_classification
        if root_cause_narrative:
            incident.root_cause_narrative = root_cause_narrative.strip()

        incident.updated_at = now_utc
        db.commit()
        db.refresh(incident)

        cls.append_timeline_event(
            db=db,
            incident=incident,
            actor_id=closed_by_id,
            event_type=TimelineEventTypeEnum.POST_MORTEM_NOTE,
            event_occurred_at=now_utc,
            description=f"Incident officially CLOSED under four-eyes review. Closure Notes: {incident.closure_notes}",
        )

        AuditService.log(
            db=db,
            organization_id=incident.organization_id,
            action="INCIDENT_CLOSED",
            resource_type="security_incident",
            actor_email=cls._get_actor_email(db, closed_by_id),
            actor_id=closed_by_id,
            resource_id=str(incident.id),
            details={"closed_by_id": closed_by_id, "closure_notes": incident.closure_notes},
        )
        return incident

    # ─── 5. APPEND-ONLY TIMELINE ─────────────────────────────────────────────

    @classmethod
    def append_timeline_event(
        cls,
        db: Session,
        incident: SecurityIncident,
        actor_id: int,
        event_type: TimelineEventTypeEnum,
        event_occurred_at: datetime,
        description: str,
        source: TimelineEventSourceEnum = TimelineEventSourceEnum.MANUAL_ENTRY,
    ) -> IncidentTimelineEvent:
        """Appends an immutable timeline event to the incident ledger."""
        now_utc = datetime.now(timezone.utc)
        event = IncidentTimelineEvent(
            organization_id=incident.organization_id,
            incident_id=incident.id,
            event_type=event_type,
            event_occurred_at=event_occurred_at,
            actor_id=actor_id,
            description=description.strip(),
            source=source,
            created_at=now_utc,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        AuditService.log(
            db=db,
            organization_id=incident.organization_id,
            action="INCIDENT_TIMELINE_EVENT_ADDED",
            resource_type="incident_timeline_event",
            actor_email=cls._get_actor_email(db, actor_id),
            actor_id=actor_id,
            resource_id=str(event.id),
            details={"event_type": event_type.value},
        )
        return event

    # ─── 6. CONTROL & VENDOR LINKAGES ────────────────────────────────────────

    @classmethod
    def link_control(
        cls,
        db: Session,
        incident: SecurityIncident,
        organization_control_id: int,
        relationship_type: IncidentControlRelationshipEnum,
        notes: Optional[str] = None,
    ) -> IncidentControlLink:
        """Associates an OrganizationControl to an Incident with strict same-tenant verification."""
        if incident.status == IncidentStatusEnum.CLOSED:
            raise ValueError("Closed incidents are permanently immutable.")

        control = db.query(OrganizationControl).filter(
            OrganizationControl.id == organization_control_id,
            OrganizationControl.organization_id == incident.organization_id,
        ).first()

        if not control:
            raise ValueError(
                f"OrganizationControl ID {organization_control_id} not found in tenant organization {incident.organization_id}."
            )

        existing = db.query(IncidentControlLink).filter(
            IncidentControlLink.organization_id == incident.organization_id,
            IncidentControlLink.incident_id == incident.id,
            IncidentControlLink.organization_control_id == organization_control_id,
        ).first()

        if existing:
            raise ValueError(f"Control #{organization_control_id} is already linked to this incident.")

        link = IncidentControlLink(
            organization_id=incident.organization_id,
            incident_id=incident.id,
            organization_control_id=organization_control_id,
            relationship_type=relationship_type,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
        db.add(link)
        db.commit()
        db.refresh(link)

        AuditService.log(
            db=db,
            organization_id=incident.organization_id,
            action="INCIDENT_CONTROL_LINKED",
            resource_type="incident_control_link",
            actor_email=cls._get_actor_email(db, incident.incident_commander_id),
            actor_id=incident.incident_commander_id,
            resource_id=str(link.id),
            details={"control_id": organization_control_id, "relationship_type": relationship_type.value},
        )
        return link

    @classmethod
    def unlink_control(
        cls,
        db: Session,
        incident: SecurityIncident,
        link_id: int,
    ) -> None:
        """Removes a control association."""
        if incident.status == IncidentStatusEnum.CLOSED:
            raise ValueError("Closed incidents are permanently immutable.")

        link = db.query(IncidentControlLink).filter(
            IncidentControlLink.id == link_id,
            IncidentControlLink.incident_id == incident.id,
            IncidentControlLink.organization_id == incident.organization_id,
        ).first()

        if not link:
            raise ValueError(f"IncidentControlLink #{link_id} not found.")

        db.delete(link)
        db.commit()

    @classmethod
    def link_vendor(
        cls,
        db: Session,
        incident: SecurityIncident,
        vendor_id: int,
        vendor_engagement_id: Optional[int] = None,
        is_vendor_originated: bool = True,
        notes: Optional[str] = None,
    ) -> IncidentVendorLink:
        """Associates a Vendor / VendorEngagement to an Incident with strict same-tenant verification."""
        if incident.status == IncidentStatusEnum.CLOSED:
            raise ValueError("Closed incidents are permanently immutable.")

        vendor = db.query(Vendor).filter(
            Vendor.id == vendor_id,
            Vendor.organization_id == incident.organization_id,
        ).first()

        if not vendor:
            raise ValueError(f"Vendor ID {vendor_id} not found in tenant organization {incident.organization_id}.")

        if vendor_engagement_id:
            engagement = db.query(VendorEngagement).filter(
                VendorEngagement.id == vendor_engagement_id,
                VendorEngagement.vendor_id == vendor_id,
                VendorEngagement.organization_id == incident.organization_id,
            ).first()
            if not engagement:
                raise ValueError(
                    f"VendorEngagement ID {vendor_engagement_id} does not belong to Vendor {vendor_id} in tenant {incident.organization_id}."
                )

        existing = db.query(IncidentVendorLink).filter(
            IncidentVendorLink.organization_id == incident.organization_id,
            IncidentVendorLink.incident_id == incident.id,
            IncidentVendorLink.vendor_id == vendor_id,
            IncidentVendorLink.vendor_engagement_id == vendor_engagement_id,
        ).first()

        if existing:
            raise ValueError("This vendor/engagement is already linked to this incident.")

        link = IncidentVendorLink(
            organization_id=incident.organization_id,
            incident_id=incident.id,
            vendor_id=vendor_id,
            vendor_engagement_id=vendor_engagement_id,
            is_vendor_originated=is_vendor_originated,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
        db.add(link)
        db.commit()
        db.refresh(link)

        AuditService.log(
            db=db,
            organization_id=incident.organization_id,
            action="INCIDENT_VENDOR_LINKED",
            resource_type="incident_vendor_link",
            actor_email=cls._get_actor_email(db, incident.incident_commander_id),
            actor_id=incident.incident_commander_id,
            resource_id=str(link.id),
            details={"vendor_id": vendor_id, "engagement_id": vendor_engagement_id},
        )
        return link

    @classmethod
    def unlink_vendor(
        cls,
        db: Session,
        incident: SecurityIncident,
        link_id: int,
    ) -> None:
        """Removes a vendor association."""
        if incident.status == IncidentStatusEnum.CLOSED:
            raise ValueError("Closed incidents are permanently immutable.")

        link = db.query(IncidentVendorLink).filter(
            IncidentVendorLink.id == link_id,
            IncidentVendorLink.incident_id == incident.id,
            IncidentVendorLink.organization_id == incident.organization_id,
        ).first()

        if not link:
            raise ValueError(f"IncidentVendorLink #{link_id} not found.")

        db.delete(link)
        db.commit()

    # ─── 7. REGULATORY DISCLOSURE MANAGEMENT ─────────────────────────────────

    @classmethod
    def evaluate_regulatory_disclosure(
        cls,
        db: Session,
        incident: SecurityIncident,
        regulator: RegulatorEnum,
        triggered_by_id: Optional[int] = None,
        trigger_type: DisclosureTriggerTypeEnum = DisclosureTriggerTypeEnum.INCIDENT_DETECTION,
        triggered_at: Optional[datetime] = None,
        rule_version: str = "1.0",
    ) -> IncidentRegulatoryDisclosure:
        """Evaluates or updates regulatory disclosure countdown record."""
        trig_at = triggered_at or incident.detected_at
        deadline, r_ver, calc_ver = cls.calculate_regulatory_deadline(
            regulator=regulator,
            triggered_at=trig_at,
            trigger_type=trigger_type,
            rule_version=rule_version,
        )

        existing = db.query(IncidentRegulatoryDisclosure).filter(
            IncidentRegulatoryDisclosure.organization_id == incident.organization_id,
            IncidentRegulatoryDisclosure.incident_id == incident.id,
            IncidentRegulatoryDisclosure.regulator == regulator,
        ).first()

        now_utc = datetime.now(timezone.utc)

        if existing:
            # If already notified or exempt, do not overwrite historical deadline
            if existing.status in [DisclosureStatusEnum.NOTIFIED, DisclosureStatusEnum.NOT_APPLICABLE]:
                return existing

            existing.triggered_at = trig_at
            existing.trigger_type = trigger_type
            existing.triggered_by_id = triggered_by_id
            existing.deadline_at = deadline
            existing.rule_version = r_ver
            existing.calculation_version = calc_ver
            existing.updated_at = now_utc
            db.commit()
            db.refresh(existing)
            return existing

        disclosure = IncidentRegulatoryDisclosure(
            organization_id=incident.organization_id,
            incident_id=incident.id,
            regulator=regulator,
            status=DisclosureStatusEnum.PENDING,
            rule_version=r_ver,
            calculation_version=calc_ver,
            trigger_type=trigger_type,
            triggered_at=trig_at,
            triggered_by_id=triggered_by_id,
            deadline_at=deadline,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(disclosure)
        db.commit()
        db.refresh(disclosure)

        AuditService.log(
            db=db,
            organization_id=incident.organization_id,
            action="INCIDENT_DISCLOSURE_EVALUATED",
            resource_type="incident_regulatory_disclosure",
            actor_email=cls._get_actor_email(db, triggered_by_id or incident.incident_commander_id),
            actor_id=triggered_by_id or incident.incident_commander_id,
            resource_id=str(disclosure.id),
            details={"regulator": regulator.value, "deadline_at": deadline.isoformat()},
        )
        return disclosure

    @classmethod
    def record_disclosure_notification(
        cls,
        db: Session,
        disclosure: IncidentRegulatoryDisclosure,
        notified_by_id: int,
        notification_reference_code: str,
        disclosure_notes: Optional[str] = None,
    ) -> IncidentRegulatoryDisclosure:
        """Records verified regulator notification with formal tracking reference."""
        now_utc = datetime.now(timezone.utc)
        disclosure.status = DisclosureStatusEnum.NOTIFIED
        disclosure.notified_at = now_utc
        disclosure.notified_by_id = notified_by_id
        disclosure.notification_reference_code = notification_reference_code.strip()
        if disclosure_notes:
            disclosure.disclosure_notes = disclosure_notes.strip()

        disclosure.updated_at = now_utc
        db.commit()
        db.refresh(disclosure)

        AuditService.log(
            db=db,
            organization_id=disclosure.organization_id,
            action="INCIDENT_DISCLOSURE_NOTIFIED",
            resource_type="incident_regulatory_disclosure",
            actor_email=cls._get_actor_email(db, notified_by_id),
            actor_id=notified_by_id,
            resource_id=str(disclosure.id),
            details={"reference_code": notification_reference_code},
        )
        return disclosure

    @classmethod
    def exempt_regulatory_disclosure(
        cls,
        db: Session,
        disclosure: IncidentRegulatoryDisclosure,
        user_id: int,
        exemption_reason: str,
    ) -> IncidentRegulatoryDisclosure:
        """Records formal legal exemption justification."""
        if not exemption_reason or len(exemption_reason.strip()) < 10:
            raise ValueError("Mandatory exemption reason (minimum 10 characters) is required.")

        now_utc = datetime.now(timezone.utc)
        disclosure.status = DisclosureStatusEnum.NOT_APPLICABLE
        disclosure.exemption_reason = exemption_reason.strip()
        disclosure.updated_at = now_utc
        db.commit()
        db.refresh(disclosure)

        AuditService.log(
            db=db,
            organization_id=disclosure.organization_id,
            action="INCIDENT_DISCLOSURE_EXEMPTED",
            resource_type="incident_regulatory_disclosure",
            actor_email=cls._get_actor_email(db, user_id),
            actor_id=user_id,
            resource_id=str(disclosure.id),
            details={"exemption_reason": exemption_reason},
        )
        return disclosure

    # ─── 8. DETERMINISTIC TELEMETRY HELPERS ──────────────────────────────────

    @classmethod
    def _ensure_utc(cls, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensures datetime has UTC timezone."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    @classmethod
    def calculate_ttc_hours(cls, incident: SecurityIncident) -> Optional[float]:
        """Calculates Time-To-Contain (TTC) in hours."""
        if not incident.contained_at or not incident.declared_at:
            return None
        c_at = cls._ensure_utc(incident.contained_at)
        d_at = cls._ensure_utc(incident.declared_at)
        delta = c_at - d_at
        return round(max(delta.total_seconds(), 0.0) / 3600.0, 2)

    @classmethod
    def calculate_mttr_hours(cls, incident: SecurityIncident) -> Optional[float]:
        """Calculates Mean Time To Recover (MTTR) in hours."""
        if not incident.recovered_at or not incident.declared_at:
            return None
        r_at = cls._ensure_utc(incident.recovered_at)
        d_at = cls._ensure_utc(incident.declared_at)
        delta = r_at - d_at
        return round(max(delta.total_seconds(), 0.0) / 3600.0, 2)
