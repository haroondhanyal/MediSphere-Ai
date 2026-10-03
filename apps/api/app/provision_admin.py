"""Provision one first hospital administrator without creating demo accounts."""
import os

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Organization, OrganizationMembership, OrganizationSettings, OrganizationSubscription, Permission, Role, User
from app.seed import ROLE_PERMISSIONS
from app.schemas import normalize_email
from app.security import hash_password


def provision_admin(db: Session, email: str, password: str):
    email = normalize_email(email.strip())
    if len(password) < 16:
        raise ValueError("Bootstrap password must have at least 16 characters")
    if db.query(User).filter_by(email=email).first():
        raise ValueError("An account with this email already exists; bootstrap stopped without changing it")

    organization = db.query(Organization).filter_by(slug="medisphere-health").first()
    if not organization:
        organization = Organization(name="MediSphere AI Medical Center", slug="medisphere-health")
        db.add(organization)
        db.flush()
    if not organization.settings:
        organization.settings = OrganizationSettings(timezone="UTC", default_locale="en")
    if not organization.subscription:
        organization.subscription = OrganizationSubscription(plan_code="standard", status="active")

    permission_codes = ROLE_PERMISSIONS["hospital_admin"]
    permissions = []
    for code in permission_codes:
        permission = db.query(Permission).filter_by(code=code).first()
        if not permission:
            permission = Permission(code=code, description=code.replace(":", " "))
            db.add(permission)
        permissions.append(permission)
    role = db.query(Role).filter_by(name="hospital_admin").first()
    if not role:
        role = Role(name="hospital_admin", description="Hospital Administrator")
        db.add(role)
    role.permissions = permissions
    user = User(email=email, full_name="MediSphere Administrator", password_hash=hash_password(password))
    db.add(user)
    db.flush()
    db.add(OrganizationMembership(organization_id=organization.id, user_id=user.id, role=role))
    db.commit()
    return user


def main():
    email = os.getenv("SEED_ADMIN_EMAIL", "").strip()
    password = os.getenv("SEED_ADMIN_PASSWORD", "")
    if not email or not password:
        raise SystemExit("Set SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD for the one-time bootstrap")
    with SessionLocal() as db:
        try:
            user = provision_admin(db, email, password)
        except Exception:
            db.rollback()
            raise
    print(f"Provisioned initial administrator {user.email} for medisphere-health.")


if __name__ == "__main__":
    main()
