import json
import logging
import os

import firebase_admin
from firebase_admin import credentials, auth

from app.core.config import settings

logger = logging.getLogger("aaroh.firebase")

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# backend/firebase-credentials.json — resolved relative to this file so it
# works no matter which directory uvicorn was started from.
_CREDENTIALS_FILE = os.path.abspath(
    os.path.join(_THIS_DIR, "..", "..", "firebase-credentials.json")
)


def _load_credentials():
    """
    Returns a firebase_admin credential, or None if none is configured.

    This used to call credentials.Certificate("firebase-credentials.json")
    unconditionally at import time and raise FileNotFoundError when no
    service account key was present — which took the whole ASGI app down
    before it could serve a single request, including the unauthenticated
    /health and /docs routes. Missing credentials now degrade to "auth is
    unavailable" (a clean 401 on protected routes) rather than "the server
    won't boot".
    """
    if settings.firebase_credentials_json:
        try:
            return credentials.Certificate(json.loads(settings.firebase_credentials_json))
        except Exception:
            logger.exception(
                "Failed to load FIREBASE_CREDENTIALS_JSON (malformed JSON, or a "
                "mangled private_key from being pasted into a single-line env "
                "var box) — falling back to auth disabled."
            )
            return None
    if os.path.exists(_CREDENTIALS_FILE):
        try:
            return credentials.Certificate(_CREDENTIALS_FILE)
        except Exception:
            logger.exception(
                "Failed to load firebase-credentials.json — falling back to "
                "auth disabled."
            )
            return None
    return None


_cred = _load_credentials()

if _cred is not None and not firebase_admin._apps:
    firebase_admin.initialize_app(_cred)

FIREBASE_ENABLED = _cred is not None


def verify_firebase_token(id_token: str):
    if not FIREBASE_ENABLED:
        raise RuntimeError(
            "Firebase is not configured on this server. Set "
            "FIREBASE_CREDENTIALS_JSON in backend/.env, or place a service "
            "account key at backend/firebase-credentials.json."
        )
    return auth.verify_id_token(id_token)
