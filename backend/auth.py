"""Shared development-session authentication and role checks."""
from fastapi import Depends, Header, HTTPException
from typing import Optional

SESSIONS: dict[str, dict] = {}


def current_user(authorization: Optional[str] = Header(None)):
    token = authorization.removeprefix("Bearer ") if authorization else ""
    user = SESSIONS.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in to continue")
    return user


def require_customer(user=Depends(current_user)):
    if user["role"] != "CUSTOMER":
        raise HTTPException(status_code=403, detail="Customer access required")
    return user


def require_employee(user=Depends(current_user)):
    if user["role"] not in ("EMPLOYEE", "ADMIN"):
        raise HTTPException(status_code=403, detail="Employee access required")
    return user


def require_admin(user=Depends(current_user)):
    if user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user
