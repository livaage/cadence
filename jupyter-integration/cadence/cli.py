"""
Command-line interface for managing locally-cached Cadence credentials.

Operates on ~/.cadence/lessons.yaml — listing, forgetting, and rotating the
teacher tokens stored there. None of the commands talk to the network except
`rotate`, which calls the backend to mint a new token.
"""

from __future__ import annotations

import os

import click

from . import lesson_store
from .api import CadenceAPI


@click.group()
@click.version_option(package_name="cadence-edu")
def main():
    """Cadence credential helpers (operates on ~/.cadence/lessons.yaml)."""


@main.group()
def lessons():
    """List, forget, or rotate locally-cached lesson/course credentials."""


@lessons.command("list")
def lessons_list():
    """Show every lesson and course stored in ~/.cadence/lessons.yaml."""
    store = lesson_store._load()
    if not store:
        click.echo("(no cached lessons or courses)")
        return
    for name, entry in store.items():
        kind = entry.get("kind", "lesson")
        join = entry.get("join_code", "?")
        api = entry.get("api_url", "?")
        token = entry.get("teacher_token", "")
        masked = f"{token[:6]}…{token[-4:]}" if len(token) > 10 else "(missing)"
        icon = "📚" if kind == "course" else "📓"
        click.echo(f"{icon} {kind:7} {name}")
        click.echo(f"     join_code={join}  api={api}  teacher_token={masked}")


@lessons.command("forget")
@click.argument("name")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def lessons_forget(name, yes):
    """Remove a stale entry from ~/.cadence/lessons.yaml.

    Use this when the server-side lesson is gone (e.g. you ran
    `docker compose down -v`) so the local cache no longer matches reality.
    The server state is not touched.
    """
    entry = lesson_store._load().get(name)
    if not entry:
        click.echo(f"❌ No cached entry named {name!r}.")
        raise SystemExit(1)
    if not yes:
        kind = entry.get("kind", "lesson")
        click.confirm(
            f"Remove cached {kind} {name!r} from {lesson_store.LESSONS_FILE}?",
            abort=True,
        )
    lesson_store.remove(name)
    click.echo(f"✅ Forgot {name!r}.")


@lessons.command("rotate")
@click.argument("name")
@click.option("--course", is_flag=True, help="The entry is a course, not a lesson.")
@click.option("--also-join-code", is_flag=True,
              help="Also rotate the join_code. Disconnects existing students.")
def lessons_rotate(name, course, also_join_code):
    """Mint a fresh teacher_token for a cached lesson or course.

    The backend revokes the old token; the local cache is updated with the new
    one. Use --also-join-code only when you need a hard revocation.
    """
    entry = lesson_store._load().get(name)
    if not entry:
        click.echo(f"❌ No cached entry named {name!r}.")
        raise SystemExit(1)
    if not entry.get("teacher_token"):
        click.echo(f"❌ Cached entry {name!r} has no teacher_token.")
        raise SystemExit(1)

    kind = entry.get("kind", "lesson")
    inferred_course = kind == "course"
    if course and not inferred_course:
        click.echo(f"❌ --course passed but {name!r} is cached as a lesson.")
        raise SystemExit(1)

    api = CadenceAPI(base_url=entry.get("api_url") or os.getenv("CADENCE_API_URL"))
    try:
        if inferred_course:
            resp = api.rotate_course_token(entry["teacher_token"], rotate_join_code=also_join_code)
            lesson_store.put_course(
                resp["name"],
                course_id=resp["id"],
                join_code=resp["join_code"],
                teacher_token=resp["teacher_token"],
                api_url=api.base_url,
            )
        else:
            resp = api.rotate_lesson_token(entry["teacher_token"], rotate_join_code=also_join_code)
            lesson_store.put(
                resp["name"],
                lesson_id=resp["id"],
                join_code=resp["join_code"],
                teacher_token=resp["teacher_token"],
                api_url=api.base_url,
            )
    except Exception as e:
        click.echo(f"❌ Rotation failed: {e}")
        raise SystemExit(1)

    click.echo(f"✅ Rotated {kind} {name!r}.")
    click.echo(f"   new join_code = {resp['join_code']}")
    click.echo(f"   new dashboard = {api.base_url.replace(':8000', ':3000').rstrip('/')}"
               f"/teacher/{'course' if inferred_course else 'live'}"
               f"?token={resp['teacher_token']}")


if __name__ == "__main__":
    main()
