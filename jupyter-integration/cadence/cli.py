"""
Command-line interface for managing locally-cached Cadence credentials.

Operates on ~/.cadence/lessons.yaml — listing, forgetting, and rotating the
teacher tokens stored there. None of the commands talk to the network except
`rotate`, which calls the backend to mint a new token.
"""

from __future__ import annotations

import os

import click
import nbformat as nbf

from . import lesson_store, notebook_starters
from .api import CadenceAPI


@click.group()
@click.version_option(package_name="cadence-edu")
def main():
    """Cadence credential helpers and notebook scaffolds."""


@main.group()
def new():
    """Mint a starter Jupyter notebook with Cadence wiring pre-populated."""


def _write_starter(nb, out_path: str, force: bool) -> None:
    if os.path.exists(out_path) and not force:
        click.echo(f"❌ {out_path} already exists. Re-run with --force to overwrite.")
        raise SystemExit(1)
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    click.echo(f"✅ Wrote {out_path}")
    click.echo("   Open it with `jupyter notebook` (or your IDE) and run the cells in order.")


@new.command("teacher")
@click.option("--out", "out_path", default="teacher-setup.ipynb",
              help="Output path for the notebook (default: ./teacher-setup.ipynb).")
@click.option("--name", "lesson_name", default="My Lesson",
              help="Lesson name pre-filled into %cadence_create_lesson.")
@click.option("--force", is_flag=True, help="Overwrite the file if it already exists.")
def new_teacher(out_path, lesson_name, force):
    """Write a starter teacher notebook (lesson creation + checkpoint registration)."""
    _write_starter(notebook_starters.teacher_starter(lesson_name=lesson_name), out_path, force)


@new.command("student")
@click.option("--out", "out_path", default="student.ipynb",
              help="Output path for the notebook (default: ./student.ipynb).")
@click.option("--name", "lesson_name", default="My Lesson",
              help="Lesson name pre-filled into the notebook title.")
@click.option("--force", is_flag=True, help="Overwrite the file if it already exists.")
def new_student(out_path, lesson_name, force):
    """Write a starter student notebook (session + example check)."""
    _write_starter(notebook_starters.student_starter(lesson_name=lesson_name), out_path, force)


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
