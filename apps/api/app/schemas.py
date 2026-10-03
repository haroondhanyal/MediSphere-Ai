from datetime import date, datetime

from email_validator import validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CopilotRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)


def normalize_email(value: str) -> str:
    # The local demo accounts intentionally use the reserved .local suffix.
    candidate = value[:-6] + ".com" if value.lower().endswith(".local") else value
    validate_email(candidate, check_deliverability=False)
    return value.lower()


class LoginRequest(BaseModel):
    email: str
    password: str
    organization_slug: str

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str) -> str:
        return normalize_email(value)


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    user: UserResponse
    organization: str
    role: str


class PatientCreate(BaseModel):
    given_name: str = Field(min_length=1, max_length=100)
    family_name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    gender: str = Field(default="unknown", max_length=30)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=320)


class PatientResponse(PatientCreate):
    id: int
    mrn: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class PractitionerCreate(BaseModel):
    given_name: str = Field(min_length=1, max_length=100)
    family_name: str = Field(min_length=1, max_length=100)
    specialty: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)


class PractitionerResponse(PractitionerCreate):
    id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class AppointmentCreate(BaseModel):
    patient_id: int
    practitioner_id: int
    starts_at: datetime
    ends_at: datetime
    reason: str = Field(default="", max_length=500)


class AppointmentResponse(AppointmentCreate):
    id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class EncounterCreate(BaseModel):
    patient_id: int
    practitioner_id: int
    appointment_id: int | None = None
    note: str = Field(default="", max_length=10000)
    diagnosis_summary: str = Field(default="", max_length=1000)


class EncounterResponse(EncounterCreate):
    id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class PrescriptionCreate(BaseModel):
    patient_id: int
    practitioner_id: int
    medication_name: str = Field(min_length=1, max_length=180)
    dosage: str = Field(min_length=1, max_length=100)
    frequency: str = Field(min_length=1, max_length=180)
    duration: str = Field(default="", max_length=100)
    instructions: str = Field(default="", max_length=1000)


class PrescriptionResponse(PrescriptionCreate):
    id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class LabOrderCreate(BaseModel):
    patient_id: int
    practitioner_id: int
    test_name: str = Field(min_length=1, max_length=180)
    priority: str = Field(default="routine", pattern="^(routine|urgent|stat)$")


class LabOrderResponse(LabOrderCreate):
    id: int
    status: str
    result_summary: str

    model_config = ConfigDict(from_attributes=True)


class OrderResultUpdate(BaseModel):
    summary: str = Field(min_length=1, max_length=4000)


class RadiologyOrderCreate(BaseModel):
    patient_id: int
    practitioner_id: int
    modality: str = Field(min_length=1, max_length=80)
    body_region: str = Field(min_length=1, max_length=120)


class RadiologyOrderResponse(RadiologyOrderCreate):
    id: int
    status: str
    report_summary: str

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    recipient_user_id: int
    body: str = Field(min_length=1, max_length=4000)


class NotificationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(default="", max_length=1000)
    category: str = Field(default="general", max_length=40)


class InsurancePolicyCreate(BaseModel):
    patient_id: int
    payer_name: str = Field(min_length=1, max_length=180)
    member_id: str = Field(min_length=1, max_length=100)
    plan_name: str = Field(default="", max_length=180)


class ClaimCreate(BaseModel):
    patient_id: int
    payer_name: str = Field(min_length=1, max_length=180)
    amount_cents: int = Field(gt=0)


class StatusUpdate(BaseModel):
    status: str


class AuthorizationCreate(BaseModel):
    patient_id: int
    payer_name: str = Field(min_length=1, max_length=180)
    service_name: str = Field(min_length=1, max_length=180)


class InvoiceCreate(BaseModel):
    patient_id: int
    description: str = Field(min_length=1, max_length=240)
    amount_cents: int = Field(gt=0)


class PaymentCreate(BaseModel):
    amount_cents: int = Field(gt=0)
    method: str = Field(default="manual", pattern="^(manual|cash|card|transfer)$")
    reference: str = Field(default="", max_length=100)


class DeviceCreate(BaseModel):
    patient_id: int
    display_name: str = Field(min_length=1, max_length=180)
    device_type: str = Field(min_length=1, max_length=80)
    serial_number: str = Field(default="", max_length=120)


class DeviceReadingCreate(BaseModel):
    metric: str = Field(min_length=1, max_length=100)
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=40)
    recorded_at: datetime
