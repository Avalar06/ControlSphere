from sqlalchemy.orm import Session
from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.services.audit_service import AuditService
from app.db.seed_frameworks import seed_nist_framework, seed_demo_organization_controls_and_policies


def init_db(db: Session) -> None:
    # 1. Check if Apex Financial Services organization exists
    apex_org = db.query(Organization).filter(Organization.slug == "apex-financial").first()
    if not apex_org:
        apex_org = Organization(
            name="Apex Financial Services",
            slug="apex-financial",
            is_active=True,
        )
        db.add(apex_org)
        db.commit()
        db.refresh(apex_org)
        print(f"Created organization: {apex_org.name} (ID: {apex_org.id})")

    # Seed users for Apex Financial Services
    users_data = [
        {
            "email": "admin@apexfinancial.com",
            "password": "AdminPassword123!",
            "full_name": "Elena Rostova (Apex Admin)",
            "role": RoleEnum.ADMIN,
        },
        {
            "email": "analyst@apexfinancial.com",
            "password": "AnalystPassword123!",
            "full_name": "Marcus Chen (Lead GRC Analyst)",
            "role": RoleEnum.GRC_ANALYST,
        },
        {
            "email": "auditor@apexfinancial.com",
            "password": "AuditorPassword123!",
            "full_name": "Sarah Jenkins (Senior Auditor)",
            "role": RoleEnum.AUDITOR,
        },
        {
            "email": "viewer@apexfinancial.com",
            "password": "ViewerPassword123!",
            "full_name": "David Sterling (Executive Stakeholder)",
            "role": RoleEnum.VIEWER,
        },
    ]

    for user_info in users_data:
        existing_user = db.query(User).filter(User.email == user_info["email"]).first()
        if not existing_user:
            user = User(
                email=user_info["email"],
                hashed_password=get_password_hash(user_info["password"]),
                full_name=user_info["full_name"],
                role=user_info["role"],
                is_active=True,
                organization_id=apex_org.id,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Audit record for user initialization
            AuditService.log(
                db=db,
                organization_id=apex_org.id,
                actor_id=user.id,
                actor_email="system@controlsphere.internal",
                action="system.seed.user",
                resource_type="USER",
                resource_id=str(user.id),
                status="SUCCESS",
                details={"seeded_user": user.email, "role": user.role.value},
            )
            print(f"Created seeded user: {user.email} [{user.role.value}]")

    # 2. Seed a second tenant for Tenant Isolation testing / verification
    meridian_org = db.query(Organization).filter(Organization.slug == "meridian-health").first()
    if not meridian_org:
        meridian_org = Organization(
            name="Meridian Health Systems",
            slug="meridian-health",
            is_active=True,
        )
        db.add(meridian_org)
        db.commit()
        db.refresh(meridian_org)
        print(f"Created secondary test organization: {meridian_org.name} (ID: {meridian_org.id})")

    meridian_admin = db.query(User).filter(User.email == "admin@meridianhealth.com").first()
    if not meridian_admin:
        meridian_user = User(
            email="admin@meridianhealth.com",
            hashed_password=get_password_hash("MeridianAdmin123!"),
            full_name="Dr. Amanda Vance (Meridian Admin)",
            role=RoleEnum.ADMIN,
            is_active=True,
            organization_id=meridian_org.id,
        )
        db.add(meridian_user)
        db.commit()
        db.refresh(meridian_user)
        print(f"Created secondary tenant admin: {meridian_user.email}")

    # 3. Seed NIST CSF 2.0 Global Catalog
    seed_nist_framework(db)

    # 4. Seed initial controls & policies for Apex Financial
    seed_demo_organization_controls_and_policies(db)


if __name__ == "__main__":
    from app.db.base import SessionLocal
    db = SessionLocal()
    init_db(db)
    db.close()