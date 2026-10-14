from datetime import datetime, timezone
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models import AuthSession, User, Employee
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    if not payload or payload.get("token_type") != "access":
        raise HTTPException(401, "Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(401, "Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    session_id = payload.get("sid")
    if not isinstance(session_id, str):
        raise HTTPException(401, "Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    user = (
        db.query(User)
        .join(AuthSession, AuthSession.user_id == User.id)
        .filter(
            User.id == user_id,
            User.is_active.is_(True),
            AuthSession.id == session_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utc_now(),
        )
        .first()
    )
    if not user:
        raise HTTPException(401, "User is inactive or session is no longer valid", headers={"WWW-Authenticate": "Bearer"})
    return user
def require_roles(*roles):
    def checker(user: User = Depends(current_user)):
        if user.role not in roles: raise HTTPException(403, "Insufficient permissions")
        return user
    return checker
def current_employee(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Employee:
    employee = db.query(Employee).filter(Employee.user_id == user.id, Employee.is_active.is_(True)).first()
    if not employee: raise HTTPException(404, "Employee profile not found")
    return employee
