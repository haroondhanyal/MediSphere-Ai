from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.seed import seed

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def override_db():
    with TestingSession() as db:
        yield db


app.dependency_overrides[get_db] = override_db
with TestingSession() as session:
    seed(session)
client = TestClient(app)


def test_login_sets_http_only_cookie_and_me_returns_session():
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@medisphere.local",
        "password": "MediSphere-Demo-2026!",
        "organization_slug": "medisphere-health",
    })
    assert response.status_code == 200
    assert response.json()["role"] == "hospital_admin"
    assert "httponly" in response.headers["set-cookie"].lower()
    assert client.get("/api/v1/auth/me").status_code == 200
    permissions = client.get("/api/v1/auth/permissions")
    assert "patients:read" in permissions.json()["permissions"]
    assert client.get("/api/v1/organizations/current").json()["slug"] == "medisphere-health"


def test_private_routes_require_session():
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401


def test_role_permissions_restrict_patient_creation():
    response = client.post("/api/v1/auth/login", json={
        "email": "doctor@medisphere.local",
        "password": "MediSphere-Demo-2026!",
        "organization_slug": "medisphere-health",
    })
    assert response.status_code == 200
    assert client.get("/api/v1/patients").status_code == 200
    denied = client.post("/api/v1/patients", json={"given_name": "Test", "family_name": "Patient"})
    assert denied.status_code == 403


def test_bad_password_is_rejected():
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@medisphere.local",
        "password": "wrong",
        "organization_slug": "medisphere-health",
    })
    assert response.status_code == 401


def test_logout_clears_session_cookie():
    client.post("/api/v1/auth/login", json={
        "email": "admin@medisphere.local",
        "password": "MediSphere-Demo-2026!",
        "organization_slug": "medisphere-health",
    })
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401
