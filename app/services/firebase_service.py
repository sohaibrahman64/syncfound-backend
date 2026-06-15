from pathlib import Path
import os

import firebase_admin
from firebase_admin import credentials, auth


DEFAULT_FIREBASE_CREDENTIALS_FILE = "syncfound-fe04d-firebase-adminsdk-fbsvc-e58f0d76f8.json"


def initialize_firebase() -> None:
    if firebase_admin._apps:
        return

    credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH", DEFAULT_FIREBASE_CREDENTIALS_FILE)
    resolved_path = Path(credentials_path)

    if not resolved_path.is_absolute():
        resolved_path = Path.cwd() / resolved_path

    if not resolved_path.exists():
        raise RuntimeError(
            f"Firebase credentials file not found at: {resolved_path}. Set FIREBASE_CREDENTIALS_PATH correctly."
        )

    firebase_credentials = credentials.Certificate(str(resolved_path))
    firebase_admin.initialize_app(firebase_credentials)


def verify_firebase_id_token(firebase_token: str) -> dict:
    return auth.verify_id_token(firebase_token)
