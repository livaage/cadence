"""Round-trip test for the scaffold tool.

Synthesizes a teacher notebook in /tmp, runs scaffold against it (CLI + the
library), reads the resulting student notebook back, and asserts shape.
Does NOT hit the network — uses an explicit --join-code so no lesson_store
lookup is needed.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import nbformat as nbf

from cadence import scaffold


def _make_teacher_notebook(path: Path) -> None:
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3"}
    # Setup cell (teacher-only): registers checkpoints. Should NOT appear in student.
    nb.cells.append(nbf.v4.new_code_cell(
        '%cadence_create_lesson "Week 3 — Stats"\n'
        '%%cadence_register_yaml\n'
        '- id: mean_value\n'
        '  comparator: exact\n'
        '  expected: 49.5\n'
    ))
    # Setup cell marked as solution (imports/data students need verbatim).
    nb.cells.append(nbf.v4.new_code_cell(
        "# cadence:solution\n"
        "import numpy as np\n"
        "data = np.arange(100)\n"
    ))
    # Task markdown (kept).
    nb.cells.append(nbf.v4.new_markdown_cell(
        "<!-- cadence:task -->\n"
        "## Exercise 1: Compute the mean\n"
        "Find the mean of the array `data`. Expected ≈ 49.5.\n"
    ))
    # Solution (becomes stub) with two checks in one cell.
    nb.cells.append(nbf.v4.new_code_cell(
        "mean = data.mean()\n"
        'check("mean_value", mean)\n'
        "median = float(np.median(data))\n"
        'check("median_value", median)\n'
    ))
    # Plain markdown with a HEADING — heading-only sections carry through to
    # the student notebook so the outline matches the teacher's.
    nb.cells.append(nbf.v4.new_markdown_cell(
        "## Part B — More exercises\n"
    ))
    # Pure prose without a heading or task marker — teacher-private, skipped.
    nb.cells.append(nbf.v4.new_markdown_cell(
        "_Teacher aside: students who skip the seed will be confused._\n"
    ))
    # Another task + exercise pair, with a `cadence.check` (attribute form).
    nb.cells.append(nbf.v4.new_markdown_cell(
        "<!-- cadence:task -->\n"
        "## Exercise 2: Find the max\n"
        "Compute the maximum value of `data`.\n"
    ))
    nb.cells.append(nbf.v4.new_code_cell(
        "import cadence\n"
        "max_value = int(data.max())\n"
        'cadence.check("max_value", max_value)\n'
    ))
    # Worked-solution reference cell shown to students AFTER they try it.
    # Has both the marker AND check() calls — marker wins, cell is copied verbatim.
    nb.cells.append(nbf.v4.new_code_cell(
        "# cadence:solution\n"
        "# Reference solution\n"
        "max_value = int(data.max())\n"
        'cadence.check("max_value", max_value)  # should match\n'
    ))
    # Scratch cell with no check and no marker — should be skipped.
    nb.cells.append(nbf.v4.new_code_cell(
        "# Just exploration\n"
        "print(data.std())\n"
    ))
    nbf.write(nb, str(path))


def _assert_student_shape(student_path: Path, expected_join_code: str) -> None:
    nb = nbf.read(str(student_path), as_version=4)
    cells = nb.cells
    # 1 intro markdown + 1 session header + 1 setup-solution + 2 task markdowns
    # + 2 exercise stubs + 1 section-heading markdown + 1 reference-solution = 9
    assert len(cells) == 9, f"expected 9 cells, got {len(cells)}: {[c.cell_type for c in cells]}"
    # Intro markdown is now a STYLED HTML BOX so it stands out from teacher prose.
    assert cells[0].cell_type == "markdown"
    assert "<div" in cells[0].source, "intro should be a styled HTML box"
    assert "border" in cells[0].source, "intro box should have a visible border"
    assert "check(" in cells[0].source, "intro should mention check()"
    assert "submit_image" in cells[0].source, "intro should mention submit_image()"
    assert "mark_done" in cells[0].source, "intro should mention mark_done() for reflections"
    assert "show_hint" in cells[0].source, "intro should mention show_hint()"
    cells = cells[1:]  # rest of the layout shifts down by one
    # Header
    assert cells[0].cell_type == "code"
    assert "%load_ext cadence" in cells[0].source
    assert f"%cadence_session {expected_join_code}" in cells[0].source
    # Setup solution: copied verbatim, marker line stripped, no leading blank
    assert cells[1].cell_type == "code"
    assert "import numpy as np" in cells[1].source
    assert "data = np.arange(100)" in cells[1].source
    assert "cadence:solution" not in cells[1].source, "marker line should be stripped"
    assert not cells[1].source.startswith("\n"), "stripped marker left a leading blank line"
    # Task 1
    assert cells[2].cell_type == "markdown"
    assert "Exercise 1" in cells[2].source
    # Exercise 1 stub: two checks, no solution code
    assert cells[3].cell_type == "code"
    assert 'check("mean_value", ...)' in cells[3].source
    assert 'check("median_value", ...)' in cells[3].source
    assert "data.mean()" not in cells[3].source, "solution code leaked into student"
    # Section heading markdown (## Part B) carries across to student.
    assert cells[4].cell_type == "markdown"
    assert "Part B" in cells[4].source
    # Task 2 (after the section heading)
    assert cells[5].cell_type == "markdown"
    assert "Exercise 2" in cells[5].source
    # Exercise 2 stub: cadence.check attribute form should also be detected
    assert cells[6].cell_type == "code"
    assert 'check("max_value", ...)' in cells[6].source
    assert "data.max()" not in cells[6].source
    # Reference solution: marker + check present together → solution wins
    assert cells[7].cell_type == "code"
    assert "Reference solution" in cells[7].source
    assert "data.max()" in cells[7].source, "solution body should be preserved when marker is present"
    assert "cadence:solution" not in cells[7].source, "marker line should be stripped"
    # Pure-prose teacher asides (no heading, no task marker) stay teacher-only.
    for c in cells:
        if c.cell_type == "markdown":
            assert "Teacher aside" not in c.source, "private teacher aside leaked"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        teacher = tmp_path / "teacher.ipynb"
        student = tmp_path / "teacher_student.ipynb"
        _make_teacher_notebook(teacher)

        # 1) Library API
        result = scaffold.scaffold(
            src_path=teacher,
            out_path=student,
            join_code="abc-def-ghi",
        )
        assert result.n_exercises == 2, f"expected 2 exercise stubs, got {result.n_exercises}"
        assert result.n_tasks == 2, f"expected 2 task descriptions, got {result.n_tasks}"
        assert result.n_solutions == 2, f"expected 2 solution cells, got {result.n_solutions}"
        # Only the stubbed exercises count toward checkpoint_ids — the second
        # max_value occurrence is inside the marker-tagged reference solution,
        # which is copied verbatim, not extracted.
        assert result.checkpoint_ids == ["mean_value", "median_value", "max_value"], result.checkpoint_ids
        assert result.lesson_name == "Week 3 — Stats", result.lesson_name
        _assert_student_shape(student, "abc-def-ghi")
        print("✓ library API: 2 exercises, 2 tasks, 2 solutions, 3 checkpoint ids")

        # 2) CLI
        student.unlink()
        rc = subprocess.run(
            [sys.executable, "-m", "cadence.cli", "scaffold",
             str(teacher), "--out", str(student), "--join-code", "xyz-789",
             "--name", "student-name"],
            check=False,
        ).returncode
        assert rc == 0, f"cli rc={rc}"
        _assert_student_shape(student, "xyz-789")
        print("✓ CLI subcommand round-trips and produces identical shape")

        # 3) Error path: missing join code, no cached lesson
        empty_nb = tmp_path / "empty.ipynb"
        nb = nbf.v4.new_notebook()
        nb.cells.append(nbf.v4.new_code_cell("# nothing here\n"))
        nbf.write(nb, str(empty_nb))
        try:
            scaffold.scaffold(src_path=empty_nb)
        except ValueError as e:
            assert "Could not auto-detect a join code" in str(e), str(e)
            print("✓ helpful error when join code is missing")
        else:
            raise AssertionError("expected ValueError for missing join code")

        # 4) detect_current_notebook honors JPY_SESSION_NAME
        prev = os.environ.get("JPY_SESSION_NAME")
        try:
            os.environ["JPY_SESSION_NAME"] = str(teacher)
            found = scaffold.detect_current_notebook()
            assert found == teacher, f"expected {teacher}, got {found}"
            print("✓ detect_current_notebook picks up JPY_SESSION_NAME")
        finally:
            if prev is None:
                os.environ.pop("JPY_SESSION_NAME", None)
            else:
                os.environ["JPY_SESSION_NAME"] = prev

        # 5) The new "task marker carries the checkpoint id" flow: teacher
        # writes solution code with NO check() call, and a task marker like
        # <!-- cadence:task my.checkpoint -->. The student stub still gets
        # check("my.checkpoint", ...) inserted.
        nb_with_id = nbf.v4.new_notebook()
        nb_with_id.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3"}
        nb_with_id.cells.append(nbf.v4.new_code_cell(
            '%cadence_create_lesson "Implicit"\n'
        ))
        nb_with_id.cells.append(nbf.v4.new_markdown_cell(
            "<!-- cadence:task exercise.one -->\n"
            "## Exercise 1\n"
            "Compute the answer.\n"
        ))
        nb_with_id.cells.append(nbf.v4.new_code_cell(
            "answer = 42  # teacher's solution; no check() needed\n"
        ))
        # Code-cell marker style — different exercise, no preceding task marker.
        nb_with_id.cells.append(nbf.v4.new_code_cell(
            "# cadence:checkpoint exercise.two\n"
            "another = compute_something_else()\n"
        ))
        nb_with_id_path = tmp_path / "implicit.ipynb"
        nb_with_id_out = tmp_path / "implicit_student.ipynb"
        nbf.write(nb_with_id, str(nb_with_id_path))
        result = scaffold.scaffold(
            src_path=nb_with_id_path,
            out_path=nb_with_id_out,
            join_code="implicit-code",
        )
        assert result.checkpoint_ids == ["exercise.one", "exercise.two"], result.checkpoint_ids
        out_nb = nbf.read(str(nb_with_id_out), as_version=4)
        # 1 intro markdown + 1 session header + 1 task md + 1 exercise stub + 1 code-cell-marker exercise stub = 5
        assert len(out_nb.cells) == 5, [c.cell_type for c in out_nb.cells]
        assert out_nb.cells[0].cell_type == "markdown" and "check(" in out_nb.cells[0].source
        assert 'check("exercise.one", ...)' in out_nb.cells[3].source
        assert "answer = 42" not in out_nb.cells[3].source, "teacher's solution leaked"
        assert 'check("exercise.two", ...)' in out_nb.cells[4].source
        assert "cadence:checkpoint" not in out_nb.cells[4].source, "marker leaked"
        assert "compute_something_else" not in out_nb.cells[4].source
        print("✓ task-marker-with-id + code-cell marker both stub without check() in teacher")

        # NEW: lesson-name extraction also accepts %cadence_add_notebook so
        # scaffold doesn't fail with "no lesson magic found" when the teacher
        # generated the notebook via the course path.
        from cadence.scaffold import _extract_lesson_name
        ctx_nb = nbf.v4.new_notebook()
        ctx_nb.cells.append(nbf.v4.new_code_cell(
            '%load_ext cadence\n'
            '%cadence_course "Fall 2026"\n'
            '%cadence_add_notebook "Week 3 — Stats"\n'
        ))
        assert _extract_lesson_name(ctx_nb.cells) == "Week 3 — Stats"
        print("✓ scaffold picks up lesson name from %cadence_add_notebook (course path)")

        # NEW: `# cadence:starter` / `# cadence:end` block becomes the student
        # stub body instead of the default `# Your code here` placeholder.
        # Anything outside the starter block (the teacher's reference solution)
        # is dropped.
        starter_nb = tmp_path / "starter.ipynb"
        starter_out = tmp_path / "starter_student.ipynb"
        nb = nbf.v4.new_notebook()
        nb.cells = [
            nbf.v4.new_code_cell('%cadence_create_lesson "X"\n'),
            nbf.v4.new_markdown_cell("<!-- cadence:task ex.fit -->\n## Fit a line\nFit y = a*x + b.\n"),
            nbf.v4.new_code_cell(
                "# cadence:starter\n"
                "# Step 1: means\n"
                "x_bar = ...\n"
                "y_bar = ...\n"
                "# cadence:end\n"
                "\n"
                "# Below: teacher reference (stripped from student)\n"
                "x_bar = x.mean()\n"
                "y_bar = y.mean()\n"
                "answer = (x_bar, y_bar)\n"
            ),
        ]
        _changes, nb = nbf.validator.normalize(nb)
        nbf.write(nb, str(starter_nb))
        scaffold.scaffold(
            src_path=starter_nb, out_path=starter_out, join_code="abc",
        )
        out_nb = nbf.read(str(starter_out), as_version=4)
        # Find the stubbed exercise cell.
        ex_cell = next(c for c in out_nb.cells if c.cell_type == "code" and 'check("ex.fit"' in c.source)
        # The starter block is in there...
        assert "Step 1: means" in ex_cell.source, ex_cell.source
        assert "x_bar = ..." in ex_cell.source
        # ...the marker lines aren't (they were the delimiters).
        assert "cadence:starter" not in ex_cell.source
        assert "cadence:end" not in ex_cell.source
        # ...and the teacher's reference solution is gone.
        assert "x.mean()" not in ex_cell.source, "teacher reference leaked"
        assert "answer = (x_bar, y_bar)" not in ex_cell.source
        # ...and the check call is appended.
        assert ex_cell.source.rstrip().endswith('check("ex.fit", ...)')
        print("✓ starter block becomes student stub body; teacher reference stripped")

        # NEW: `cadence:hide` / `cadence:end` strips teacher-only regions from
        # the student notebook — works in BOTH markdown and code cells.
        hide_nb_path = tmp_path / "hide.ipynb"
        hide_out = tmp_path / "hide_student.ipynb"
        nb = nbf.v4.new_notebook()
        nb.cells = [
            nbf.v4.new_code_cell('%cadence_create_lesson "H"\n'),
            nbf.v4.new_markdown_cell(
                "<!-- cadence:task ex.one -->\n"
                "## Exercise\n"
                "Public task description.\n"
                "\n"
                "<!-- cadence:hide -->\n"
                "*Teacher note: this trips up most students because of axis=0.*\n"
                "<!-- cadence:end -->\n"
                "\n"
                "Keep reading: another public sentence.\n"
            ),
            nbf.v4.new_code_cell(
                "# cadence:checkpoint ex.one\n"
                "# cadence:hide\n"
                "# Teacher's pre-work — only relevant for self-test.\n"
                "calibration = preflight()\n"
                "# cadence:end\n"
                "answer = compute()\n"
            ),
        ]
        _changes, nb = nbf.validator.normalize(nb)
        nbf.write(nb, str(hide_nb_path))
        scaffold.scaffold(src_path=hide_nb_path, out_path=hide_out, join_code="x")
        out_nb = nbf.read(str(hide_out), as_version=4)
        md = next(c for c in out_nb.cells if c.cell_type == "markdown" and "Exercise" in c.source)
        assert "Public task description" in md.source
        assert "Keep reading" in md.source
        assert "Teacher note" not in md.source, "markdown hide block leaked into student"
        assert "cadence:hide" not in md.source, "hide marker leaked into student"
        assert "cadence:end" not in md.source
        # No `compute()` (it's in a stubbed exercise cell), but specifically
        # `preflight()` from the code hide block shouldn't appear anywhere.
        for c in out_nb.cells:
            if c.cell_type == "code":
                assert "preflight" not in c.source, "code hide block leaked"
                assert "cadence:hide" not in c.source
        print("✓ cadence:hide strips teacher-only regions from markdown AND code")

        # 6) detect_current_notebook returns None when there's nothing to detect
        prev = os.environ.pop("JPY_SESSION_NAME", None)
        try:
            # Not running under VSCode or a Jupyter server in this test, so all
            # three detection sources fail → graceful None.
            assert scaffold.detect_current_notebook() is None
            print("✓ detect_current_notebook returns None when undetectable")
        finally:
            if prev is not None:
                os.environ["JPY_SESSION_NAME"] = prev

    print("\nAll scaffold tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
