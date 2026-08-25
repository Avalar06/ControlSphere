import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.permissions import RoleEnum
from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.seed_frameworks import seed_nist_framework
from app.main import app
from app.models.framework import Framework
from app.models.organization import Organization
from app.models.user import User

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def org_apex(db) -> Organization:
    org = Organization(
        name="Apex Financial Services",
        slug="apex-financial",
        is_active=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture(scope="function")
def org_meridian(db) -> Organization:
    org = Organization(
        name="Meridian Health Systems",
        slug="meridian-health",
        is_active=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture(scope="function")
def admin_user(db, org_apex) -> User:
    user = User(
        email="admin@apexfinancial.com",
        hashed_password=get_password_hash("AdminPassword123!"),
        full_name="Elena Rostova",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def analyst_user(db, org_apex) -> User:
    user = User(
        email="analyst@apexfinancial.com",
        hashed_password=get_password_hash("AnalystPassword123!"),
        full_name="Marcus Chen",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auditor_user(db, org_apex) -> User:
    user = User(
        email="auditor@apexfinancial.com",
        hashed_password=get_password_hash("AuditorPassword123!"),
        full_name="Sarah Jenkins",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def viewer_user(db, org_apex) -> User:
    user = User(
        email="viewer@apexfinancial.com",
        hashed_password=get_password_hash("ViewerPassword123!"),
        full_name="David Sterling",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def meridian_admin_user(db, org_meridian) -> User:
    user = User(
        email="admin@meridianhealth.com",
        hashed_password=get_password_hash("MeridianAdmin123!"),
        full_name="Dr. Amanda Vance",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def seeded_framework(db) -> Framework:
    return seed_nist_framework(db)


def get_token_headers(user: User) -> dict:
    token = create_access_token(
        subject=user.id,
        organization_id=user.organization_id,
        role=user.role.value,
    )
    return {"Authorization": f"Bearer {token}"}