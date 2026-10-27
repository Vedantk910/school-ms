"""Auth: login -> access/refresh JWT; /auth/me; /auth/refresh."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.audit import record
from app.db import get_session
from app.dependencies import current_user
from app.models import User
from app.security import create_tokens, decode_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


def _auth_user(session: Session, username: str, password: str) -> User:
    u = session.exec(select(User).where(User.username == username)).first()
    if u is None or not verify_password(password, u.password_hash) or not u.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return u


@router.post("/login")
def login(body: LoginIn, session: Session = Depends(get_session)):
    u = _auth_user(session, body.username, body.password)
    access, refresh = create_tokens(u.username, u.role, u.id)
    record(session, actor=u.username, action="login", resource=f"user#{u.id}")
    return {"access_token": access, "refresh_token": refresh,
            "token_type": "bearer", "role": u.role, "uid": u.id, "username": u.username}


@router.post("/refresh")
def refresh(body: RefreshIn, session: Session = Depends(get_session)):
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token")
    u = session.get(User, int(payload["uid"]))
    if u is None or not u.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    access, new_refresh = create_tokens(u.username, u.role, u.id)
    return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"}


@router.get("/me")
def me(u: User = Depends(current_user)) -> dict:
    return {"username": u.username, "role": u.role, "uid": u.id, "full_name": u.full_name}
