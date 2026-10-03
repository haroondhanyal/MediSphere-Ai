from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import OrganizationMembership, User
from app.security import decode_access_token


def get_current_context(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> tuple[User, OrganizationMembership]:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if not access_token:
        raise unauthorized
    try:
        payload = decode_access_token(access_token)
        user_id = int(payload["sub"])
        org_id = int(payload["org"])
    except Exception:
        raise unauthorized
    membership = (
        db.query(OrganizationMembership)
        .options(joinedload(OrganizationMembership.organization), joinedload(OrganizationMembership.role))
        .filter_by(user_id=user_id, organization_id=org_id)
        .first()
    )
    user = db.get(User, user_id)
    if not user or not user.is_active or not membership or payload.get("ver", 0) != user.session_version:
        raise unauthorized
    return user, membership


def require_permission(permission_code: str):
    def check(context=Depends(get_current_context)):
        user, membership = context
        if membership.role.name == "super_admin":
            return user, membership
        granted = {permission.code for permission in membership.role.permissions}
        if permission_code not in granted:
            raise HTTPException(status_code=403, detail="Permission denied")
        return user, membership
    return check
