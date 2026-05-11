"""
Local persistent cache of lesson credentials for a single teacher.

Stored at ~/.cadence/lessons.yaml so that teachers don't need to manage
environment variables or copy-paste tokens between notebooks. Each entry:

    "Week 3: Fibonacci":
      lesson_id: <uuid>
      join_code: soup-river-42
      teacher_token: <random>
      api_url: http://localhost:8000
      dashboard_url: http://localhost:8000/teacher/live?token=...
"""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # PyYAML is already a dependency
except ImportError:  # pragma: no cover
    yaml = None


CONFIG_DIR = Path(os.getenv("CADENCE_CONFIG_DIR", str(Path.home() / ".cadence")))
LESSONS_FILE = CONFIG_DIR / "lessons.yaml"


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load() -> Dict[str, Dict[str, Any]]:
    if not LESSONS_FILE.exists() or yaml is None:
        return {}
    try:
        with LESSONS_FILE.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(store: Dict[str, Dict[str, Any]]) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required to persist lesson credentials")
    _ensure_dir()
    with LESSONS_FILE.open("w", encoding="utf-8") as f:
        yaml.safe_dump(store, f, sort_keys=False)
    # 0600 so other users on a shared machine can't read teacher_tokens
    try:
        os.chmod(LESSONS_FILE, 0o600)
    except OSError:
        pass


def get(name: str) -> Optional[Dict[str, Any]]:
    return _load().get(name)


def put(name: str, **fields: Any) -> None:
    """Upsert a lesson entry (kind='lesson' is implied for legacy entries)."""
    store = _load()
    existing = store.get(name, {})
    existing.update(fields)
    existing.setdefault("kind", "lesson")
    store[name] = existing
    _save(store)


def put_course(name: str, **fields: Any) -> None:
    """Upsert a course entry (kind='course')."""
    store = _load()
    existing = store.get(name, {})
    existing.update(fields)
    existing["kind"] = "course"
    store[name] = existing
    _save(store)


def get_course(name: str) -> Optional[Dict[str, Any]]:
    entry = _load().get(name)
    if not entry:
        return None
    if entry.get("kind") != "course":
        return None
    return entry


def remove(name: str) -> None:
    store = _load()
    if name in store:
        del store[name]
        _save(store)


def list_names() -> list:
    return list(_load().keys())


def list_by_kind(kind: str) -> list:
    return [
        name for name, entry in _load().items()
        if entry.get("kind", "lesson") == kind
    ]


# ----------------------------------------------------------------------------
# Human-readable join code generator
# ----------------------------------------------------------------------------

_WORDS = [
    "amber", "apple", "arrow", "aspen", "auburn", "azure",
    "basil", "bison", "blaze", "bloom", "breeze", "bronze",
    "canyon", "cedar", "cherry", "clover", "cobalt", "comet",
    "copper", "coral", "crane", "crimson", "crystal", "dahlia",
    "daisy", "delta", "desert", "dune", "ember", "fable",
    "falcon", "fern", "finch", "flint", "forest", "garnet",
    "ginger", "glacier", "hazel", "heron", "honey", "horizon",
    "indigo", "ivory", "jade", "jasmine", "juniper", "kestrel",
    "lagoon", "lemon", "lilac", "linen", "lotus", "lupine",
    "mango", "maple", "marble", "marigold", "meadow", "midnight",
    "mint", "moss", "mulberry", "nectar", "nimbus", "oasis",
    "ocean", "olive", "onyx", "opal", "orchid", "pebble",
    "pine", "plum", "poppy", "prairie", "quartz", "quill",
    "raven", "rhapsody", "ribbon", "river", "rose", "saffron",
    "sage", "sapphire", "shadow", "silver", "solstice", "sparrow",
    "spruce", "storm", "sunny", "sycamore", "tangerine", "thistle",
    "topaz", "tulip", "twilight", "umber", "velvet", "violet",
    "walnut", "willow", "wisteria", "zephyr",
]


def generate_join_code(rng: Optional[random.Random] = None) -> str:
    """Return a code like 'soup-river-42' — memorable, readable aloud."""
    r = rng or random.SystemRandom()
    a = r.choice(_WORDS)
    b = r.choice(_WORDS)
    n = r.randint(10, 99)
    return f"{a}-{b}-{n}"
