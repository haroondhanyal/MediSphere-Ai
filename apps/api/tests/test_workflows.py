from datetime import datetime, timedelta, timezone

from app.main import app
from fastapi.testclient import TestClient
from app.models import AuditLog, Organization, OrganizationMembership, Role, User
from app.security import hash_password
from test_auth import TestingSession

client = TestClient(app)


def sign_in():
    return client.post("/api/v1/auth/login", json={
        "email": "admin@medisphere.local",
        "password": "MediSphere-Demo-2026!",
        "organization_slug": "medisphere-health",
    })


def test_patient_practitioner_appointment_and_encounter_flow():
    assert sign_in().status_code == 200
    patient = client.post("/api/v1/patients", json={
        "given_name": "Amina", "family_name": "Khan", "gender": "female", "birth_date": None,
    })
    assert patient.status_code == 201
    assert patient.json()["mrn"].startswith("NC-")
    practitioner = client.post("/api/v1/practitioners", json={
        "given_name": "Sara", "family_name": "Malik", "specialty": "Family Medicine", "email": "sara@example.test",
    })
    assert practitioner.status_code == 201
    starts = datetime.now(timezone.utc) + timedelta(days=2)
    ends = starts + timedelta(minutes=30)
    booking = {
        "patient_id": patient.json()["id"],
        "practitioner_id": practitioner.json()["id"],
        "starts_at": starts.isoformat(),
        "ends_at": ends.isoformat(),
        "reason": "Annual checkup",
    }
    appointment = client.post("/api/v1/appointments", json=booking)
    assert appointment.status_code == 201
    conflict = client.post("/api/v1/appointments", json={**booking, "patient_id": patient.json()["id"]})
    assert conflict.status_code == 409
    encounter = client.post("/api/v1/encounters", json={
        "patient_id": patient.json()["id"],
        "practitioner_id": practitioner.json()["id"],
        "appointment_id": appointment.json()["id"],
        "diagnosis_summary": "Routine check",
        "note": "Follow-up in one year.",
    })
    assert encounter.status_code == 201
    assert encounter.json()["status"] == "in_progress"


def test_appointment_rejects_unknown_patient_or_practitioner():
    assert sign_in().status_code == 200
    response = client.post("/api/v1/appointments", json={
        "patient_id": 99999,
        "practitioner_id": 99999,
        "starts_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "ends_at": (datetime.now(timezone.utc) + timedelta(days=1, minutes=30)).isoformat(),
    })
    assert response.status_code == 404


def test_prescription_lab_and_radiology_workflows():
    assert sign_in().status_code == 200
    patient = client.post("/api/v1/patients", json={"given_name": "Omar", "family_name": "Raza"}).json()
    practitioner = client.post("/api/v1/practitioners", json={
        "given_name": "Nadia", "family_name": "Ali", "specialty": "Internal Medicine", "email": "nadia@example.test",
    }).json()
    subjects = {"patient_id": patient["id"], "practitioner_id": practitioner["id"]}
    prescription = client.post("/api/v1/prescriptions", json={
        **subjects, "medication_name": "Example medication", "dosage": "10 mg", "frequency": "Once daily",
    })
    assert prescription.status_code == 201
    lab = client.post("/api/v1/lab-orders", json={**subjects, "test_name": "CBC", "priority": "routine"})
    assert lab.status_code == 201
    result = client.patch(f"/api/v1/lab-orders/{lab.json()['id']}/result", json={"summary": "Within expected range"})
    assert result.status_code == 200
    assert result.json()["status"] == "completed"
    imaging = client.post("/api/v1/radiology-orders", json={**subjects, "modality": "X-Ray", "body_region": "Chest"})
    assert imaging.status_code == 201
    report = client.patch(f"/api/v1/radiology-orders/{imaging.json()['id']}/report", json={"summary": "No acute findings"})
    assert report.status_code == 200
    assert report.json()["status"] == "completed"


def test_secure_message_creates_private_notification():
    with TestingSession() as db:
        organization = db.query(Organization).filter_by(slug="medisphere-health").one()
        role = db.query(Role).filter_by(name="doctor").one()
        recipient = User(email="member@medisphere.local", full_name="Care Team Member", password_hash=hash_password("Local-Test-Password!"))
        db.add(recipient)
        db.flush()
        db.add(OrganizationMembership(organization_id=organization.id, user_id=recipient.id, role_id=role.id))
        db.commit()
        recipient_id = recipient.id
    assert sign_in().status_code == 200
    response = client.post("/api/v1/messages", json={"recipient_user_id": recipient_id, "body": "Please review the visit note."})
    assert response.status_code == 201
    assert client.get("/api/v1/messages", params={"with_user_id": recipient_id}).json()[0]["body"] == "Please review the visit note."
    recipient_login = client.post("/api/v1/auth/login", json={
        "email": "member@medisphere.local",
        "password": "Local-Test-Password!",
        "organization_slug": "medisphere-health",
    })
    assert recipient_login.status_code == 200
    notices = client.get("/api/v1/notifications")
    assert notices.status_code == 200
    assert notices.json()[0]["category"] == "message"
    assert client.post(f"/api/v1/notifications/{notices.json()[0]['id']}/read").status_code == 200


def test_coverage_claim_authorization_and_billing_workflow():
    assert sign_in().status_code == 200
    patient = client.post("/api/v1/patients", json={"given_name": "Noor", "family_name": "Hassan"}).json()
    policy = client.post("/api/v1/insurance/policies", json={
        "patient_id": patient["id"], "payer_name": "Prime Health", "member_id": "MEM-1001", "plan_name": "Standard",
    })
    assert policy.status_code == 201
    claim = client.post("/api/v1/claims", json={"patient_id": patient["id"], "payer_name": "Prime Health", "amount_cents": 12500})
    assert claim.status_code == 201
    claim_status = client.patch(f"/api/v1/claims/{claim.json()['id']}/status", json={"status": "submitted"})
    assert claim_status.json()["status"] == "submitted"
    auth = client.post("/api/v1/authorizations", json={
        "patient_id": patient["id"], "payer_name": "Prime Health", "service_name": "MRI",
    })
    assert auth.status_code == 201
    assert client.patch(f"/api/v1/authorizations/{auth.json()['id']}/status", json={"status": "submitted"}).json()["status"] == "submitted"
    invoice = client.post("/api/v1/billing/invoices", json={
        "patient_id": patient["id"], "description": "Consultation", "amount_cents": 5000,
    })
    assert invoice.status_code == 201
    payment = client.post(f"/api/v1/billing/invoices/{invoice.json()['id']}/payments", json={"amount_cents": 2000})
    assert payment.json()["status"] == "partial"
    overpayment = client.post(f"/api/v1/billing/invoices/{invoice.json()['id']}/payments", json={"amount_cents": 4000})
    assert overpayment.status_code == 409


def test_fhir_r4_patient_create_read_and_search():
    assert sign_in().status_code == 200
    resource = {
        "resourceType": "Patient",
        "identifier": [{"system": "https://medisphere.example/fhir/mrn", "value": "FHIR-100"}],
        "name": [{"family": "Iqbal", "given": ["Mina"]}],
        "gender": "female",
        "birthDate": "1992-04-10",
        "telecom": [{"system": "email", "value": "mina@example.test"}],
    }
    created = client.post("/api/v1/fhir/r4/Patient", json=resource)
    assert created.status_code == 201
    assert created.headers["content-type"].startswith("application/fhir+json")
    patient_id = created.json()["id"]
    read = client.get(f"/api/v1/fhir/r4/Patient/{patient_id}")
    assert read.json()["resourceType"] == "Patient"
    search = client.get("/api/v1/fhir/r4/Patient", params={"name": "Iqbal"})
    assert search.json()["type"] == "searchset"
    assert search.json()["total"] == 1


def test_remote_monitoring_records_tenant_scoped_readings():
    assert sign_in().status_code == 200
    patient = client.post("/api/v1/patients", json={"given_name": "Farah", "family_name": "Siddiqui"}).json()
    device = client.post("/api/v1/remote-monitoring/devices", json={
        "patient_id": patient["id"], "display_name": "Home monitor", "device_type": "Blood pressure",
    })
    assert device.status_code == 201
    reading = client.post(f"/api/v1/remote-monitoring/devices/{device.json()['id']}/readings", json={
        "metric": "Systolic pressure", "value": 120, "unit": "mmHg",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    assert reading.status_code == 201
    assert len(client.get(f"/api/v1/remote-monitoring/devices/{device.json()['id']}/readings").json()) == 1


def test_copilot_retrieves_permission_scoped_records_and_audits_without_query_text():
    assert sign_in().status_code == 200
    patient = client.post("/api/v1/patients", json={"given_name": "Zara", "family_name": "Ahmed"}).json()
    response = client.post("/api/v1/ai/copilot", json={"query": "Find patient record Zara Ahmed"})
    assert response.status_code == 200
    assert response.json()["generated"] is False
    assert response.json()["sources"][0]["id"] == patient["id"]

    client.post("/api/v1/auth/login", json={"email": "doctor@medisphere.local", "password": "MediSphere-Demo-2026!", "organization_slug": "medisphere-health"})
    denied = client.post("/api/v1/ai/copilot", json={"query": "Show recent claims"})
    assert denied.status_code == 403

    with TestingSession() as db:
        audit = db.query(AuditLog).filter_by(event="ai.copilot.retrieval").order_by(AuditLog.id.desc()).first()
        assert audit is not None
        assert "query" not in audit.details


def test_fhir_capability_and_read_search_for_care_resources():
    assert sign_in().status_code == 200
    patient = client.post("/api/v1/patients", json={"given_name": "Layla", "family_name": "Noor"}).json()
    practitioner = client.post("/api/v1/practitioners", json={"given_name": "Hina", "family_name": "Khan", "specialty": "Family Medicine", "email": "hina@example.test"}).json()
    starts = datetime.now(timezone.utc) + timedelta(days=1)
    appointment = client.post("/api/v1/appointments", json={"patient_id": patient["id"], "practitioner_id": practitioner["id"], "starts_at": starts.isoformat(), "ends_at": (starts + timedelta(minutes=30)).isoformat(), "reason": "Follow-up"}).json()
    encounter = client.post("/api/v1/encounters", json={"patient_id": patient["id"], "practitioner_id": practitioner["id"], "appointment_id": appointment["id"], "diagnosis_summary": "Routine follow-up", "note": "Review recorded"}).json()

    capability = client.get("/api/v1/fhir/r4/metadata").json()
    supported = {resource["type"] for resource in capability["rest"][0]["resource"]}
    assert {"Patient", "Practitioner", "Appointment", "Encounter"} <= supported
    practitioner_fhir = client.get(f"/api/v1/fhir/r4/Practitioner/{practitioner['id']}").json()
    assert practitioner_fhir["resourceType"] == "Practitioner"
    appointment_search = client.get("/api/v1/fhir/r4/Appointment", params={"patient": f"Patient/{patient['id']}"})
    assert appointment_search.json()["entry"][0]["resource"]["participant"][0]["actor"]["reference"] == f"Patient/{patient['id']}"
    encounter_fhir = client.get(f"/api/v1/fhir/r4/Encounter/{encounter['id']}").json()
    assert encounter_fhir["resourceType"] == "Encounter"
    assert encounter_fhir["appointment"][0]["reference"] == f"Appointment/{appointment['id']}"


def test_pharmacy_dispensing_status_lifecycle():
    assert sign_in().status_code == 200
    patient = client.post("/api/v1/patients", json={"given_name": "Sana", "family_name": "Iqbal"}).json()
    practitioner = client.post("/api/v1/practitioners", json={"given_name": "Adeel", "family_name": "Raza", "specialty": "Family Medicine", "email": "adeel@example.test"}).json()
    prescription = client.post("/api/v1/prescriptions", json={"patient_id": patient["id"], "practitioner_id": practitioner["id"], "medication_name": "Demo medicine", "dosage": "5 mg", "frequency": "Daily"}).json()
    preparing = client.patch(f"/api/v1/pharmacy/prescriptions/{prescription['id']}/status", json={"status": "dispensing"})
    assert preparing.status_code == 200
    dispensed = client.patch(f"/api/v1/pharmacy/prescriptions/{prescription['id']}/status", json={"status": "dispensed"})
    assert dispensed.status_code == 200
    assert dispensed.json()["status"] == "dispensed"
