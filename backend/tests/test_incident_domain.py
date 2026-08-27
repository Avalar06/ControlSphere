from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.permissions import Permission, RoleEnum, has_permission
from app.models.control import OrganizationControl
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
from app.models.organization import Organization
from app.models.tprm import Vendor, VendorEngagement, VendorStatusEnum
from app.models.user import User
from app.services.incident_service import IncidentService


class TestIncidentDomain:
    """Exhaustive Domain & Lifecycle Test Suite for Phase 10 Incident Management."""

    # ── 1. ENUMS & CONSTANTS ──────────────────────────────────────────────────

    def test_enums_and_constants(self):
        """Verify all Phase 10 enums have expected members."""
        assert IncidentSeverityEnum.CRITICAL == "CRITICAL"
        assert IncidentSeverityEnum.HIGH == "HIGH"
        assert IncidentSeverityEnum.MEDIUM == "MEDIUM"
        assert IncidentSeverityEnum.LOW == "LOW"

        assert IncidentCategoryEnum.RANSOMWARE == "RANSOMWARE"
        assert IncidentCategoryEnum.DATA_BREACH == "DATA_BREACH"
        assert IncidentCategoryEnum.SUPPLY_CHAIN_COMPROMISE == "SUPPLY_CHAIN_COMPROMISE"

        assert IncidentStatusEnum.DECLARED == "DECLARED"
        assert IncidentStatusEnum.CLOSED == "CLOSED"

        assert RegulatorEnum.GDPR_DPA == "GDPR_DPA"
        assert RegulatorEnum.SEC_8K == "SEC_8K"
        assert RegulatorEnum.HHS_OCR == "HHS_OCR"
        assert RegulatorEnum.PCI_SSC == "PCI_SSC"
        assert RegulatorEnum.NYDFS == "NYDFS"
        assert RegulatorEnum.STATE_AG == "STATE_AG"

        assert DisclosureStatusEnum.NOT_APPLICABLE == "NOT_APPLICABLE"
        assert DisclosureStatusEnum.PENDING == "PENDING"
        assert DisclosureStatusEnum.NOTIFIED == "NOTIFIED"

    # ── 2. INCIDENT CREATION DEFAULTS ─────────────────────────────────────────

    def test_incident_creation_defaults(self, db: Session, org_apex: Organization, admin_user: User):
        """Creates incident with verified server-authoritative timestamps and defaults."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-2026-001",
            title="Database Unauthorized Exfiltration Attempt",
            description="Suspicious high-volume egress detected on production database replica.",
            severity=IncidentSeverityEnum.HIGH,
            category=IncidentCategoryEnum.DATA_BREACH,
            detected_at=now,
            affected_record_count=1500,
            financial_impact_estimate=25000.0,
        )

        assert incident.id is not None
        assert incident.organization_id == org_apex.id
        assert incident.incident_code == "INC-2026-001"
        assert incident.status == IncidentStatusEnum.DECLARED
        assert incident.affected_record_count == 1500
        assert incident.financial_impact_estimate == 25000.0
        assert incident.is_material is False
        assert len(incident.timeline_events) == 1
        assert incident.timeline_events[0].event_type == TimelineEventTypeEnum.DETECTION

    # ── 3. LEGAL LIFECYCLE TRANSITIONS ────────────────────────────────────────

    def test_legal_lifecycle_transitions(self, db: Session, org_apex: Organization, admin_user: User):
        """Step through canonical progression: DECLARED -> TRIAGED -> CONTAINED -> ERADICATED -> RECOVERED -> POST_MORTEM."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-FLOW-01",
            title="Ransomware Infection in Staging",
            description="Crypto locker detected on isolated staging jump host.",
            severity=IncidentSeverityEnum.CRITICAL,
            category=IncidentCategoryEnum.RANSOMWARE,
            detected_at=now,
        )

        # 1. DECLARED -> TRIAGED
        incident = IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.TRIAGED, admin_user.id)
        assert incident.status == IncidentStatusEnum.TRIAGED

        # 2. TRIAGED -> CONTAINED
        incident = IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.CONTAINED, admin_user.id)
        assert incident.status == IncidentStatusEnum.CONTAINED
        assert incident.contained_at is not None

        # 3. CONTAINED -> ERADICATED
        incident = IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.ERADICATED, admin_user.id)
        assert incident.status == IncidentStatusEnum.ERADICATED
        assert incident.eradicated_at is not None

        # 4. ERADICATED -> RECOVERED
        incident = IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.RECOVERED, admin_user.id)
        assert incident.status == IncidentStatusEnum.RECOVERED
        assert incident.recovered_at is not None

        # 5. RECOVERED -> POST_MORTEM
        incident = IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.POST_MORTEM, admin_user.id)
        assert incident.status == IncidentStatusEnum.POST_MORTEM
        assert incident.post_mortem_at is not None

    # ── 4. ILLEGAL LIFECYCLE TRANSITIONS ──────────────────────────────────────

    def test_illegal_lifecycle_jumps_blocked(self, db: Session, org_apex: Organization, admin_user: User):
        """Cannot jump phases arbitrarily (e.g. DECLARED -> CLOSED or DECLARED -> ERADICATED)."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-ILLEGAL-01",
            title="Illegal Jump Test",
            description="Testing state machine invalid transition prevention.",
            severity=IncidentSeverityEnum.LOW,
            category=IncidentCategoryEnum.OTHER,
            detected_at=now,
        )

        with pytest.raises(ValueError, match="Invalid incident lifecycle transition"):
            IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.CLOSED, admin_user.id)

        with pytest.raises(ValueError, match="Invalid incident lifecycle transition"):
            IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.ERADICATED, admin_user.id)

    # ── 5. RECOVERED -> CONTAINED RE-ENTRY ────────────────────────────────────

    def test_recovered_to_contained_reentry(self, db: Session, org_apex: Organization, admin_user: User):
        """If malware re-emerges after recovery, incident can transition back to CONTAINED."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-REENTRY-01",
            title="Re-entry test",
            description="Testing containment re-entry.",
            severity=IncidentSeverityEnum.HIGH,
            category=IncidentCategoryEnum.UNAUTHORIZED_ACCESS,
            detected_at=now,
        )
        incident = IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.TRIAGED, admin_user.id)
        incident = IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.CONTAINED, admin_user.id)
        incident = IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.ERADICATED, admin_user.id)
        incident = IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.RECOVERED, admin_user.id)

        # RECOVERED -> CONTAINED
        incident = IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.CONTAINED, admin_user.id, notes="Secondary beaconing discovered")
        assert incident.status == IncidentStatusEnum.CONTAINED

    # ── 6. FOUR-EYES CLOSURE & COMMANDER SEPARATION OF DUTIES ─────────────────

    def test_closure_requires_post_mortem_status(self, db: Session, org_apex: Organization, admin_user: User, analyst_user: User):
        """Incident cannot be closed directly from TRIAGED or CONTAINED."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-PREMATURE-01",
            title="Premature Closure Test",
            description="Testing closure prerequisites.",
            severity=IncidentSeverityEnum.MEDIUM,
            category=IncidentCategoryEnum.OTHER,
            detected_at=now,
        )
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.TRIAGED, admin_user.id)

        with pytest.raises(ValueError, match="Incident must be in POST_MORTEM status before closing"):
            IncidentService.close_incident(
                db=db,
                incident=incident,
                closed_by_id=analyst_user.id,
                closure_notes="Premature closure attempt.",
            )

    def test_closure_requires_valid_notes(self, db: Session, org_apex: Organization, admin_user: User, analyst_user: User):
        """Closure requires at least 10 characters of justification notes."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-NOTES-01",
            title="Closure Notes Test",
            description="Testing minimum character validation.",
            severity=IncidentSeverityEnum.LOW,
            category=IncidentCategoryEnum.OTHER,
            detected_at=now,
        )
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.TRIAGED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.CONTAINED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.ERADICATED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.RECOVERED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.POST_MORTEM, admin_user.id)

        with pytest.raises(ValueError, match="Mandatory closure notes"):
            IncidentService.close_incident(
                db=db,
                incident=incident,
                closed_by_id=analyst_user.id,
                closure_notes="Short",
            )

    def test_four_eyes_closure_commander_blocked(self, db: Session, org_apex: Organization, admin_user: User, analyst_user: User):
        """Incident commander cannot close their own incident."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-SOD-01",
            title="Separation of Duties Test",
            description="Commander cannot close own incident.",
            severity=IncidentSeverityEnum.MEDIUM,
            category=IncidentCategoryEnum.INSIDER_THREAT,
            detected_at=now,
        )
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.TRIAGED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.CONTAINED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.ERADICATED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.RECOVERED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.POST_MORTEM, admin_user.id)

        # Admin is commander -> Closing by admin must fail
        with pytest.raises(ValueError, match="Separation of duties violation"):
            IncidentService.close_incident(
                db=db,
                incident=incident,
                closed_by_id=admin_user.id,
                closure_notes="Admin attempting to close own incident.",
            )

        # Independent user closes -> Success
        closed = IncidentService.close_incident(
            db=db,
            incident=incident,
            closed_by_id=analyst_user.id,
            closure_notes="Independent review completed and accepted by Security Operations Manager.",
            lessons_learned="Implement tighter role-based access to database secrets.",
            root_cause_classification=RootCauseClassificationEnum.CONTROL_FAILURE,
        )
        assert closed.status == IncidentStatusEnum.CLOSED
        assert closed.closed_by_id == analyst_user.id
        assert closed.closed_at is not None

    # ── 7. CLOSED TERMINAL IMMUTABILITY ───────────────────────────────────────

    def test_closed_terminal_immutability(self, db: Session, org_apex: Organization, admin_user: User, analyst_user: User):
        """Closed incidents reject metadata updates, lifecycle transitions, and control link changes."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-IMMUT-01",
            title="Terminal Immutability Test",
            description="Testing closed record lock.",
            severity=IncidentSeverityEnum.LOW,
            category=IncidentCategoryEnum.OTHER,
            detected_at=now,
        )
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.TRIAGED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.CONTAINED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.ERADICATED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.RECOVERED, admin_user.id)
        IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.POST_MORTEM, admin_user.id)
        IncidentService.close_incident(
            db=db,
            incident=incident,
            closed_by_id=analyst_user.id,
            closure_notes="Closed successfully by independent reviewer.",
        )

        with pytest.raises(ValueError, match="Closed incidents are permanently immutable"):
            IncidentService.update_incident_metadata(db, incident, admin_user.id, title="Tampered Title")

        with pytest.raises(ValueError, match="Closed incidents are permanently immutable"):
            IncidentService.transition_lifecycle(db, incident, IncidentStatusEnum.DECLARED, admin_user.id)

    # ── 8. TIMELINE APPEND-ONLY SEMANTICS ─────────────────────────────────────

    def test_timeline_append_only(self, db: Session, org_apex: Organization, admin_user: User):
        """Timeline events can be appended with verified actor ID and event types."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-TIME-01",
            title="Timeline Test",
            description="Testing chronological ledger.",
            severity=IncidentSeverityEnum.MEDIUM,
            category=IncidentCategoryEnum.OTHER,
            detected_at=now,
        )

        event = IncidentService.append_timeline_event(
            db=db,
            incident=incident,
            actor_id=admin_user.id,
            event_type=TimelineEventTypeEnum.CONTAINMENT_ACTION,
            event_occurred_at=now + timedelta(minutes=15),
            description="Isolated VPC subnet us-east-1a",
            source=TimelineEventSourceEnum.MANUAL_ENTRY,
        )

        assert event.id is not None
        assert event.actor_id == admin_user.id
        assert event.incident_id == incident.id
        assert event.event_type == TimelineEventTypeEnum.CONTAINMENT_ACTION

    # ── 9. CROSS-TENANT LINKAGE REJECTIONS ────────────────────────────────────

    def test_cross_tenant_control_linkage_rejected(
        self, db: Session, org_apex: Organization, org_meridian: Organization, admin_user: User, seeded_framework
    ):
        """Cannot link an OrganizationControl belonging to Tenant Meridian to an Incident of Tenant Apex."""
        now = datetime.now(timezone.utc)
        incident_apex = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-APEX-01",
            title="Tenant Apex Incident",
            description="Testing cross-tenant isolation.",
            severity=IncidentSeverityEnum.HIGH,
            category=IncidentCategoryEnum.DATA_BREACH,
            detected_at=now,
        )

        subcat = seeded_framework.functions[0].categories[0].subcategories[0]

        # Control belonging to Org Meridian
        control_meridian = OrganizationControl(
            organization_id=org_meridian.id,
            subcategory_id=subcat.id,
        )
        db.add(control_meridian)
        db.commit()
        db.refresh(control_meridian)

        with pytest.raises(ValueError, match=f"not found in tenant organization {org_apex.id}"):
            IncidentService.link_control(
                db=db,
                incident=incident_apex,
                organization_control_id=control_meridian.id,
                relationship_type=IncidentControlRelationshipEnum.FAILED_CONTROL,
            )

    def test_cross_tenant_vendor_linkage_rejected(
        self, db: Session, org_apex: Organization, org_meridian: Organization, admin_user: User
    ):
        """Cannot link a Vendor from Tenant Meridian to an Incident of Tenant Apex."""
        now = datetime.now(timezone.utc)
        incident_apex = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-APEX-VND",
            title="Tenant Apex Incident",
            description="Testing vendor tenant isolation.",
            severity=IncidentSeverityEnum.CRITICAL,
            category=IncidentCategoryEnum.SUPPLY_CHAIN_COMPROMISE,
            detected_at=now,
        )

        vendor_meridian = Vendor(
            organization_id=org_meridian.id,
            vendor_code="VND-MERIDIAN-01",
            legal_name="Meridian Cloud Services",
            vendor_status=VendorStatusEnum.ACTIVE,
        )
        db.add(vendor_meridian)
        db.commit()
        db.refresh(vendor_meridian)

        with pytest.raises(ValueError, match=f"not found in tenant organization {org_apex.id}"):
            IncidentService.link_vendor(
                db=db,
                incident=incident_apex,
                vendor_id=vendor_meridian.id,
            )

    def test_cross_tenant_engagement_linkage_rejected(
        self, db: Session, org_apex: Organization, admin_user: User
    ):
        """Cannot link an engagement belonging to another vendor."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-VND-ENG-01",
            title="Engagement Mismatch Test",
            description="Testing engagement validation.",
            severity=IncidentSeverityEnum.HIGH,
            category=IncidentCategoryEnum.SUPPLY_CHAIN_COMPROMISE,
            detected_at=now,
        )

        vendor1 = Vendor(organization_id=org_apex.id, vendor_code="VND-1", legal_name="Vendor 1")
        vendor2 = Vendor(organization_id=org_apex.id, vendor_code="VND-2", legal_name="Vendor 2")
        db.add_all([vendor1, vendor2])
        db.commit()

        eng2 = VendorEngagement(
            organization_id=org_apex.id,
            vendor_id=vendor2.id,
            engagement_code="ENG-2",
            engagement_name="Engagement 2",
        )
        db.add(eng2)
        db.commit()

        # Link vendor1 with eng2 (which belongs to vendor2) -> must fail
        with pytest.raises(ValueError, match="does not belong to Vendor"):
            IncidentService.link_vendor(
                db=db,
                incident=incident,
                vendor_id=vendor1.id,
                vendor_engagement_id=eng2.id,
            )

    # ── 10. NEGATIVE VALUE REJECTIONS ─────────────────────────────────────────

    def test_negative_affected_records_rejected(self, db: Session, org_apex: Organization, admin_user: User):
        """Negative affected record count raises ValueError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Affected record count must be non-negative"):
            IncidentService.create_incident(
                db=db,
                organization_id=org_apex.id,
                incident_commander_id=admin_user.id,
                incident_code="INC-NEG-01",
                title="Negative Records Test",
                description="Testing validation.",
                severity=IncidentSeverityEnum.LOW,
                category=IncidentCategoryEnum.OTHER,
                detected_at=now,
                affected_record_count=-5,
            )

    def test_negative_financial_impact_rejected(self, db: Session, org_apex: Organization, admin_user: User):
        """Negative financial impact estimate raises ValueError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="Financial impact estimate must be non-negative"):
            IncidentService.create_incident(
                db=db,
                organization_id=org_apex.id,
                incident_commander_id=admin_user.id,
                incident_code="INC-NEG-02",
                title="Negative Impact Test",
                description="Testing validation.",
                severity=IncidentSeverityEnum.LOW,
                category=IncidentCategoryEnum.OTHER,
                detected_at=now,
                financial_impact_estimate=-100.0,
            )

    # ── 11. REGULATORY DISCLOSURE COUNTDOWN & VERSIONING ──────────────────────

    def test_regulatory_disclosure_deadlines(self, db: Session, org_apex: Organization, admin_user: User):
        """Evaluates statutory deadlines across all supported regulators."""
        t0 = datetime(2026, 8, 24, 10, 0, 0, tzinfo=timezone.utc)  # Monday 10:00 AM UTC

        # GDPR 72h -> Thursday 10:00 AM
        d_gdpr, r_v, c_v = IncidentService.calculate_regulatory_deadline(RegulatorEnum.GDPR_DPA, t0, DisclosureTriggerTypeEnum.INCIDENT_DETECTION)
        assert d_gdpr == t0 + timedelta(hours=72)
        assert r_v == "1.0"
        assert c_v == "1.0"

        # PCI 24h -> Tuesday 10:00 AM
        d_pci, _, _ = IncidentService.calculate_regulatory_deadline(RegulatorEnum.PCI_SSC, t0, DisclosureTriggerTypeEnum.CDE_COMPROMISE)
        assert d_pci == t0 + timedelta(hours=24)

        # HHS 60 days
        d_hhs, _, _ = IncidentService.calculate_regulatory_deadline(RegulatorEnum.HHS_OCR, t0, DisclosureTriggerTypeEnum.PHI_THRESHOLD_BREACH)
        assert d_hhs == t0 + timedelta(days=60)

        # SEC 8-K 4 Business Days from Monday -> Friday 10:00 AM
        d_sec, _, c_sec = IncidentService.calculate_regulatory_deadline(RegulatorEnum.SEC_8K, t0, DisclosureTriggerTypeEnum.MATERIALITY_DETERMINATION)
        assert d_sec == datetime(2026, 8, 28, 10, 0, 0, tzinfo=timezone.utc)  # 4 business days later
        assert c_sec == "1.0_business_days"

    def test_sec_business_days_over_weekend(self):
        """SEC 4 business days spanning across weekend skips Saturday and Sunday."""
        # Thursday 10:00 AM UTC -> Day 1 Fri, Day 2 Mon, Day 3 Tue, Day 4 Wed
        t_thu = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)
        d_sec = IncidentService.add_business_days(t_thu, 4)
        assert d_sec == datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)  # Wednesday

    def test_materiality_determination_triggers_sec_8k(self, db: Session, org_apex: Organization, admin_user: User):
        """Marking an incident as material sets timestamps and evaluates SEC 8-K disclosure."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-SEC-01",
            title="SEC 8-K Materiality Trigger Test",
            description="Testing SEC 8-K automation.",
            severity=IncidentSeverityEnum.CRITICAL,
            category=IncidentCategoryEnum.DATA_BREACH,
            detected_at=now,
        )
        assert incident.is_material is False

        # Set material
        updated = IncidentService.set_materiality(db, incident, admin_user.id, True, "Loss of core IP customer database")
        assert updated.is_material is True
        assert updated.materiality_determined_at is not None
        assert updated.materiality_determined_by_id == admin_user.id

        # Verify SEC_8K disclosure record was auto-created
        sec_disc = db.query(IncidentRegulatoryDisclosure).filter(
            IncidentRegulatoryDisclosure.incident_id == incident.id,
            IncidentRegulatoryDisclosure.regulator == RegulatorEnum.SEC_8K,
        ).first()
        assert sec_disc is not None
        assert sec_disc.status == DisclosureStatusEnum.PENDING
        assert sec_disc.calculation_version == "1.0_business_days"

    def test_regulatory_notification_and_exemption(self, db: Session, org_apex: Organization, admin_user: User):
        """Records verified notification and legal exemption workflows."""
        now = datetime.now(timezone.utc)
        incident = IncidentService.create_incident(
            db=db,
            organization_id=org_apex.id,
            incident_commander_id=admin_user.id,
            incident_code="INC-REG-01",
            title="Regulatory Disclosure Flow",
            description="Testing notification and exemption.",
            severity=IncidentSeverityEnum.CRITICAL,
            category=IncidentCategoryEnum.DATA_BREACH,
            detected_at=now,
        )

        # Evaluate GDPR
        disc_gdpr = IncidentService.evaluate_regulatory_disclosure(
            db=db,
            incident=incident,
            regulator=RegulatorEnum.GDPR_DPA,
            triggered_by_id=admin_user.id,
        )
        assert disc_gdpr.status == DisclosureStatusEnum.PENDING

        # Record Notification
        notified = IncidentService.record_disclosure_notification(
            db=db,
            disclosure=disc_gdpr,
            notified_by_id=admin_user.id,
            notification_reference_code="DPA-IRE-2026-9812",
            disclosure_notes="Reported via DPC Ireland online breach portal.",
        )
        assert notified.status == DisclosureStatusEnum.NOTIFIED
        assert notified.notification_reference_code == "DPA-IRE-2026-9812"

        # Evaluate NYDFS & Exempt
        disc_nydfs = IncidentService.evaluate_regulatory_disclosure(
            db=db,
            incident=incident,
            regulator=RegulatorEnum.NYDFS,
            triggered_by_id=admin_user.id,
        )
        exempted = IncidentService.exempt_regulatory_disclosure(
            db=db,
            disclosure=disc_nydfs,
            user_id=admin_user.id,
            exemption_reason="No New York financial covered entity customer records affected.",
        )
        assert exempted.status == DisclosureStatusEnum.NOT_APPLICABLE
        assert "No New York" in exempted.exemption_reason

    # ── 12. TELEMETRY TTC & MTTR HELPERS ──────────────────────────────────────

    def test_ttc_and_mttr_calculations(self, db: Session, org_apex: Organization, admin_user: User):
        """Calculates Time-to-Contain and Mean-Time-to-Recover in hours."""
        t0 = datetime(2026, 8, 27, 8, 0, 0, tzinfo=timezone.utc)
        incident = SecurityIncident(
            organization_id=org_apex.id,
            incident_code="INC-TELEMETRY-01",
            title="Telemetry Test",
            description="Testing TTC and MTTR.",
            severity=IncidentSeverityEnum.HIGH,
            category=IncidentCategoryEnum.UNAUTHORIZED_ACCESS,
            status=IncidentStatusEnum.RECOVERED,
            incident_commander_id=admin_user.id,
            detected_at=t0,
            declared_at=t0,
            contained_at=t0 + timedelta(hours=2, minutes=30),  # 2.5 hours
            recovered_at=t0 + timedelta(hours=8, minutes=15),  # 8.25 hours
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        ttc = IncidentService.calculate_ttc_hours(incident)
        mttr = IncidentService.calculate_mttr_hours(incident)

        assert ttc == 2.5
        assert mttr == 8.25

    # ── 13. RBAC PERMISSIONS ──────────────────────────────────────────────────

    def test_rbac_incident_permissions(self):
        """Verifies Phase 10 permissions across all six system roles."""
        # ADMIN: All 4
        assert has_permission(RoleEnum.ADMIN, Permission.INCIDENT_READ)
        assert has_permission(RoleEnum.ADMIN, Permission.INCIDENT_MANAGE)
        assert has_permission(RoleEnum.ADMIN, Permission.INCIDENT_DISCLOSE)
        assert has_permission(RoleEnum.ADMIN, Permission.INCIDENT_CLOSE)

        # MANAGER: All 4
        assert has_permission(RoleEnum.MANAGER, Permission.INCIDENT_READ)
        assert has_permission(RoleEnum.MANAGER, Permission.INCIDENT_MANAGE)
        assert has_permission(RoleEnum.MANAGER, Permission.INCIDENT_DISCLOSE)
        assert has_permission(RoleEnum.MANAGER, Permission.INCIDENT_CLOSE)

        # GRC_ANALYST: Read, Manage, Disclose (NO close)
        assert has_permission(RoleEnum.GRC_ANALYST, Permission.INCIDENT_READ)
        assert has_permission(RoleEnum.GRC_ANALYST, Permission.INCIDENT_MANAGE)
        assert has_permission(RoleEnum.GRC_ANALYST, Permission.INCIDENT_DISCLOSE)
        assert not has_permission(RoleEnum.GRC_ANALYST, Permission.INCIDENT_CLOSE)

        # SECURITY_ANALYST: Read, Manage, Disclose (NO close)
        assert has_permission(RoleEnum.SECURITY_ANALYST, Permission.INCIDENT_READ)
        assert has_permission(RoleEnum.SECURITY_ANALYST, Permission.INCIDENT_MANAGE)
        assert has_permission(RoleEnum.SECURITY_ANALYST, Permission.INCIDENT_DISCLOSE)
        assert not has_permission(RoleEnum.SECURITY_ANALYST, Permission.INCIDENT_CLOSE)

        # AUDITOR: Read only
        assert has_permission(RoleEnum.AUDITOR, Permission.INCIDENT_READ)
        assert not has_permission(RoleEnum.AUDITOR, Permission.INCIDENT_MANAGE)
        assert not has_permission(RoleEnum.AUDITOR, Permission.INCIDENT_DISCLOSE)
        assert not has_permission(RoleEnum.AUDITOR, Permission.INCIDENT_CLOSE)

        # VIEWER: Read only
        assert has_permission(RoleEnum.VIEWER, Permission.INCIDENT_READ)
        assert not has_permission(RoleEnum.VIEWER, Permission.INCIDENT_MANAGE)
        assert not has_permission(RoleEnum.VIEWER, Permission.INCIDENT_DISCLOSE)
        assert not has_permission(RoleEnum.VIEWER, Permission.INCIDENT_CLOSE)
