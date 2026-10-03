from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import User
from app.provision_admin import provision_admin
from test_auth import TestingSession

client = TestClient(app)


def test_configured_monitoring_threshold_creates_auditable_acknowledgeable_alert():
    login = client.post("/api/v1/auth/login", json={
        "email": "admin@medisphere.local",
        "password": "MediSphere-Demo-2026!",
        "organization_slug": "medisphere-health",
    })
    assert login.status_code == 200
    patient = client.post("/api/v1/patients", json={"given_name": "Monitoring", "family_name": "Patient"}).json()
    device = client.post("/api/v1/remote-monitoring/devices", json={
        "patient_id": patient["id"], "display_name": "Home monitor", "device_type": "Blood pressure",
    }).json()
    rule = client.post("/api/v1/remote-monitoring/rules", json={
        "metric": "Systolic pressure", "unit": "mmHg", "maximum": 130,
    })
    assert rule.status_code == 201
    invalid = client.post("/api/v1/remote-monitoring/rules", json={
        "metric": "Invalid range", "unit": "mmHg", "minimum": 130, "maximum": 100,
    })
    assert invalid.status_code == 422
    reading = client.post(f"/api/v1/remote-monitoring/devices/{device['id']}/readings", json={
        "metric": "Systolic pressure", "value": 140, "unit": "mmHg",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    assert reading.status_code == 201
    alerts = client.get("/api/v1/remote-monitoring/alerts")
    assert alerts.status_code == 200
    alert = next(item for item in alerts.json() if item["device_id"] == device["id"])
    assert alert["status"] == "open"
    acknowledged = client.post(f"/api/v1/remote-monitoring/alerts/{alert['id']}/acknowledge")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "acknowledged"


def test_device_token_accepts_remote_readings_and_rotation_revokes_old_token():
    client.post("/api/v1/auth/login", json={
        "email": "admin@medisphere.local",
        "password": "MediSphere-Demo-2026!",
        "organization_slug": "medisphere-health",
    })
    patient = client.post("/api/v1/patients", json={"given_name": "Remote", "family_name": "Reading"}).json()
    device = client.post("/api/v1/remote-monitoring/devices", json={
        "patient_id": patient["id"], "display_name": "Connected monitor", "device_type": "Pulse oximeter",
    }).json()
    payload = {"metric": "Oxygen saturation", "value": 97, "unit": "%", "recorded_at": datetime.now(timezone.utc).isoformat()}
    route = f"/api/v1/remote-monitoring/ingest/{device['id']}/readings"
    assert client.post(route, json=payload).status_code == 401
    accepted = client.post(route, json=payload, headers={"Authorization": f"Bearer {device['ingest_token']}"})
    assert accepted.status_code == 201
    rotated = client.post(f"/api/v1/remote-monitoring/devices/{device['id']}/ingest-token")
    assert rotated.status_code == 200
    rejected = client.post(route, json=payload, headers={"Authorization": f"Bearer {device['ingest_token']}"})
    assert rejected.status_code == 401
    accepted_again = client.post(route, json=payload, headers={"Authorization": f"Bearer {rotated.json()['ingest_token']}"})
    assert accepted_again.status_code == 201


def test_production_bootstrap_creates_only_one_admin_and_is_safe_to_retry():
    with TestingSession() as db:
        users_before = db.query(User).count()
        created = provision_admin(db, "first-admin@medisphere.local", "One-Time-Long-Bootstrap-Secret!")
        assert created.email == "first-admin@medisphere.local"
        assert db.query(User).count() == users_before + 1
        try:
            provision_admin(db, created.email, "One-Time-Long-Bootstrap-Secret!")
        except ValueError as error:
            assert "already exists" in str(error)
        else:
            raise AssertionError("Provisioning the same administrator twice must fail safely")
