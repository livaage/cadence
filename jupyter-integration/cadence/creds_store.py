"""Local persistent cache of the teacher's JWT.

Stored at ~/.cadence/credentials.yaml so teachers don't have to log in
every kernel restart. Separate file from lessons.yaml because credentials
have different sensitivity (compromising a JWT compromises every owned
course; compromising a lesson token only that lesson).

Schema:
    teacher_jwt: <jwt>
    teacher_username: <str>
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from .lesson_store import CONFIG_DIR, _ensure_dir

CREDS_FILE = CONFIG_DIR / "credentials.yaml"


def _load() -> Dict[str, Any]:
    if not CREDS_FILE.exists() or yaml is None:
        return {}
    try:
        with CREDS_FILE.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: Dict[str, Any]) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required to persist credentials")
    _ensure_dir()
    with CREDS_FILE.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    try:
        os.chmod(CREDS_FILE, 0o600)
    except OSError:
        pass


def get_jwt() -> Optional[str]:
    return _load().get("teacher_jwt")


def get_username() -> Optional[str]:
    return _load().get("teacher_username")


def set_credentials(jwt: str, username: Optional[str] = None) -> None:
    data: Dict[str, Any] = {"teacher_jwt": jwt}
    if username:
        data["teacher_username"] = username
    _save(data)


def clear() -> None:
    if CREDS_FILE.exists():
        try:
            CREDS_FILE.unlink()
        except OSError:
            pass
