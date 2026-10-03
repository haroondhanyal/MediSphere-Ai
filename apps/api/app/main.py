from fastapi import Depends, FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from datetime import datetime, timezone
import secrets
from datetime import date
import json
import logging
import time
import hashlib
from collections import defaultdict
from threading import Lock
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_context, require_permission
from app.models import Appointment, AuditLog, ChatMessage, Claim, Device, DeviceReading, Encounter, InsurancePolicy, Invoice, LabOrder, MonitoringAlert, MonitoringRule, Notification, Organization, OrganizationMembership, Patient, Payment, Practitioner, Prescription, PriorAuthorization, RadiologyOrder, User, VideoSession
from app.schemas import AppointmentCreate, AppointmentResponse, AuthorizationCreate, ClaimCreate, CopilotRequest, DeviceCreate, DeviceReadingCreate, EncounterCreate, EncounterResponse, InsurancePolicyCreate, InvoiceCreate, LabOrderCreate, LabOrderResponse, LoginRequest, MessageCreate, MonitoringRuleCreate, NotificationCreate, OrderResultUpdate, OrganizationProfileUpdate, PatientCreate, PatientResponse, PaymentCreate, PractitionerBatchCreate, PractitionerCreate, PractitionerResponse, PrescriptionCreate, PrescriptionResponse, RadiologyOrderCreate, RadiologyOrderResponse, SessionResponse, StatusUpdate, UserResponse
from app.security import create_access_token, verify_password

app = FastAPI(title="MediSphere AI API", version="1.0.0", openapi_url="/api/v1/openapi.json")
if settings.environment.lower() == "production":
    if settings.jwt_secret == "local-development-secret-change-before-deployment" or len(settings.jwt_secret) < 32:
        raise RuntimeError("Production requires a unique JWT_SECRET with at least 32 characters")
    if not settings.cookie_secure or not settings.allowed_origins or "*" in settings.allowed_origins:
        raise RuntimeError("Production requires secure cookies and explicit CORS_ORIGINS")
    if not settings.database_url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Production requires PostgreSQL via the psycopg driver")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)
_duration_buckets = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
_http_metrics: dict[tuple[str, str, int], list[float]] = defaultdict(lambda: [0, 0.0] + [0] * len(_duration_buckets))
_metrics_lock = Lock()
_http_logger = logging.getLogger("medisphere.http")


@app.middleware("http")
async def request_telemetry(request: Request, call_next):
    request_id = str(uuid4())
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = time.perf_counter() - started
        _http_logger.error(json.dumps({"request_id": request_id, "method": request.method, "status": 500, "duration_seconds": round(elapsed, 6)}))
        raise
    elapsed = time.perf_counter() - started
    response.headers["X-Request-ID"] = request_id
    route = getattr(request.scope.get("route"), "path", "unmatched")
    with _metrics_lock:
        values = _http_metrics[(request.method, route, response.status_code)]
        values[0] += 1
        values[1] += elapsed
        for index, boundary in enumerate(_duration_buckets):
            if elapsed <= boundary:
                for bucket_index in range(index, len(_duration_buckets)):
                    values[2 + bucket_index] += 1
    _http_logger.info(json.dumps({"request_id": request_id, "method": request.method, "path": route, "status": response.status_code, "duration_seconds": round(elapsed, 6)}))
    return response


@app.get("/metrics", include_in_schema=False)
def metrics():
    with _metrics_lock:
        rows = [(key, value[:]) for key, value in _http_metrics.items()]
    output = ["# HELP medisphere_http_requests_total HTTP responses by route and status", "# TYPE medisphere_http_requests_total counter",
              "# HELP medisphere_http_request_duration_seconds HTTP response latency", "# TYPE medisphere_http_request_duration_seconds histogram"]
    for (method, route, status), values in rows:
        count, duration = values[:2]
        labels = f'method="{method}",route="{route}",status="{status}"'
        output.append(f"medisphere_http_requests_total{{{labels}}} {count}")
        for index, boundary in enumerate(_duration_buckets):
            output.append(f'medisphere_http_request_duration_seconds_bucket{{{labels},le="{boundary:g}"}} {values[2 + index]}')
        output.append(f'medisphere_http_request_duration_seconds_bucket{{{labels},le="+Inf"}} {count}')
        output.append(f"medisphere_http_request_duration_seconds_sum{{{labels}}} {duration:.9f}")
        output.append(f"medisphere_http_request_duration_seconds_count{{{labels}}} {count}")
    return Response(content="\n".join(output) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/api/v1/health/live")
def liveness():
    return {"status": "ok"}


@app.get("/api/v1/health/ready")
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready", "database": "ok"}


def to_fhir_patient(patient: Patient) -> dict:
    gender = patient.gender.lower()
    if gender not in {"male", "female", "other", "unknown"}:
        gender = "unknown"
    resource = {
        "resourceType": "Patient",
        "id": str(patient.id),
        "identifier": [{"system": "https://medisphere.example/fhir/mrn", "value": patient.mrn}],
        "active": patient.status == "active",
        "name": [{"use": "official", "family": patient.family_name, "given": [patient.given_name]}],
        "gender": gender,
    }
    if patient.birth_date:
        resource["birthDate"] = patient.birth_date.isoformat()
    telecom = []
    if patient.phone:
        telecom.append({"system": "phone", "value": patient.phone})
    if patient.email:
        telecom.append({"system": "email", "value": patient.email})
    if telecom:
        resource["telecom"] = telecom
    return resource


def to_fhir_practitioner(practitioner: Practitioner) -> dict:
    resource = {"resourceType": "Practitioner", "id": str(practitioner.id), "active": practitioner.status == "active",
                "name": [{"use": "official", "family": practitioner.family_name, "given": [practitioner.given_name]}],
                "qualification": [{"code": {"text": practitioner.specialty}}]}
    if practitioner.email:
        resource["telecom"] = [{"system": "email", "value": practitioner.email, "use": "work"}]
    return resource


def to_fhir_appointment(appointment: Appointment) -> dict:
    status_map = {"scheduled": "booked", "completed": "fulfilled", "cancelled": "cancelled", "no_show": "noshow"}
    starts_at = appointment.starts_at if appointment.starts_at.tzinfo else appointment.starts_at.replace(tzinfo=timezone.utc)
    ends_at = appointment.ends_at if appointment.ends_at.tzinfo else appointment.ends_at.replace(tzinfo=timezone.utc)
    return {"resourceType": "Appointment", "id": str(appointment.id), "status": status_map.get(appointment.status, "proposed"),
            **({"description": appointment.reason} if appointment.reason else {}), "start": starts_at.isoformat(), "end": ends_at.isoformat(),
            "participant": [{"actor": {"reference": f"Patient/{appointment.patient_id}"}, "status": "accepted"},
                           {"actor": {"reference": f"Practitioner/{appointment.practitioner_id}"}, "status": "accepted"}]}


def to_fhir_encounter(encounter: Encounter) -> dict:
    status_map = {"in_progress": "in-progress", "completed": "finished", "cancelled": "cancelled"}
    resource = {"resourceType": "Encounter", "id": str(encounter.id), "status": status_map.get(encounter.status, "unknown"),
                "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB", "display": "ambulatory"},
                "subject": {"reference": f"Patient/{encounter.patient_id}"},
                "participant": [{"individual": {"reference": f"Practitioner/{encounter.practitioner_id}"}}]}
    if encounter.diagnosis_summary:
        resource["reasonCode"] = [{"text": encounter.diagnosis_summary}]
    if encounter.note:
        resource["note"] = [{"text": encounter.note}]
    if encounter.appointment_id:
        resource["appointment"] = [{"reference": f"Appointment/{encounter.appointment_id}"}]
    return resource


@app.get("/api/v1/fhir/r4/Patient/{patient_id}")
def fhir_read_patient(patient_id: int, context=Depends(require_permission("patients:read")), db: Session = Depends(get_db)):
    user, membership = context
    patient = db.query(Patient).filter_by(id=patient_id, organization_id=membership.organization_id, status="active").first()
    if not patient:
        raise HTTPException(status_code=404, detail="FHIR Patient not found")
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="fhir.patient.read", resource_type="patient", resource_id=str(patient.id), details={"version": "R4"}))
    db.commit()
    return Response(content=json.dumps(to_fhir_patient(patient)), media_type="application/fhir+json")


@app.get("/api/v1/fhir/r4/metadata")
def fhir_capability_statement():
    """Publish the supported, authenticated FHIR R4 Patient interactions."""
    statement = {
        "resourceType": "CapabilityStatement", "status": "active", "date": date.today().isoformat(),
        "kind": "instance", "fhirVersion": "4.0.1", "format": ["application/fhir+json", "application/json"],
        "rest": [{"mode": "server", "security": {"description": "Use the MediSphere authenticated session."},
            "resource": [
                {"type": "Patient", "interaction": [{"code": "read"}, {"code": "search-type"}, {"code": "create"}], "searchParam": [{"name": "name", "type": "string"}]},
                {"type": "Practitioner", "interaction": [{"code": "read"}, {"code": "search-type"}], "searchParam": [{"name": "name", "type": "string"}]},
                {"type": "Appointment", "interaction": [{"code": "read"}, {"code": "search-type"}], "searchParam": [{"name": "patient", "type": "reference"}]},
                {"type": "Encounter", "interaction": [{"code": "read"}, {"code": "search-type"}], "searchParam": [{"name": "patient", "type": "reference"}]},
            ]}]
    }
    return Response(content=json.dumps(statement), media_type="application/fhir+json")


@app.get("/api/v1/fhir/r4/Patient")
def fhir_search_patients(name: str | None = None, context=Depends(require_permission("patients:read")), db: Session = Depends(get_db)):
    user, membership = context
    query = db.query(Patient).filter_by(organization_id=membership.organization_id, status="active")
    if name:
        term = "%" + name.strip() + "%"
        query = query.filter((Patient.given_name.ilike(term)) | (Patient.family_name.ilike(term)))
    rows = query.order_by(Patient.family_name, Patient.given_name).limit(100).all()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="fhir.patient.search", details={"count": len(rows), "version": "R4"}))
    db.commit()
    bundle = {
        "resourceType": "Bundle", "type": "searchset", "total": len(rows),
        "entry": [{"fullUrl": "https://medisphere.example/fhir/Patient/" + str(row.id), "resource": to_fhir_patient(row)} for row in rows],
    }
    return Response(content=json.dumps(bundle), media_type="application/fhir+json")


def fhir_search_bundle(resource_type: str, rows: list, mapper) -> dict:
    return {"resourceType": "Bundle", "type": "searchset", "total": len(rows),
            "entry": [{"fullUrl": f"https://medisphere.example/fhir/{resource_type}/{row.id}", "resource": mapper(row)} for row in rows]}


def record_fhir_access(db: Session, user: User, organization_id: int, interaction: str, resource_type: str, resource_id: str | None = None):
    db.add(AuditLog(organization_id=organization_id, actor_user_id=user.id, event=f"fhir.{resource_type.lower()}.{interaction}",
                    resource_type=resource_type.lower(), resource_id=resource_id, details={"version": "R4"}))
    db.commit()


@app.get("/api/v1/fhir/r4/Practitioner")
def fhir_search_practitioners(name: str | None = None, context=Depends(require_permission("appointments:read")), db: Session = Depends(get_db)):
    user, membership = context
    query = db.query(Practitioner).filter_by(organization_id=membership.organization_id, status="active")
    if name:
        term = "%" + name.strip() + "%"
        query = query.filter((Practitioner.given_name.ilike(term)) | (Practitioner.family_name.ilike(term)))
    rows = query.order_by(Practitioner.family_name, Practitioner.given_name).limit(100).all()
    record_fhir_access(db, user, membership.organization_id, "search", "Practitioner")
    return Response(content=json.dumps(fhir_search_bundle("Practitioner", rows, to_fhir_practitioner)), media_type="application/fhir+json")


@app.get("/api/v1/fhir/r4/Practitioner/{practitioner_id}")
def fhir_read_practitioner(practitioner_id: int, context=Depends(require_permission("appointments:read")), db: Session = Depends(get_db)):
    user, membership = context
    row = db.query(Practitioner).filter_by(id=practitioner_id, organization_id=membership.organization_id, status="active").first()
    if not row:
        raise HTTPException(status_code=404, detail="FHIR Practitioner not found")
    record_fhir_access(db, user, membership.organization_id, "read", "Practitioner", str(row.id))
    return Response(content=json.dumps(to_fhir_practitioner(row)), media_type="application/fhir+json")


@app.get("/api/v1/fhir/r4/Appointment")
def fhir_search_appointments(patient: str | None = None, context=Depends(require_permission("appointments:read")), db: Session = Depends(get_db)):
    user, membership = context
    query = db.query(Appointment).filter_by(organization_id=membership.organization_id)
    if patient:
        patient_id = patient.rsplit("/", 1)[-1]
        if not patient_id.isdigit():
            raise HTTPException(status_code=400, detail="FHIR patient search must reference Patient/{id}")
        query = query.filter_by(patient_id=int(patient_id))
    rows = query.order_by(Appointment.starts_at.desc()).limit(100).all()
    record_fhir_access(db, user, membership.organization_id, "search", "Appointment")
    return Response(content=json.dumps(fhir_search_bundle("Appointment", rows, to_fhir_appointment)), media_type="application/fhir+json")


@app.get("/api/v1/fhir/r4/Appointment/{appointment_id}")
def fhir_read_appointment(appointment_id: int, context=Depends(require_permission("appointments:read")), db: Session = Depends(get_db)):
    user, membership = context
    row = db.query(Appointment).filter_by(id=appointment_id, organization_id=membership.organization_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="FHIR Appointment not found")
    record_fhir_access(db, user, membership.organization_id, "read", "Appointment", str(row.id))
    return Response(content=json.dumps(to_fhir_appointment(row)), media_type="application/fhir+json")


@app.get("/api/v1/fhir/r4/Encounter")
def fhir_search_encounters(patient: str | None = None, context=Depends(require_permission("encounters:read")), db: Session = Depends(get_db)):
    user, membership = context
    query = db.query(Encounter).filter_by(organization_id=membership.organization_id)
    if patient:
        patient_id = patient.rsplit("/", 1)[-1]
        if not patient_id.isdigit():
            raise HTTPException(status_code=400, detail="FHIR patient search must reference Patient/{id}")
        query = query.filter_by(patient_id=int(patient_id))
    rows = query.order_by(Encounter.created_at.desc()).limit(100).all()
    record_fhir_access(db, user, membership.organization_id, "search", "Encounter")
    return Response(content=json.dumps(fhir_search_bundle("Encounter", rows, to_fhir_encounter)), media_type="application/fhir+json")


@app.get("/api/v1/fhir/r4/Encounter/{encounter_id}")
def fhir_read_encounter(encounter_id: int, context=Depends(require_permission("encounters:read")), db: Session = Depends(get_db)):
    user, membership = context
    row = db.query(Encounter).filter_by(id=encounter_id, organization_id=membership.organization_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="FHIR Encounter not found")
    record_fhir_access(db, user, membership.organization_id, "read", "Encounter", str(row.id))
    return Response(content=json.dumps(to_fhir_encounter(row)), media_type="application/fhir+json")


@app.post("/api/v1/fhir/r4/Patient", status_code=201)
def fhir_create_patient(resource: dict, context=Depends(require_permission("patients:write")), db: Session = Depends(get_db)):
    user, membership = context
    if resource.get("resourceType") != "Patient":
        raise HTTPException(status_code=422, detail="FHIR resourceType must be Patient")
    names = resource.get("name") or []
    if not isinstance(names, list) or not names or not isinstance(names[0], dict) or not names[0].get("family") or not isinstance(names[0].get("given"), list) or not names[0]["given"]:
        raise HTTPException(status_code=422, detail="FHIR Patient requires a family and given name")
    gender = resource.get("gender", "unknown")
    if gender not in {"male", "female", "other", "unknown"}:
        raise HTTPException(status_code=422, detail="Invalid FHIR administrative gender")
    birth_date = None
    if resource.get("birthDate"):
        try:
            birth_date = date.fromisoformat(resource["birthDate"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="FHIR birthDate must use YYYY-MM-DD")
    identifiers = resource.get("identifier") or []
    mrn = next((item.get("value") for item in identifiers if item.get("value")), None) or "NC-" + uuid4().hex[:10].upper()
    telecom = resource.get("telecom") or []
    phone = next((item.get("value") for item in telecom if item.get("system") == "phone"), None)
    email = next((item.get("value") for item in telecom if item.get("system") == "email"), None)
    patient = Patient(
        organization_id=membership.organization_id, mrn=mrn, given_name=names[0]["given"][0],
        family_name=names[0]["family"], gender=gender, birth_date=birth_date,
        phone=phone, email=email, status="active" if resource.get("active", True) else "inactive", created_by=user.id,
    )
    db.add(patient)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="FHIR Patient identifier already exists")
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="fhir.patient.created", resource_type="patient", resource_id=str(patient.id), details={"version": "R4"}))
    db.commit()
    db.refresh(patient)
    return Response(content=json.dumps(to_fhir_patient(patient)), status_code=201, media_type="application/fhir+json")


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/analytics/summary")
def analytics_summary(context=Depends(require_permission("reports:read")), db: Session = Depends(get_db)):
    _, membership = context
    org_id = membership.organization_id
    return {
        "patients": db.query(Patient).filter_by(organization_id=org_id, status="active").count(),
        "appointments": db.query(Appointment).filter_by(organization_id=org_id).count(),
        "encounters": db.query(Encounter).filter_by(organization_id=org_id).count(),
        "open_claims": db.query(Claim).filter(Claim.organization_id == org_id, Claim.status.in_(["draft", "submitted", "in_review"])).count(),
        "unpaid_invoices": db.query(Invoice).filter(Invoice.organization_id == org_id, Invoice.status != "paid").count(),
        "prescriptions": db.query(Prescription).filter_by(organization_id=org_id).count(),
    }


@app.get("/api/v1/audit")
def list_audit_events(context=Depends(require_permission("users:read")), db: Session = Depends(get_db)):
    _, membership = context
    rows = db.query(AuditLog).filter_by(organization_id=membership.organization_id).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [{"id": row.id, "actor_user_id": row.actor_user_id, "event": row.event, "resource_type": row.resource_type,
             "resource_id": row.resource_id, "created_at": row.created_at, "details": row.details} for row in rows]


@app.post("/api/v1/ai/copilot")
def care_copilot(payload: CopilotRequest, context=Depends(get_current_context), db: Session = Depends(get_db)):
    """Private, permission-aware retrieval helper. It does not generate clinical advice."""
    user, membership = context
    role_permissions_set = {permission.code for permission in membership.role.permissions}
    if membership.role.name == "super_admin":
        role_permissions_set.add("*")
    query = payload.query.strip()
    lowered = query.lower()
    organization_id = membership.organization_id
    words = [part for part in query.replace("?", " ").replace(",", " ").split() if len(part) > 2 and part.lower() not in {"the", "and", "for", "show", "list", "find", "what", "about", "please", "today", "upcoming", "recent"}]
    sources: list[dict] = []
    category = "help"

    def require(code: str):
        if "*" not in role_permissions_set and code not in role_permissions_set:
            raise HTTPException(status_code=403, detail=f"This assistant query requires {code} permission")

    if any(word in lowered for word in ("patient", "mrn", "chart")):
        require("patients:read")
        category = "patients"
        query_rows = db.query(Patient).filter_by(organization_id=organization_id, status="active")
        if words:
            from sqlalchemy import or_
            query_rows = query_rows.filter(or_(*[Patient.given_name.ilike(f"%{word}%") | Patient.family_name.ilike(f"%{word}%") | Patient.mrn.ilike(f"%{word}%") for word in words]))
        rows = query_rows.order_by(Patient.family_name, Patient.given_name).limit(20).all()
        sources = [{"id": row.id, "mrn": row.mrn, "name": f"{row.given_name} {row.family_name}", "status": row.status} for row in rows]
        answer = f"Found {len(sources)} matching active patient record(s)." if sources else "No active patient records matched that search."
    elif any(word in lowered for word in ("appointment", "schedule", "visit")):
        require("appointments:read")
        category = "appointments"
        rows = db.query(Appointment, Patient, Practitioner).join(Patient, Appointment.patient_id == Patient.id).join(Practitioner, Appointment.practitioner_id == Practitioner.id).filter(Appointment.organization_id == organization_id).order_by(Appointment.starts_at.desc()).limit(20).all()
        sources = [{"id": row.id, "patient": f"{patient.given_name} {patient.family_name}", "practitioner": f"{practitioner.given_name} {practitioner.family_name}", "starts_at": row.starts_at.isoformat(), "status": row.status, "reason": row.reason} for row, patient, practitioner in rows]
        answer = f"Showing {len(sources)} most recent appointment(s) for this organization."
    elif any(word in lowered for word in ("claim", "payer", "insurance")):
        require("claims:read")
        category = "claims"
        rows = db.query(Claim).filter_by(organization_id=organization_id).order_by(Claim.created_at.desc()).limit(20).all()
        sources = [{"claim_number": row.claim_number, "payer": row.payer_name, "amount_cents": row.amount_cents, "status": row.status} for row in rows]
        answer = f"Showing {len(sources)} most recent claim(s)."
    elif any(word in lowered for word in ("prescription", "medication", "medicine")):
        require("prescriptions:read")
        category = "prescriptions"
        rows = db.query(Prescription).filter_by(organization_id=organization_id).order_by(Prescription.created_at.desc()).limit(20).all()
        sources = [{"id": row.id, "patient_id": row.patient_id, "medication": row.medication_name, "dosage": row.dosage, "frequency": row.frequency, "status": row.status} for row in rows]
        answer = f"Showing {len(sources)} most recent prescription(s)."
    elif any(word in lowered for word in ("summary", "overview", "counts", "operations")):
        require("reports:read")
        category = "summary"
        sources = [{"patients": db.query(Patient).filter_by(organization_id=organization_id, status="active").count(),
                    "appointments": db.query(Appointment).filter_by(organization_id=organization_id).count(),
                    "encounters": db.query(Encounter).filter_by(organization_id=organization_id).count(),
                    "open_claims": db.query(Claim).filter(Claim.organization_id == organization_id, Claim.status.in_(["draft", "submitted", "in_review"])).count()}]
        answer = "Here is a current count summary for your organization."
    else:
        answer = "I can find patients, appointments, prescriptions, claims, or organization counts you are permitted to view. I do not interpret symptoms or recommend diagnosis or treatment."

    db.add(AuditLog(organization_id=organization_id, actor_user_id=user.id, event="ai.copilot.retrieval", details={"category": category, "result_count": len(sources)}))
    db.commit()
    return {"answer": answer, "category": category, "sources": sources, "generated": False}


@app.post("/api/v1/auth/login", response_model=SessionResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        db.add(AuditLog(event="auth.login.failed", details={}))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    membership = (
        db.query(OrganizationMembership)
        .options(joinedload(OrganizationMembership.organization), joinedload(OrganizationMembership.role))
        .join(Organization)
        .filter(OrganizationMembership.user_id == user.id, Organization.slug == payload.organization_slug)
        .first()
    )
    if not membership:
        db.add(AuditLog(actor_user_id=user.id, event="auth.login.denied", details={}))
        db.commit()
        raise HTTPException(status_code=403, detail="No access to this organization")
    token = create_access_token(subject=str(user.id), organization_id=membership.organization_id, role=membership.role.name)
    response.set_cookie(
        "access_token", token, httponly=True, secure=settings.cookie_secure, samesite="lax",
        max_age=settings.access_token_minutes * 60, path="/",
    )
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="auth.login.succeeded", details={}))
    db.commit()
    return SessionResponse(user=UserResponse.model_validate(user), organization=membership.organization.name, role=membership.role.name)


@app.post("/api/v1/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token", path="/", httponly=True, secure=settings.cookie_secure, samesite="lax")
    return {"status": "signed_out"}


@app.get("/api/v1/auth/me", response_model=SessionResponse)
def me(context=Depends(get_current_context)):
    user, membership = context
    return SessionResponse(user=UserResponse.model_validate(user), organization=membership.organization.name, role=membership.role.name)


@app.get("/api/v1/auth/permissions")
def permissions(context=Depends(get_current_context)):
    _, membership = context
    codes = sorted(permission.code for permission in membership.role.permissions)
    if membership.role.name == "super_admin":
        codes.append("*")
    return {"role": membership.role.name, "permissions": codes}


@app.get("/api/v1/organizations/current")
def current_organization(context=Depends(require_permission("users:read"))):
    _, membership = context
    organization = membership.organization
    return {
        "id": organization.id,
        "name": organization.name,
        "slug": organization.slug,
        "status": organization.status,
        "logo_url": organization.logo_url,
        "contact_phone": organization.contact_phone,
        "settings": {
            "timezone": organization.settings.timezone,
            "default_locale": organization.settings.default_locale,
        },
        "subscription": {
            "plan_code": organization.subscription.plan_code,
            "status": organization.subscription.status,
        },
    }


@app.put("/api/v1/organizations/current")
def update_current_organization(payload: OrganizationProfileUpdate, context=Depends(require_permission("users:write")), db: Session = Depends(get_db)):
    user, membership = context
    organization = membership.organization
    organization.name = payload.name
    organization.logo_url = payload.logo_url or None
    organization.contact_phone = payload.contact_phone or None
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="organization.profile.updated", resource_type="organization", resource_id=str(organization.id), details={}))
    db.commit()
    return {"id": organization.id, "name": organization.name, "slug": organization.slug, "status": organization.status, "logo_url": organization.logo_url, "contact_phone": organization.contact_phone,
            "settings": {"timezone": organization.settings.timezone, "default_locale": organization.settings.default_locale},
            "subscription": {"plan_code": organization.subscription.plan_code, "status": organization.subscription.status}}


@app.get("/api/v1/patients", response_model=list[PatientResponse])
def list_patients(context=Depends(require_permission("patients:read")), db: Session = Depends(get_db)):
    user, membership = context
    rows = db.query(Patient).filter_by(organization_id=membership.organization_id, status="active").order_by(Patient.family_name, Patient.given_name).all()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="patient.listed", details={"count": len(rows)}))
    db.commit()
    return rows


@app.post("/api/v1/patients", response_model=PatientResponse, status_code=201)
def create_patient(payload: PatientCreate, context=Depends(require_permission("patients:write")), db: Session = Depends(get_db)):
    user, membership = context
    patient = Patient(**payload.model_dump(), organization_id=membership.organization_id, mrn="NC-" + uuid4().hex[:10].upper(), created_by=user.id)
    db.add(patient)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="patient.created", resource_type="patient", resource_id=str(patient.id), details={}))
    db.commit()
    db.refresh(patient)
    return patient


@app.get("/api/v1/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: int, context=Depends(require_permission("patients:read")), db: Session = Depends(get_db)):
    user, membership = context
    patient = db.query(Patient).filter_by(id=patient_id, organization_id=membership.organization_id, status="active").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="patient.viewed", resource_type="patient", resource_id=str(patient.id), details={}))
    db.commit()
    return patient


@app.get("/api/v1/practitioners", response_model=list[PractitionerResponse])
def list_practitioners(context=Depends(require_permission("patients:read")), db: Session = Depends(get_db)):
    _, membership = context
    return db.query(Practitioner).filter_by(organization_id=membership.organization_id, status="active").order_by(Practitioner.family_name, Practitioner.given_name).all()


@app.post("/api/v1/practitioners", response_model=PractitionerResponse, status_code=201)
def create_practitioner(payload: PractitionerCreate, context=Depends(require_permission("users:write")), db: Session = Depends(get_db)):
    user, membership = context
    practitioner = Practitioner(**payload.model_dump(), organization_id=membership.organization_id, created_by=user.id)
    db.add(practitioner)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="practitioner.created", resource_type="practitioner", resource_id=str(practitioner.id), details={}))
    db.commit()
    db.refresh(practitioner)
    return practitioner


@app.post("/api/v1/practitioners/bulk", response_model=list[PractitionerResponse], status_code=201)
def create_practitioners(payload: PractitionerBatchCreate, context=Depends(require_permission("users:write")), db: Session = Depends(get_db)):
    user, membership = context
    emails = [row.email.lower() for row in payload.practitioners]
    if len(emails) != len(set(emails)):
        raise HTTPException(status_code=409, detail="Each care team member must have a unique email address")
    rows = [Practitioner(**item.model_dump(), organization_id=membership.organization_id, created_by=user.id) for item in payload.practitioners]
    db.add_all(rows)
    try:
        db.flush()
        for row in rows:
            db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="practitioner.created", resource_type="practitioner", resource_id=str(row.id), details={}))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A care team member with one of these email addresses already exists") from exc
    for row in rows:
        db.refresh(row)
    return rows


@app.get("/api/v1/appointments", response_model=list[AppointmentResponse])
def list_appointments(context=Depends(require_permission("appointments:read")), db: Session = Depends(get_db)):
    _, membership = context
    return db.query(Appointment).filter_by(organization_id=membership.organization_id).order_by(Appointment.starts_at.desc()).limit(200).all()


@app.post("/api/v1/appointments", response_model=AppointmentResponse, status_code=201)
def create_appointment(payload: AppointmentCreate, context=Depends(require_permission("appointments:write")), db: Session = Depends(get_db)):
    user, membership = context
    if payload.starts_at.tzinfo is None or payload.ends_at.tzinfo is None or payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="Appointment times require a timezone and end must follow start")
    patient = db.query(Patient).filter_by(id=payload.patient_id, organization_id=membership.organization_id, status="active").first()
    practitioner = db.query(Practitioner).filter_by(id=payload.practitioner_id, organization_id=membership.organization_id, status="active").first()
    if not patient or not practitioner:
        raise HTTPException(status_code=404, detail="Patient or practitioner not found")
    conflict = db.query(Appointment).filter(
        Appointment.organization_id == membership.organization_id,
        Appointment.practitioner_id == practitioner.id,
        Appointment.status.in_(["scheduled", "in_progress"]),
        Appointment.starts_at < payload.ends_at,
        Appointment.ends_at > payload.starts_at,
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail="Practitioner already has an appointment in this time range")
    appointment = Appointment(**payload.model_dump(), organization_id=membership.organization_id, created_by=user.id)
    db.add(appointment)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="appointment.created", resource_type="appointment", resource_id=str(appointment.id), details={}))
    db.commit()
    db.refresh(appointment)
    return appointment


@app.get("/api/v1/encounters", response_model=list[EncounterResponse])
def list_encounters(context=Depends(require_permission("encounters:read")), db: Session = Depends(get_db)):
    _, membership = context
    return db.query(Encounter).filter_by(organization_id=membership.organization_id).order_by(Encounter.created_at.desc()).limit(200).all()


@app.post("/api/v1/encounters", response_model=EncounterResponse, status_code=201)
def create_encounter(payload: EncounterCreate, context=Depends(require_permission("encounters:write")), db: Session = Depends(get_db)):
    user, membership = context
    patient = db.query(Patient).filter_by(id=payload.patient_id, organization_id=membership.organization_id, status="active").first()
    practitioner = db.query(Practitioner).filter_by(id=payload.practitioner_id, organization_id=membership.organization_id, status="active").first()
    if not patient or not practitioner:
        raise HTTPException(status_code=404, detail="Patient or practitioner not found")
    if payload.appointment_id and not db.query(Appointment).filter_by(id=payload.appointment_id, organization_id=membership.organization_id, patient_id=patient.id, practitioner_id=practitioner.id).first():
        raise HTTPException(status_code=404, detail="Appointment not found for this patient and practitioner")
    encounter = Encounter(**payload.model_dump(), organization_id=membership.organization_id, created_by=user.id)
    db.add(encounter)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="encounter.created", resource_type="encounter", resource_id=str(encounter.id), details={}))
    db.commit()
    db.refresh(encounter)
    return encounter


def validate_clinical_subjects(db: Session, organization_id: int, patient_id: int, practitioner_id: int):
    patient = db.query(Patient).filter_by(id=patient_id, organization_id=organization_id, status="active").first()
    practitioner = db.query(Practitioner).filter_by(id=practitioner_id, organization_id=organization_id, status="active").first()
    if not patient or not practitioner:
        raise HTTPException(status_code=404, detail="Patient or practitioner not found")


@app.get("/api/v1/prescriptions", response_model=list[PrescriptionResponse])
def list_prescriptions(context=Depends(require_permission("prescriptions:read")), db: Session = Depends(get_db)):
    _, membership = context
    return db.query(Prescription).filter_by(organization_id=membership.organization_id).order_by(Prescription.created_at.desc()).limit(200).all()


@app.post("/api/v1/prescriptions", response_model=PrescriptionResponse, status_code=201)
def create_prescription(payload: PrescriptionCreate, context=Depends(require_permission("prescriptions:write")), db: Session = Depends(get_db)):
    user, membership = context
    validate_clinical_subjects(db, membership.organization_id, payload.patient_id, payload.practitioner_id)
    order = Prescription(**payload.model_dump(), organization_id=membership.organization_id, created_by=user.id)
    db.add(order)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="prescription.created", resource_type="prescription", resource_id=str(order.id), details={}))
    db.commit()
    db.refresh(order)
    return order


@app.patch("/api/v1/pharmacy/prescriptions/{prescription_id}/status", response_model=PrescriptionResponse)
def update_dispense_status(prescription_id: int, payload: StatusUpdate, context=Depends(require_permission("pharmacy:write")), db: Session = Depends(get_db)):
    user, membership = context
    if payload.status not in {"active", "dispensing", "dispensed", "cancelled"}:
        raise HTTPException(status_code=422, detail="Unsupported dispensing status")
    order = db.query(Prescription).filter_by(id=prescription_id, organization_id=membership.organization_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Prescription not found")
    if order.status == "cancelled" and payload.status != "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled prescriptions cannot be reopened")
    order.status = payload.status
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="pharmacy.dispense.status_changed",
                    resource_type="prescription", resource_id=str(order.id), details={"status": payload.status}))
    db.commit()
    db.refresh(order)
    return order


@app.get("/api/v1/lab-orders", response_model=list[LabOrderResponse])
def list_lab_orders(context=Depends(require_permission("labs:read")), db: Session = Depends(get_db)):
    _, membership = context
    return db.query(LabOrder).filter_by(organization_id=membership.organization_id).order_by(LabOrder.created_at.desc()).limit(200).all()


@app.post("/api/v1/lab-orders", response_model=LabOrderResponse, status_code=201)
def create_lab_order(payload: LabOrderCreate, context=Depends(require_permission("labs:write")), db: Session = Depends(get_db)):
    user, membership = context
    validate_clinical_subjects(db, membership.organization_id, payload.patient_id, payload.practitioner_id)
    order = LabOrder(**payload.model_dump(), organization_id=membership.organization_id, created_by=user.id)
    db.add(order)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="lab.order.created", resource_type="lab_order", resource_id=str(order.id), details={}))
    db.commit()
    db.refresh(order)
    return order


@app.patch("/api/v1/lab-orders/{order_id}/result", response_model=LabOrderResponse)
def update_lab_result(order_id: int, payload: OrderResultUpdate, context=Depends(require_permission("labs:write")), db: Session = Depends(get_db)):
    user, membership = context
    order = db.query(LabOrder).filter_by(id=order_id, organization_id=membership.organization_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    if order.status == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled lab orders cannot receive results")
    order.result_summary = payload.summary
    order.status = "completed"
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="lab.result.recorded", resource_type="lab_order", resource_id=str(order.id), details={}))
    db.commit()
    db.refresh(order)
    return order


@app.get("/api/v1/radiology-orders", response_model=list[RadiologyOrderResponse])
def list_radiology_orders(context=Depends(require_permission("radiology:read")), db: Session = Depends(get_db)):
    _, membership = context
    return db.query(RadiologyOrder).filter_by(organization_id=membership.organization_id).order_by(RadiologyOrder.created_at.desc()).limit(200).all()


@app.post("/api/v1/radiology-orders", response_model=RadiologyOrderResponse, status_code=201)
def create_radiology_order(payload: RadiologyOrderCreate, context=Depends(require_permission("radiology:write")), db: Session = Depends(get_db)):
    user, membership = context
    validate_clinical_subjects(db, membership.organization_id, payload.patient_id, payload.practitioner_id)
    order = RadiologyOrder(**payload.model_dump(), organization_id=membership.organization_id, created_by=user.id)
    db.add(order)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="radiology.order.created", resource_type="radiology_order", resource_id=str(order.id), details={}))
    db.commit()
    db.refresh(order)
    return order


@app.patch("/api/v1/radiology-orders/{order_id}/report", response_model=RadiologyOrderResponse)
def update_radiology_report(order_id: int, payload: OrderResultUpdate, context=Depends(require_permission("radiology:write")), db: Session = Depends(get_db)):
    user, membership = context
    order = db.query(RadiologyOrder).filter_by(id=order_id, organization_id=membership.organization_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Radiology order not found")
    if order.status == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled imaging orders cannot receive reports")
    order.report_summary = payload.summary
    order.status = "completed"
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="radiology.report.recorded", resource_type="radiology_order", resource_id=str(order.id), details={}))
    db.commit()
    db.refresh(order)
    return order


@app.get("/api/v1/directory")
def organization_directory(context=Depends(require_permission("messages:read")), db: Session = Depends(get_db)):
    user, membership = context
    users = (
        db.query(User)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .filter(OrganizationMembership.organization_id == membership.organization_id, User.is_active.is_(True), User.id != user.id)
        .order_by(User.full_name)
        .all()
    )
    return [{"id": person.id, "full_name": person.full_name, "email": person.email} for person in users]


@app.get("/api/v1/messages")
def list_messages(with_user_id: int, context=Depends(require_permission("messages:read")), db: Session = Depends(get_db)):
    user, membership = context
    other = db.query(OrganizationMembership).filter_by(organization_id=membership.organization_id, user_id=with_user_id).first()
    if not other:
        raise HTTPException(status_code=404, detail="Recipient not found")
    messages = db.query(ChatMessage).filter(
        ChatMessage.organization_id == membership.organization_id,
        ((ChatMessage.sender_user_id == user.id) & (ChatMessage.recipient_user_id == with_user_id)) |
        ((ChatMessage.sender_user_id == with_user_id) & (ChatMessage.recipient_user_id == user.id)),
    ).order_by(ChatMessage.sent_at).limit(200).all()
    return [{"id": item.id, "sender_user_id": item.sender_user_id, "recipient_user_id": item.recipient_user_id, "body": item.body, "sent_at": item.sent_at, "read_at": item.read_at} for item in messages]


@app.post("/api/v1/messages", status_code=201)
def send_message(payload: MessageCreate, context=Depends(require_permission("messages:write")), db: Session = Depends(get_db)):
    user, membership = context
    recipient = db.query(OrganizationMembership).filter_by(organization_id=membership.organization_id, user_id=payload.recipient_user_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    message = ChatMessage(organization_id=membership.organization_id, sender_user_id=user.id, recipient_user_id=payload.recipient_user_id, body=payload.body)
    db.add(message)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="message.sent", resource_type="message", resource_id=str(message.id), details={}))
    db.add(Notification(organization_id=membership.organization_id, recipient_user_id=payload.recipient_user_id, title="New secure message", body="You have a new message.", category="message"))
    db.commit()
    return {"id": message.id, "sent_at": message.sent_at}


@app.get("/api/v1/notifications")
def list_notifications(context=Depends(require_permission("notifications:read")), db: Session = Depends(get_db)):
    user, membership = context
    items = db.query(Notification).filter_by(organization_id=membership.organization_id, recipient_user_id=user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return [{"id": item.id, "title": item.title, "body": item.body, "category": item.category, "read_at": item.read_at, "created_at": item.created_at} for item in items]


@app.post("/api/v1/notifications")
def create_notification(payload: NotificationCreate, context=Depends(require_permission("notifications:write")), db: Session = Depends(get_db)):
    user, membership = context
    item = Notification(organization_id=membership.organization_id, recipient_user_id=user.id, title=payload.title, body=payload.body, category=payload.category)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "title": item.title, "created_at": item.created_at}


@app.post("/api/v1/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, context=Depends(require_permission("notifications:read")), db: Session = Depends(get_db)):
    user, membership = context
    item = db.query(Notification).filter_by(id=notification_id, organization_id=membership.organization_id, recipient_user_id=user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "read"}


@app.get("/api/v1/telehealth/sessions")
def list_video_sessions(context=Depends(require_permission("telehealth:read")), db: Session = Depends(get_db)):
    _, membership = context
    rows = db.query(VideoSession).filter_by(organization_id=membership.organization_id).order_by(VideoSession.created_at.desc()).limit(100).all()
    return [{"id": row.id, "appointment_id": row.appointment_id, "room_code": row.room_code, "status": row.status, "started_at": row.started_at, "ended_at": row.ended_at} for row in rows]


@app.post("/api/v1/telehealth/sessions", status_code=201)
def create_video_session(appointment_id: int, context=Depends(require_permission("telehealth:write")), db: Session = Depends(get_db)):
    user, membership = context
    appointment = db.query(Appointment).filter_by(id=appointment_id, organization_id=membership.organization_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if db.query(VideoSession).filter_by(appointment_id=appointment.id).first():
        raise HTTPException(status_code=409, detail="A virtual session already exists for this appointment")
    row = VideoSession(organization_id=membership.organization_id, appointment_id=appointment.id, room_code=secrets.token_urlsafe(24), created_by=user.id)
    db.add(row)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="telehealth.session.created", resource_type="video_session", resource_id=str(row.id), details={}))
    db.commit()
    return {"id": row.id, "appointment_id": row.appointment_id, "room_code": row.room_code, "status": row.status}


@app.post("/api/v1/telehealth/sessions/{session_id}/{action}")
def change_video_session(session_id: int, action: str, context=Depends(require_permission("telehealth:write")), db: Session = Depends(get_db)):
    user, membership = context
    row = db.query(VideoSession).filter_by(id=session_id, organization_id=membership.organization_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Virtual session not found")
    if action == "start" and row.status == "scheduled":
        row.status = "in_progress"
        row.started_at = datetime.now(timezone.utc)
    elif action == "end" and row.status == "in_progress":
        row.status = "completed"
        row.ended_at = datetime.now(timezone.utc)
    else:
        raise HTTPException(status_code=409, detail="Invalid virtual session state transition")
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="telehealth.session." + action, resource_type="video_session", resource_id=str(row.id), details={}))
    db.commit()
    return {"id": row.id, "status": row.status}


@app.get("/api/v1/insurance/policies")
def list_policies(context=Depends(require_permission("insurance:read")), db: Session = Depends(get_db)):
    _, membership = context
    rows = db.query(InsurancePolicy).filter_by(organization_id=membership.organization_id).order_by(InsurancePolicy.created_at.desc()).limit(200).all()
    return [{"id": row.id, "patient_id": row.patient_id, "payer_name": row.payer_name, "member_id": row.member_id, "plan_name": row.plan_name, "status": row.status} for row in rows]


@app.post("/api/v1/insurance/policies", status_code=201)
def create_policy(payload: InsurancePolicyCreate, context=Depends(require_permission("insurance:write")), db: Session = Depends(get_db)):
    user, membership = context
    if not db.query(Patient).filter_by(id=payload.patient_id, organization_id=membership.organization_id, status="active").first():
        raise HTTPException(status_code=404, detail="Patient not found")
    row = InsurancePolicy(**payload.model_dump(), organization_id=membership.organization_id, created_by=user.id)
    db.add(row)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="insurance.policy.created", resource_type="insurance_policy", resource_id=str(row.id), details={}))
    db.commit()
    return {"id": row.id, "patient_id": row.patient_id, "payer_name": row.payer_name, "member_id": row.member_id, "plan_name": row.plan_name, "status": row.status}


@app.get("/api/v1/claims")
def list_claims(context=Depends(require_permission("claims:read")), db: Session = Depends(get_db)):
    _, membership = context
    rows = db.query(Claim).filter_by(organization_id=membership.organization_id).order_by(Claim.created_at.desc()).limit(200).all()
    return [{"id": row.id, "patient_id": row.patient_id, "claim_number": row.claim_number, "payer_name": row.payer_name, "amount_cents": row.amount_cents, "status": row.status} for row in rows]


@app.post("/api/v1/claims", status_code=201)
def create_claim(payload: ClaimCreate, context=Depends(require_permission("claims:write")), db: Session = Depends(get_db)):
    user, membership = context
    if not db.query(Patient).filter_by(id=payload.patient_id, organization_id=membership.organization_id, status="active").first():
        raise HTTPException(status_code=404, detail="Patient not found")
    row = Claim(**payload.model_dump(), organization_id=membership.organization_id, claim_number="CL-" + uuid4().hex[:12].upper(), created_by=user.id)
    db.add(row)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="claim.created", resource_type="claim", resource_id=str(row.id), details={}))
    db.commit()
    return {"id": row.id, "patient_id": row.patient_id, "claim_number": row.claim_number, "payer_name": row.payer_name, "amount_cents": row.amount_cents, "status": row.status}


@app.patch("/api/v1/claims/{claim_id}/status")
def update_claim_status(claim_id: int, payload: StatusUpdate, context=Depends(require_permission("claims:write")), db: Session = Depends(get_db)):
    user, membership = context
    row = db.query(Claim).filter_by(id=claim_id, organization_id=membership.organization_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Claim not found")
    allowed = {"draft": {"submitted"}, "submitted": {"in_review", "approved", "denied"}, "in_review": {"approved", "denied"}, "approved": {"paid"}}
    if payload.status not in allowed.get(row.status, set()):
        raise HTTPException(status_code=409, detail="Invalid claim status transition")
    row.status = payload.status
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="claim.status.updated", resource_type="claim", resource_id=str(row.id), details={"status": row.status}))
    db.commit()
    return {"id": row.id, "status": row.status}


@app.get("/api/v1/authorizations")
def list_authorizations(context=Depends(require_permission("authorizations:read")), db: Session = Depends(get_db)):
    _, membership = context
    rows = db.query(PriorAuthorization).filter_by(organization_id=membership.organization_id).order_by(PriorAuthorization.created_at.desc()).limit(200).all()
    return [{"id": row.id, "patient_id": row.patient_id, "payer_name": row.payer_name, "service_name": row.service_name, "reference_number": row.reference_number, "status": row.status} for row in rows]


@app.post("/api/v1/authorizations", status_code=201)
def create_authorization(payload: AuthorizationCreate, context=Depends(require_permission("authorizations:write")), db: Session = Depends(get_db)):
    user, membership = context
    if not db.query(Patient).filter_by(id=payload.patient_id, organization_id=membership.organization_id, status="active").first():
        raise HTTPException(status_code=404, detail="Patient not found")
    row = PriorAuthorization(**payload.model_dump(), organization_id=membership.organization_id, created_by=user.id)
    db.add(row)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="authorization.created", resource_type="authorization", resource_id=str(row.id), details={}))
    db.commit()
    return {"id": row.id, "patient_id": row.patient_id, "payer_name": row.payer_name, "service_name": row.service_name, "reference_number": row.reference_number, "status": row.status}


@app.patch("/api/v1/authorizations/{authorization_id}/status")
def update_authorization_status(authorization_id: int, payload: StatusUpdate, context=Depends(require_permission("authorizations:write")), db: Session = Depends(get_db)):
    user, membership = context
    row = db.query(PriorAuthorization).filter_by(id=authorization_id, organization_id=membership.organization_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Authorization not found")
    allowed = {"requested": {"submitted"}, "submitted": {"approved", "denied", "needs_information"}, "needs_information": {"submitted"}}
    if payload.status not in allowed.get(row.status, set()):
        raise HTTPException(status_code=409, detail="Invalid authorization status transition")
    row.status = payload.status
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="authorization.status.updated", resource_type="authorization", resource_id=str(row.id), details={"status": row.status}))
    db.commit()
    return {"id": row.id, "status": row.status}


@app.get("/api/v1/billing/invoices")
def list_invoices(context=Depends(require_permission("billing:read")), db: Session = Depends(get_db)):
    _, membership = context
    rows = db.query(Invoice).filter_by(organization_id=membership.organization_id).order_by(Invoice.created_at.desc()).limit(200).all()
    return [{"id": row.id, "patient_id": row.patient_id, "invoice_number": row.invoice_number, "description": row.description, "amount_cents": row.amount_cents, "paid_cents": row.paid_cents, "status": row.status} for row in rows]


@app.post("/api/v1/billing/invoices", status_code=201)
def create_invoice(payload: InvoiceCreate, context=Depends(require_permission("billing:write")), db: Session = Depends(get_db)):
    user, membership = context
    if not db.query(Patient).filter_by(id=payload.patient_id, organization_id=membership.organization_id, status="active").first():
        raise HTTPException(status_code=404, detail="Patient not found")
    row = Invoice(**payload.model_dump(), organization_id=membership.organization_id, invoice_number="INV-" + uuid4().hex[:12].upper(), created_by=user.id)
    db.add(row)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="invoice.created", resource_type="invoice", resource_id=str(row.id), details={}))
    db.commit()
    return {"id": row.id, "invoice_number": row.invoice_number, "amount_cents": row.amount_cents, "status": row.status}


@app.post("/api/v1/billing/invoices/{invoice_id}/payments", status_code=201)
def record_payment(invoice_id: int, payload: PaymentCreate, context=Depends(require_permission("billing:write")), db: Session = Depends(get_db)):
    user, membership = context
    row = db.query(Invoice).filter_by(id=invoice_id, organization_id=membership.organization_id).with_for_update().first()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if payload.amount_cents > row.amount_cents - row.paid_cents:
        raise HTTPException(status_code=409, detail="Payment exceeds the remaining invoice balance")
    payment = Payment(organization_id=membership.organization_id, invoice_id=row.id, amount_cents=payload.amount_cents, method=payload.method, reference=payload.reference, created_by=user.id)
    row.paid_cents += payload.amount_cents
    row.status = "paid" if row.paid_cents == row.amount_cents else "partial"
    db.add(payment)
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="payment.recorded", resource_type="invoice", resource_id=str(row.id), details={"amount_cents": payload.amount_cents}))
    db.commit()
    return {"payment_id": payment.id, "invoice_id": row.id, "paid_cents": row.paid_cents, "status": row.status}


@app.get("/api/v1/remote-monitoring/devices")
def list_devices(context=Depends(require_permission("monitoring:read")), db: Session = Depends(get_db)):
    _, membership = context
    rows = db.query(Device).filter_by(organization_id=membership.organization_id, status="active").order_by(Device.created_at.desc()).limit(200).all()
    return [{"id": row.id, "patient_id": row.patient_id, "display_name": row.display_name, "device_type": row.device_type, "serial_number": row.serial_number, "status": row.status} for row in rows]


def create_reading_alerts(db: Session, device: Device, reading: DeviceReading):
    rules = db.query(MonitoringRule).filter_by(organization_id=device.organization_id, metric=reading.metric.strip(), unit=reading.unit.strip(), enabled=True).all()
    for rule in rules:
        breached = (rule.minimum is not None and reading.value < rule.minimum) or (rule.maximum is not None and reading.value > rule.maximum)
        if breached:
            boundary = "below minimum" if rule.minimum is not None and reading.value < rule.minimum else "above maximum"
            db.add(MonitoringAlert(organization_id=device.organization_id, device_id=device.id, reading_id=reading.id,
                                   rule_id=rule.id, message=f"{reading.metric} is {boundary} configured threshold ({reading.value:g} {reading.unit})"))


@app.get("/api/v1/remote-monitoring/rules")
def list_monitoring_rules(context=Depends(require_permission("monitoring:read")), db: Session = Depends(get_db)):
    _, membership = context
    rows = db.query(MonitoringRule).filter_by(organization_id=membership.organization_id).order_by(MonitoringRule.metric).all()
    return [{"id": r.id, "metric": r.metric, "unit": r.unit, "minimum": r.minimum, "maximum": r.maximum, "enabled": r.enabled} for r in rows]


@app.post("/api/v1/remote-monitoring/rules", status_code=201)
def create_monitoring_rule(payload: MonitoringRuleCreate, context=Depends(require_permission("monitoring:write")), db: Session = Depends(get_db)):
    user, membership = context
    rule = db.query(MonitoringRule).filter_by(organization_id=membership.organization_id, metric=payload.metric.strip(), unit=payload.unit.strip()).first()
    if rule:
        rule.minimum, rule.maximum, rule.enabled = payload.minimum, payload.maximum, True
    else:
        rule = MonitoringRule(organization_id=membership.organization_id, metric=payload.metric.strip(), unit=payload.unit.strip(), minimum=payload.minimum, maximum=payload.maximum)
        db.add(rule)
        db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="monitoring.rule.saved", resource_type="monitoring_rule", resource_id=str(rule.id), details={"metric": rule.metric, "unit": rule.unit}))
    db.commit()
    return {"id": rule.id, "metric": rule.metric, "unit": rule.unit, "minimum": rule.minimum, "maximum": rule.maximum, "enabled": rule.enabled}


@app.get("/api/v1/remote-monitoring/alerts")
def list_monitoring_alerts(context=Depends(require_permission("monitoring:read")), db: Session = Depends(get_db)):
    _, membership = context
    rows = (db.query(MonitoringAlert, Device, Patient, DeviceReading)
            .join(Device, MonitoringAlert.device_id == Device.id)
            .join(Patient, Device.patient_id == Patient.id)
            .join(DeviceReading, MonitoringAlert.reading_id == DeviceReading.id)
            .filter(MonitoringAlert.organization_id == membership.organization_id)
            .order_by(MonitoringAlert.created_at.desc()).limit(200).all())
    return [{"id": a.id, "device_id": d.id, "device_name": d.display_name, "patient_name": p.given_name + " " + p.family_name,
             "metric": reading.metric, "value": reading.value, "unit": reading.unit, "message": a.message,
             "status": a.status, "created_at": a.created_at, "acknowledged_at": a.acknowledged_at} for a, d, p, reading in rows]


@app.post("/api/v1/remote-monitoring/alerts/{alert_id}/acknowledge")
def acknowledge_monitoring_alert(alert_id: int, context=Depends(require_permission("monitoring:write")), db: Session = Depends(get_db)):
    user, membership = context
    alert = db.query(MonitoringAlert).filter_by(id=alert_id, organization_id=membership.organization_id).with_for_update().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status == "open":
        alert.status, alert.acknowledged_at, alert.acknowledged_by = "acknowledged", datetime.now(timezone.utc), user.id
        db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="monitoring.alert.acknowledged", resource_type="monitoring_alert", resource_id=str(alert.id), details={}))
        db.commit()
    return {"id": alert.id, "status": alert.status, "acknowledged_at": alert.acknowledged_at}


@app.post("/api/v1/remote-monitoring/devices", status_code=201)
def create_device(payload: DeviceCreate, context=Depends(require_permission("monitoring:write")), db: Session = Depends(get_db)):
    user, membership = context
    if not db.query(Patient).filter_by(id=payload.patient_id, organization_id=membership.organization_id, status="active").first():
        raise HTTPException(status_code=404, detail="Patient not found")
    ingest_token = secrets.token_urlsafe(32)
    row = Device(**payload.model_dump(), organization_id=membership.organization_id, created_by=user.id,
                 ingest_token_hash=hashlib.sha256(ingest_token.encode()).hexdigest())
    db.add(row)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="monitoring.device.created", resource_type="device", resource_id=str(row.id), details={}))
    db.commit()
    return {"id": row.id, "patient_id": row.patient_id, "display_name": row.display_name, "device_type": row.device_type, "serial_number": row.serial_number, "status": row.status, "ingest_token": ingest_token}


@app.post("/api/v1/remote-monitoring/devices/{device_id}/ingest-token")
def rotate_device_ingest_token(device_id: int, context=Depends(require_permission("monitoring:write")), db: Session = Depends(get_db)):
    user, membership = context
    device = db.query(Device).filter_by(id=device_id, organization_id=membership.organization_id, status="active").first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    ingest_token = secrets.token_urlsafe(32)
    device.ingest_token_hash = hashlib.sha256(ingest_token.encode()).hexdigest()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="monitoring.device.token_rotated", resource_type="device", resource_id=str(device.id), details={}))
    db.commit()
    return {"device_id": device.id, "ingest_token": ingest_token}


@app.post("/api/v1/remote-monitoring/ingest/{device_id}/readings", status_code=201)
def ingest_device_reading(device_id: int, payload: DeviceReadingCreate, request: Request, db: Session = Depends(get_db)):
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Device bearer token required")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    device = db.query(Device).filter_by(id=device_id, ingest_token_hash=token_hash, status="active").first()
    if not device:
        raise HTTPException(status_code=401, detail="Invalid device token")
    if payload.recorded_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="Reading timestamp must include a timezone")
    row = DeviceReading(device_id=device.id, organization_id=device.organization_id, **payload.model_dump())
    db.add(row)
    db.flush()
    create_reading_alerts(db, device, row)
    db.add(AuditLog(organization_id=device.organization_id, event="monitoring.reading.ingested", resource_type="device_reading", resource_id=str(row.id), details={"metric": row.metric, "unit": row.unit}))
    db.commit()
    return {"id": row.id, "device_id": row.device_id, "metric": row.metric, "value": row.value, "unit": row.unit, "recorded_at": row.recorded_at}


@app.get("/api/v1/remote-monitoring/devices/{device_id}/readings")
def list_device_readings(device_id: int, context=Depends(require_permission("monitoring:read")), db: Session = Depends(get_db)):
    _, membership = context
    device = db.query(Device).filter_by(id=device_id, organization_id=membership.organization_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    rows = db.query(DeviceReading).filter_by(device_id=device.id, organization_id=membership.organization_id).order_by(DeviceReading.recorded_at.desc()).limit(200).all()
    return [{"id": row.id, "metric": row.metric, "value": row.value, "unit": row.unit, "recorded_at": row.recorded_at} for row in rows]


@app.post("/api/v1/remote-monitoring/devices/{device_id}/readings", status_code=201)
def add_device_reading(device_id: int, payload: DeviceReadingCreate, context=Depends(require_permission("monitoring:write")), db: Session = Depends(get_db)):
    user, membership = context
    if payload.recorded_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="Reading timestamp must include a timezone")
    device = db.query(Device).filter_by(id=device_id, organization_id=membership.organization_id, status="active").first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    row = DeviceReading(device_id=device.id, organization_id=membership.organization_id, **payload.model_dump())
    db.add(row)
    db.flush()
    db.add(AuditLog(organization_id=membership.organization_id, actor_user_id=user.id, event="monitoring.reading.recorded", resource_type="device_reading", resource_id=str(row.id), details={"metric": row.metric, "unit": row.unit}))
    create_reading_alerts(db, device, row)
    db.commit()
    return {"id": row.id, "device_id": row.device_id, "metric": row.metric, "value": row.value, "unit": row.unit, "recorded_at": row.recorded_at}
