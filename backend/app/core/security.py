from typing import Optional

from fastapi import Header, HTTPException

from app.core.firebase import FIREBASE_ENABLED, verify_firebase_token


def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Expects a header like: Authorization: Bearer <firebase_id_token>
    Verifies the token and returns the decoded user info.
    """
    # Header(...) turned a *missing* Authorization header into a 422
    # validation error rather than a 401, so unauthenticated calls were
    # reported as malformed requests. Header(None) plus an explicit check
    # gives the correct status.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    if not FIREBASE_ENABLED:
        # Distinguish "this server has no auth configured" from "your token
        # is bad" — otherwise a missing service account key looks to the
        # frontend like every user's credentials are being rejected.
        raise HTTPException(
            status_code=503,
            detail=(
                "Authentication is not configured on this server. Set "
                "FIREBASE_CREDENTIALS_JSON in backend/.env, or place a service "
                "account key at backend/firebase-credentials.json."
            ),
        )

    token = authorization.split(" ", 1)[1]

    try:
        decoded_token = verify_firebase_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return decoded_token
