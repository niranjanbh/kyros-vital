import secrets

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

_security = HTTPBasic()


def verify_admin(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    """Validate HTTP Basic credentials against env-var-configured admin account.

    Constant-time username comparison prevents timing oracle on the username.
    bcrypt.checkpw does constant-time comparison internally.
    Returns the admin username on success.
    """
    username_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.ADMIN_USERNAME.encode("utf-8"),
    )

    # Guard: if no hash is configured at all, reject immediately
    if not settings.ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin access not configured.",
            headers={"WWW-Authenticate": "Basic"},
        )

    try:
        password_ok = bcrypt.checkpw(
            credentials.password.encode("utf-8"),
            settings.ADMIN_PASSWORD_HASH.encode("utf-8"),
        )
    except Exception:
        password_ok = False

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
