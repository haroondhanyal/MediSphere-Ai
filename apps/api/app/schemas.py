from datetime import date, datetime
from base64 import b64decode
from binascii import Error as Base64Error
from typing import Literal

from email_validator import validate_email
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    organization_slug: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str) -> str:
        return normalize_email(value)


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)
    organization_name: str = Field(min_length=2, max_length=180)
    role_code: Literal["hospital_admin", "doctor", "nurse", "receptionist"]
    phone_e164: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    country_code: Literal["PK", "US", "GB", "IN"]
    region: str = Field(min_length=1, max_length=120)
    profile_image_data: str | None = Field(default=None, max_length=700_000)

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str) -> str:
        return normalize_email(value.strip())

    @field_validator("full_name", "organization_name", "region")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("profile_image_data")
    @classmethod
    def validate_profile_image(cls, value: str | None) -> str | None:
        if value is None:
            return None
        prefixes = {
            "data:image/png;base64,": b"\x89PNG\r\n\x1a\n",
            "data:image/jpeg;base64,": b"\xff\xd8\xff",
            "data:image/webp;base64,": b"RIFF",
        }
        prefix = next((item for item in prefixes if value.startswith(item)), None)
        if prefix is None:
            raise ValueError("Profile image must be PNG, JPEG, or WebP")
        try:
            image = b64decode(value[len(prefix):], validate=True)
        except Base64Error as exc:
            raise ValueError("Profile image data is invalid") from exc
        if len(image) > 512_000:
            raise ValueError("Profile image must be 512 KB or smaller")
        signature = prefixes[prefix]
        if not image.startswith(signature) or (prefix.startswith("data:image/webp") and image[8:12] != b"WEBP"):
            raise ValueError("Profile image data does not match its file type")
        return value


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, value: str) -> str:
        return normalize_email(value.strip())


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=12, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone_e164: str | None = None
    country_code: str | None = None
    region: str | None = None
    profile_image_data: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    user: UserResponse
    organization: str
    organization_slug: str | None = None
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
    phone: str | None = Field(default=None, max_length=40)
    role: str = Field(default="Practitioner", min_length=1, max_length=80)


class PractitionerResponse(PractitionerCreate):
    id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class PractitionerBatchCreate(BaseModel):
    practitioners: list[PractitionerCreate] = Field(min_length=1, max_length=30)


class OrganizationProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    logo_url: str | None = Field(default=None, max_length=2048)
    contact_phone: str | None = Field(default=None, max_length=40)


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


class MonitoringRuleCreate(BaseModel):
    metric: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=40)
    minimum: float | None = Field(default=None, allow_inf_nan=False)
    maximum: float | None = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.minimum is None and self.maximum is None:
            raise ValueError("Set at least one alert threshold")
        if self.minimum is not None and self.maximum is not None and self.minimum >= self.maximum:
            raise ValueError("Minimum threshold must be lower than maximum threshold")
        return self
