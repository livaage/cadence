"""Starter notebooks for `cadence-cli new student / new teacher`.

Each builder returns an nbformat NotebookNode pre-populated with the minimum
Cadence wiring — `%load_ext cadence`, a session/lesson cell, a placeholder
exercise — so a teacher can `jupyter notebook` straight into editing real
content instead of copy-pasting magics from the docs.

Kept deliberately tiny: this is scaffolding, not a tutorial. The Guide and the
particle-physics demo notebooks cover the longer-form examples.
"""

from __future__ import annotations

import nbformat as nbf
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


def _stamp(nb: "nbf.NotebookNode") -> "nbf.NotebookNode":
    nb.metadata.setdefault("kernelspec", {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    })
    nb.metadata.setdefault("language_info", {"name": "python"})
    return nb


def teacher_starter(lesson_name: str = "My Lesson") -> "nbf.NotebookNode":
    """Minimal scaffold for a teacher setting up a new lesson.

    Order matches the typical first-run path: load magics, sign in (optional
    on self-hosted), mint the lesson, register checkpoints, self-test.
    """
    nb = new_notebook()
    nb.cells = [
        new_markdown_cell(
            f"# Teacher setup — {lesson_name}\n\n"
            "Run the cells below in order. They will:\n\n"
            "1. Load the Cadence magics.\n"
            "2. (Hosted only) sign you in so the lesson is attached to your account.\n"
            "3. Create a fresh lesson and print the join code + dashboard URL.\n"
            "4. Register checkpoints in bulk via YAML — edit the placeholders below.\n"
            "5. Self-test the expected answers before any student touches them.\n\n"
            "Once you're happy, give the printed join code to students. They can run "
            "`cadence-cli new student` to get a matching student-side starter."
        ),
        new_code_cell(
            "%load_ext cadence\n"
            "# Tip: type `%cadence_help` to see every Cadence magic in one place.\n"
        ),
        new_markdown_cell(
            "## Sign in (hosted Cadence only)\n\n"
            "Skip this cell if you're running Cadence locally with no auth. "
            "On the hosted service it prints a one-time URL or accepts your "
            "username/password — see <https://cadence-dash.com/guide>."
        ),
        new_code_cell("%cadence_login\n"),
        new_markdown_cell(
            "## Create the lesson\n\n"
            "This mints a join code (give it to students) and a teacher token "
            "(keep this private — it grants dashboard access)."
        ),
        new_code_cell(f'%cadence_create_lesson "{lesson_name}"\n'),
        new_markdown_cell(
            "## Register checkpoints\n\n"
            "Two equivalent forms are available — pick whichever reads better "
            "for the cell you're writing.\n\n"
            "**One-liner per checkpoint** (good for sketching a single check):\n\n"
            "```python\n"
            "%cadence_register example.first --comparator numeric --expected 49.5\n"
            "```\n\n"
            "**Block form** (good for several at once — same fields, no flag noise):"
        ),
        new_code_cell(
            "%%cadence_register_yaml\n"
            "- id: example.first\n"
            "  comparator: numeric\n"
            "  expected: {value: 49.5, tolerance: 0.001}\n"
            "  hint: average of 0..99\n"
            "  order: 1\n"
            "\n"
            "- id: example.reflect\n"
            "  comparator: manual\n"
            "  hint: Briefly describe what you observed.\n"
            "  allow_submissions: true\n"
            "  order: 2\n"
        ),
        new_markdown_cell(
            "## Self-test\n\n"
            "Submits the teacher's own expected answer for every auto-checked "
            "checkpoint — catches typos in `expected` and tolerance errors "
            "*before* any student sees them. Manual and regex checkpoints "
            "are skipped automatically."
        ),
        new_code_cell("%cadence_self_test\n"),
        new_markdown_cell(
            "## Next\n\n"
            "Open the dashboard URL printed above in another tab. Hand students "
            "the join code from the same output. Their starter notebook is "
            "`cadence-cli new student` away."
        ),
    ]
    return _stamp(nb)


def student_starter(lesson_name: str = "My Lesson") -> "nbf.NotebookNode":
    """Minimal scaffold for a student joining a lesson.

    Pre-fills the session line with placeholders and one example `check(...)`
    cell — enough to demonstrate the contract without imposing any specific
    lab content.
    """
    nb = new_notebook()
    nb.cells = [
        new_markdown_cell(
            f"# {lesson_name} — your notebook\n\n"
            "1. Replace `<JOIN_CODE>` with the code your teacher gave you.\n"
            "2. Replace `Your name here` with how you'd like to appear on the dashboard "
            "(a pseudonym like `birb_42` is fine).\n"
            "3. Work through the exercises below. Your teacher sees your progress live; "
            "you can see (and delete) everything they hold about you via "
            "`%cadence_my_data` / `%cadence_delete_my_data`."
        ),
        new_code_cell(
            "%load_ext cadence\n"
            '%cadence_session <JOIN_CODE> "Your name here"\n'
        ),
        new_markdown_cell(
            "## Exercise 1 — example\n\n"
            "Pretend the teacher asked: *compute the mean of `0, 1, …, 99`*. "
            "Replace this with the actual exercise your teacher wrote."
        ),
        new_code_cell(
            "import numpy as np\n"
            "\n"
            "answer = np.arange(100).mean()\n"
            "\n"
            "# The id below must match what the teacher registered.\n"
            'check("example.first", answer)\n'
        ),
        new_markdown_cell(
            "## Useful student commands\n\n"
            "- `show_hint(\"<id>\")` — peek the teacher's hint (once enough wrong attempts).\n"
            "- `show_solution(\"<id>\")` — see the worked solution (if the teacher enabled it).\n"
            "- `mark_done(\"<id>\")` — self-attest a manual / reflection checkpoint.\n"
            "- `%cadence_my_data` — see exactly what's stored about you.\n"
            "- `%cadence_help` — full cheatsheet of every Cadence magic."
        ),
    ]
    return _stamp(nb)
