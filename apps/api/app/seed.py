import os
from datetime import date

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Organization, OrganizationMembership, OrganizationSettings, OrganizationSubscription, Patient, Permission, Role, User
from app.security import hash_password

ROLE_PERMISSIONS = {
    "super_admin": ["*"],
    "hospital_admin": ["patients:read", "patients:write", "appointments:read", "appointments:write", "encounters:read", "encounters:write", "prescriptions:read", "prescriptions:write", "pharmacy:write", "labs:read", "labs:write", "radiology:read", "radiology:write", "insurance:read", "insurance:write", "claims:read", "claims:write", "authorizations:read", "authorizations:write", "billing:read", "billing:write", "monitoring:read", "monitoring:write", "users:read", "users:write", "messages:read", "messages:write", "notifications:read", "notifications:write", "telehealth:read", "telehealth:write", "reports:read"],
    "doctor": ["patients:read", "appointments:read", "encounters:read", "encounters:write", "prescriptions:read", "prescriptions:write", "labs:read", "labs:write", "radiology:read", "radiology:write", "authorizations:read", "authorizations:write", "monitoring:read", "monitoring:write", "messages:read", "messages:write", "notifications:read", "notifications:write", "telehealth:read", "telehealth:write"],
    "nurse": ["patients:read", "appointments:read", "encounters:read", "encounters:write", "labs:read", "monitoring:read", "monitoring:write", "messages:read", "messages:write", "notifications:read", "telehealth:read"],
    "receptionist": ["patients:read", "appointments:read", "appointments:write"],
    "lab_technician": ["patients:read", "labs:read", "labs:write"],
    "radiologist": ["patients:read", "radiology:read", "radiology:write"],
    "pharmacist": ["patients:read", "prescriptions:read", "pharmacy:write"],
    "insurance_reviewer": ["insurance:read", "claims:read", "claims:write", "authorizations:read", "authorizations:write"],
    "billing_officer": ["claims:read", "claims:write", "authorizations:read", "billing:read", "billing:write"],
    "patient": ["appointments:read"],
    "support_agent": ["users:read"],
}

# Synthetic directory entries for local demos only; these are not real people.
DEMO_PATIENTS = [
    ("Amina", "Khan", "female", "1988-04-12"),
    ("Omar", "Raza", "male", "1976-09-03"),
    ("Zara", "Ahmed", "female", "1995-01-26"),
    ("Hamza", "Iqbal", "male", "2001-07-18"),
    ("Noor", "Hassan", "female", "1969-11-09"),
    ("Bilal", "Malik", "male", "1982-02-14"),
    ("Mina", "Siddiqui", "female", "1992-04-10"),
    ("Daniyal", "Shah", "male", "1958-06-21"),
    ("Sara", "Farooq", "female", "2005-08-30"),
    ("Yusuf", "Butt", "male", "1947-12-05"),
    ("Hira", "Qureshi", "female", "1973-03-17"),
    ("Adeel", "Chaudhry", "male", "1999-10-11"),
    ("Layla", "Noor", "female", "1985-05-24"),
    ("Sameer", "Akhtar", "male", "1961-01-08"),
    ("Nadia", "Rehman", "female", "2014-09-15"),
]


def seed(db: Session):
    organization = db.query(Organization).filter_by(slug="medisphere-health").first()
    if not organization:
        organization = Organization(name="MediSphere AI Medical Center", slug="medisphere-health")
        db.add(organization)
    db.flush()
    if not organization.settings:
        organization.settings = OrganizationSettings(timezone="Asia/Karachi", default_locale="en")
    if not organization.subscription:
        organization.subscription = OrganizationSubscription(plan_code="demo", status="trial")
    permissions = {}
    for code in sorted({item for items in ROLE_PERMISSIONS.values() for item in items if item != "*"}):
        permissions[code] = db.query(Permission).filter_by(code=code).first() or Permission(code=code, description=code.replace(":", " "))
        db.add(permissions[code])
    db.flush()
    roles = {}
    for name, codes in ROLE_PERMISSIONS.items():
        role = db.query(Role).filter_by(name=name).first() or Role(name=name, description=name.replace("_", " ").title())
        role.permissions = [permissions[code] for code in codes if code != "*"]
        db.add(role)
        roles[name] = role
    db.flush()
    password = os.getenv("SEED_ADMIN_PASSWORD", "MediSphere-Demo-2026!")
    demo_users = {
        "superadmin@medisphere.local": ("MediSphere AI Super Admin", "super_admin"),
        os.getenv("SEED_ADMIN_EMAIL", "admin@medisphere.local").lower(): ("MediSphere AI Administrator", "hospital_admin"),
        "doctor@medisphere.local": ("Demo Doctor", "doctor"),
        "nurse@medisphere.local": ("Demo Nurse", "nurse"),
        "insurance@medisphere.local": ("Demo Insurance Reviewer", "insurance_reviewer"),
        "pharmacy@medisphere.local": ("Demo Pharmacist", "pharmacist"),
        "lab@medisphere.local": ("Demo Lab Technician", "lab_technician"),
    }
    for email, (full_name, role_name) in demo_users.items():
        user = db.query(User).filter_by(email=email).first()
        if not user:
            user = User(email=email, full_name=full_name, password_hash=hash_password(password))
            db.add(user)
            db.flush()
        membership = db.query(OrganizationMembership).filter_by(organization_id=organization.id, user_id=user.id).first()
        if not membership:
            db.add(OrganizationMembership(organization=organization, user=user, role=roles[role_name]))
        elif membership.role_id != roles[role_name].id:
            membership.role_id = roles[role_name].id
    # Keep the old local patient demo login disabled if a developer seeded it earlier.
    legacy_patient_user = db.query(User).filter_by(email="patient@medisphere.local").first()
    if legacy_patient_user:
        legacy_patient_user.is_active = False
    admin = db.query(User).filter_by(email=os.getenv("SEED_ADMIN_EMAIL", "admin@medisphere.local").lower()).one()
    for index, (given_name, family_name, gender, birth_date) in enumerate(DEMO_PATIENTS, start=1):
        mrn = f"DEMO-{index:04d}"
        if not db.query(Patient).filter_by(organization_id=organization.id, mrn=mrn).first():
            db.add(Patient(
                organization_id=organization.id,
                mrn=mrn,
                given_name=given_name,
                family_name=family_name,
                gender=gender,
                birth_date=date.fromisoformat(birth_date),
                email=f"demo.patient{index:02d}@example.test",
                phone=f"+1-202-555-{index:04d}",
                created_by=admin.id,
            ))
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
    print("Local demo data seeded.")
