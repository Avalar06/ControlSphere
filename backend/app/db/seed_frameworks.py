import json
import os
from sqlalchemy.orm import Session
from app.models.framework import (
    Framework,
    FrameworkFunction,
    FrameworkCategory,
    FrameworkSubcategory,
)
from app.models.organization import Organization
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.policy import (
    Policy,
    PolicyVersion,
    PolicyControlMapping,
    PolicyStatusEnum,
    PolicyTypeEnum,
)
from app.models.user import User


def seed_nist_framework(db: Session) -> Framework:
    """Seed the authoritative NIST CSF 2.0 catalog from nist_csf_2_0.json (Idempotent)."""
    json_path = os.path.join(os.path.dirname(__file__), "nist_csf_2_0.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    fw = db.query(Framework).filter(Framework.identifier == data["identifier"]).first()
    if not fw:
        fw = Framework(
            identifier=data["identifier"],
            name=data["name"],
            version=data["version"],
            description=data["description"],
        )
        db.add(fw)
        db.commit()
        db.refresh(fw)

        for fn_data in data["functions"]:
            fn = FrameworkFunction(
                framework_id=fw.id,
                identifier=fn_data["identifier"],
                name=fn_data["name"],
                description=fn_data["description"],
                display_order=fn_data["display_order"],
            )
            db.add(fn)
            db.commit()
            db.refresh(fn)

            for cat_data in fn_data["categories"]:
                cat = FrameworkCategory(
                    function_id=fn.id,
                    identifier=cat_data["identifier"],
                    name=cat_data["name"],
                    description=cat_data["description"],
                    display_order=cat_data["display_order"],
                )
                db.add(cat)
                db.commit()
                db.refresh(cat)

                for sub_data in cat_data["subcategories"]:
                    sub = FrameworkSubcategory(
                        category_id=cat.id,
                        identifier=sub_data["identifier"],
                        title=sub_data["title"],
                        description=sub_data["description"],
                        display_order=sub_data["display_order"],
                    )
                    db.add(sub)
                db.commit()

        print(f"Successfully seeded {fw.name} v{fw.version} catalog.")
    return fw


def seed_demo_organization_controls_and_policies(db: Session) -> None:
    """Seed initial controls, policies, and mappings for the demo organization Apex Financial Services."""
    apex_org = db.query(Organization).filter(Organization.slug == "apex-financial").first()
    if not apex_org:
        return

    admin_user = db.query(User).filter(User.email == "admin@apexfinancial.com").first()
    analyst_user = db.query(User).filter(User.email == "analyst@apexfinancial.com").first()

    # 1. Initialize organization controls if not already seeded
    all_subcategories = db.query(FrameworkSubcategory).all()
    for subcat in all_subcategories:
        existing_ctrl = (
            db.query(OrganizationControl)
            .filter(
                OrganizationControl.organization_id == apex_org.id,
                OrganizationControl.subcategory_id == subcat.id,
            )
            .first()
        )
        if not existing_ctrl:
            status = ImplementationStatusEnum.NOT_STARTED
            priority = PriorityEnum.MEDIUM
            statement = None

            if subcat.identifier in ["GV.OC-01", "GV.PO-01", "PR.AA-01", "PR.AA-02", "PR.DS-01", "DE.CM-01"]:
                status = ImplementationStatusEnum.IMPLEMENTED
                priority = PriorityEnum.HIGH
                statement = f"Fully enforced in accordance with standard enterprise baseline for {subcat.identifier}."
            elif subcat.identifier in ["PR.AA-03", "PR.DS-02", "PR.PS-01", "DE.AE-02", "RS.MA-01"]:
                status = ImplementationStatusEnum.PARTIALLY_IMPLEMENTED
                priority = PriorityEnum.HIGH
                statement = f"Partially implemented; automated validation rollout in progress for {subcat.identifier}."
            elif subcat.identifier in ["GV.RM-01", "PR.AT-01", "ID.RA-01"]:
                status = ImplementationStatusEnum.IN_PROGRESS
                priority = PriorityEnum.MEDIUM
                statement = "Assessment and remediation plan underway."

            ctrl = OrganizationControl(
                organization_id=apex_org.id,
                subcategory_id=subcat.id,
                status=status,
                priority=priority,
                owner_id=analyst_user.id if analyst_user else (admin_user.id if admin_user else None),
                implementation_statement=statement,
            )
            db.add(ctrl)

    db.commit()

    # 2. Seed initial demo policies for Apex Financial
    policies_data = [
        {
            "title": "Access Control & Identity Management Policy",
            "description": "Governs user onboarding, Multi-Factor Authentication (MFA), least privilege access, and quarterly privilege audits.",
            "policy_type": PolicyTypeEnum.ACCESS_CONTROL,
            "status": PolicyStatusEnum.PUBLISHED,
            "content": """# Access Control & Identity Management Policy

## 1. Purpose & Scope
This policy establishes mandatory requirements for managing identity lifecycle, authentication mechanisms, and access privileges across all Apex Financial corporate assets.

## 2. Authentication Requirements
- **Multi-Factor Authentication (MFA)**: MFA is mandatory for all access to internal systems, remote connections, and cloud management consoles.
- **Password Standards**: Passwords must contain a minimum of 14 characters, incorporating upper and lower case letters, numbers, and special characters.

## 3. Privilege Management
- Access privileges are granted strictly based on the principle of **Least Privilege** and role-based access control (RBAC).
- Administrative privileges must be approved by the CISO and audited on a quarterly basis.
- Account access must be revoked within 24 hours of employee departure or contract termination.
""",
            "mapped_subcats": ["PR.AA-01", "PR.AA-02", "PR.AA-03", "PR.AA-04", "PR.AA-05", "GV.PO-01"],
        },
        {
            "title": "Data Protection & Encryption Policy",
            "description": "Defines standards for data classification, cryptographic protections at-rest and in-transit, and data loss prevention.",
            "policy_type": PolicyTypeEnum.DATA_PROTECTION,
            "status": PolicyStatusEnum.PUBLISHED,
            "content": """# Data Protection & Encryption Policy

## 1. Overview
Apex Financial Services classifies all sensitive customer, financial, and proprietary data and mandates robust cryptographic controls.

## 2. Encryption Standards
- **Data at Rest**: All databases, storage volumes, and backups containing sensitive or financial data must be encrypted using AES-256 or stronger.
- **Data in Transit**: All external and internal communications carrying restricted data must employ TLS 1.3.

## 3. Data Retention & Backups
- Immutable backups must be executed daily and tested for integrity quarterly.
""",
            "mapped_subcats": ["PR.DS-01", "PR.DS-02", "PR.DS-10", "PR.DS-11"],
        },
        {
            "title": "Cybersecurity Incident Response Plan",
            "description": "Prescribes incident triage, categorization, containment, eradication, stakeholder communication, and post-incident review procedures.",
            "policy_type": PolicyTypeEnum.INCIDENT_RESPONSE,
            "status": PolicyStatusEnum.APPROVED,
            "content": """# Cybersecurity Incident Response Plan

## 1. Purpose
Provides a structured methodology for detecting, containing, and recovering from cybersecurity incidents affecting Apex Financial Services.

## 2. Incident Classification & Triage
- **Critical (Sev 1)**: Active compromise of customer data or core transaction processing.
- **High (Sev 2)**: Compromise of internal servers or unauthorized privilege escalation.
- **Medium (Sev 3)**: Isolated malware detection on a non-critical endpoint.

## 3. Eradication & Recovery
- All impacted systems must be isolated immediately upon detection.
- Post-incident post-mortem reports must be published within 7 business days of incident closure.
""",
            "mapped_subcats": ["RS.MA-01", "RS.AN-03", "RS.CO-02", "RS.MI-01", "RC.RP-01"],
        },
    ]

    for p_info in policies_data:
        existing_pol = db.query(Policy).filter(Policy.organization_id == apex_org.id, Policy.title == p_info["title"]).first()
        if not existing_pol:
            pol = Policy(
                organization_id=apex_org.id,
                title=p_info["title"],
                description=p_info["description"],
                policy_type=p_info["policy_type"],
                status=p_info["status"],
                owner_id=admin_user.id if admin_user else None,
            )
            db.add(pol)
            db.commit()
            db.refresh(pol)

            ver = PolicyVersion(
                policy_id=pol.id,
                version_number=1,
                content=p_info["content"],
                change_summary="Initial approved baseline release",
                created_by_id=admin_user.id if admin_user else None,
            )
            db.add(ver)

            for subcat_ident in p_info["mapped_subcats"]:
                sub = db.query(FrameworkSubcategory).filter(FrameworkSubcategory.identifier == subcat_ident).first()
                if sub:
                    mapping = PolicyControlMapping(
                        organization_id=apex_org.id,
                        policy_id=pol.id,
                        subcategory_id=sub.id,
                    )
                    db.add(mapping)

            db.commit()


if __name__ == "__main__":
    from app.db.base import SessionLocal
    db = SessionLocal()
    seed_nist_framework(db)
    seed_demo_organization_controls_and_policies(db)
    db.close()