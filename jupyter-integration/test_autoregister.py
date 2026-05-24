"""Round-trip test for %cadence_autoregister (the autoregister module).

Builds a synthetic vanilla teacher notebook, runs autoregister against it
with a fake kernel namespace, and checks that:
  * a setup cell with the YAML block is injected at the top
  * task markers are added to the right markdown cells
  * imports + unmarked setup cells get copied through verbatim
  * comparator inference handles int / float / str / list / bool / numpy
  * auto-all mode pairs every (markdown-heading + code) pair without markers
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import nbformat as nbf

from cadence import autoregister


def _build_manual_notebook(path: Path) -> None:
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3"}
    nb.cells = [
        nbf.v4.new_code_cell("import numpy as np\nrng = np.random.default_rng(7)\n"),
        nbf.v4.new_markdown_cell("## Exercise 1: Mean\nCompute the mean.\n"),
        nbf.v4.new_code_cell(
            "# cadence:checkpoint setup.mean\n"
            "# cadence:hint: try `.mean()`\n"
            "arr = np.arange(100)\n"
            "mean_value = arr.mean()\n"
        ),
        nbf.v4.new_markdown_cell("## Exercise 2: Row sums\nSum each row.\n"),
        nbf.v4.new_code_cell(
            "# cadence:checkpoint setup.row-sums\n"
            "M = np.arange(12).reshape(3, 4)\n"
            "row_sums = M.sum(axis=1).tolist()\n"
        ),
    ]
    _changes, nb = nbf.validator.normalize(nb)
    nbf.write(nb, str(path))


def _build_auto_notebook(path: Path) -> None:
    """Same content, but with NO `# cadence:checkpoint` markers — auto mode
    should pair every (heading + code) pair as an exercise."""
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3"}
    nb.cells = [
        nbf.v4.new_code_cell("import numpy as np\n"),  # pure imports — verbatim
        nbf.v4.new_markdown_cell("# Intro\nSome narrative without an exercise after.\n"),
        nbf.v4.new_markdown_cell("## Exercise 1: Mean of an arange\nFind the mean.\n"),
        nbf.v4.new_code_cell("arr = np.arange(100)\nmean_value = arr.mean()\n"),
        nbf.v4.new_markdown_cell("## Exercise 2: A boolean\n"),
        nbf.v4.new_code_cell("is_true = bool(2 + 2 == 4)\n"),
    ]
    _changes, nb = nbf.validator.normalize(nb)
    nbf.write(nb, str(path))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # ----------------------------- Manual marker mode -----------------------------
        manual_src = tmp_path / "manual.ipynb"
        manual_out = tmp_path / "manual_registered.ipynb"
        _build_manual_notebook(manual_src)
        user_ns = {
            "mean_value": 49.5,
            "row_sums": [6, 22, 38],
        }
        result = autoregister.autoregister(
            src_path=manual_src,
            user_ns=user_ns,
            out_path=manual_out,
            reveal_after_attempts=3,
        )
        assert result.mode == "manual", result.mode
        assert result.n_checkpoints == 2, result.n_checkpoints
        assert result.n_failed == 0, [c.error for c in result.checkpoints]
        assert [c.checkpoint_id for c in result.checkpoints] == [
            "setup.mean", "setup.row-sums"
        ]
        # Float → numeric, list → set
        mean_cp = result.checkpoints[0]
        assert mean_cp.comparator == "numeric", mean_cp.comparator
        assert mean_cp.expected["value"] == 49.5
        assert "tolerance" in mean_cp.expected
        assert mean_cp.hint == "try `.mean()`", mean_cp.hint
        rows_cp = result.checkpoints[1]
        assert rows_cp.comparator == "set", rows_cp.comparator
        assert rows_cp.expected["value"] == [6, 22, 38]

        out_nb = nbf.read(str(manual_out), as_version=4)
        # Setup cell: minimal — load_ext + create_lesson, NO yaml block.
        assert out_nb.cells[0].cell_type == "code"
        assert "%load_ext cadence" in out_nb.cells[0].source
        assert "%cadence_create_lesson" in out_nb.cells[0].source
        # The login hint should be in there but commented out so it's a no-op
        # until the teacher uncomments it.
        assert "# %cadence_login" in out_nb.cells[0].source, \
            "setup cell should carry a commented-out login hint for convenience"
        assert "%%cadence_register_yaml" not in out_nb.cells[0].source, \
            "registrations should be inline per-cell, not in a YAML block"
        # Imports cell preserved AND marked as cadence:solution so it carries
        # across to the student notebook when scaffold runs.
        imports_cell = next(c for c in out_nb.cells if c.cell_type == "code" and "import numpy as np" in c.source)
        assert "# cadence:solution" in imports_cell.source, \
            "setup/import cells should be marked as solution so students get them too"
        # Task marker injected on the markdown cells.
        md_one = next(c for c in out_nb.cells if c.cell_type == "markdown" and "Exercise 1" in c.source)
        assert "<!-- cadence:task setup.mean -->" in md_one.source
        md_two = next(c for c in out_nb.cells if c.cell_type == "markdown" and "Exercise 2" in c.source)
        assert "<!-- cadence:task setup.row-sums -->" in md_two.source
        # %cadence_register injected as the first line of each exercise cell.
        mean_cell = next(
            c for c in out_nb.cells
            if c.cell_type == "code" and "arr = np.arange(100)" in c.source
        )
        first_line = mean_cell.source.splitlines()[0]
        assert first_line.startswith("%cadence_register setup.mean"), first_line
        assert "--comparator numeric" in first_line
        assert "--reveal-after 3" in first_line
        assert "--hint" in first_line
        assert "try `.mean()`" in first_line
        # Teacher's solution code still present below the register line.
        assert "arr.mean()" in mean_cell.source
        print("✓ manual marker mode: minimal setup + inline %cadence_register per cell")

        # ----------------------------- Auto mode -----------------------------
        auto_src = tmp_path / "auto.ipynb"
        auto_out = tmp_path / "auto_registered.ipynb"
        _build_auto_notebook(auto_src)
        user_ns = {"mean_value": 49.5, "is_true": True}
        result = autoregister.autoregister(
            src_path=auto_src,
            user_ns=user_ns,
            out_path=auto_out,
            lesson_name="My Class",
        )
        assert result.mode == "auto", result.mode
        # The intro markdown has no following code cell → skipped.
        # Exercise 1 and Exercise 2 should both be paired.
        assert result.n_checkpoints == 2, [(c.checkpoint_id, c.error) for c in result.checkpoints]
        ids = [c.checkpoint_id for c in result.checkpoints]
        assert ids == ["exercise-1-mean-of-an-arange", "exercise-2-a-boolean"], ids
        # bool stays as exact, not numeric (despite isinstance(bool, int)).
        bool_cp = result.checkpoints[1]
        assert bool_cp.comparator == "exact"
        assert bool_cp.expected["value"] is True
        # Imports cell preserved (no marker needed in auto mode).
        out_nb = nbf.read(str(auto_out), as_version=4)
        assert any("import numpy as np" in c.source for c in out_nb.cells if c.cell_type == "code")
        # Lesson name override honored.
        assert "%cadence_create_lesson \"My Class\"" in out_nb.cells[0].source
        print("✓ auto mode: heading-pairing, slug ids, lesson-name override, bool stays exact")

        # ----------------------------- Numpy + missing variable -----------------------------
        np_src = tmp_path / "np.ipynb"
        np_out = tmp_path / "np_registered.ipynb"
        nb = nbf.v4.new_notebook()
        nb.cells = [
            nbf.v4.new_markdown_cell("## Exercise: array\n"),
            nbf.v4.new_code_cell(
                "# cadence:checkpoint exercise.array\n"
                "arr_result = make_array()\n"
            ),
            nbf.v4.new_markdown_cell("## Exercise: missing\n"),
            nbf.v4.new_code_cell(
                "# cadence:checkpoint exercise.missing\n"
                "never_run = 'oops'\n"
            ),
        ]
        _changes, nb = nbf.validator.normalize(nb)
        nbf.write(nb, str(np_src))
        try:
            import numpy as np
            arr_value = np.array([1.5, 2.5, 3.5])
        except ImportError:
            arr_value = [1.5, 2.5, 3.5]
        result = autoregister.autoregister(
            src_path=np_src,
            user_ns={"arr_result": arr_value},  # `never_run` deliberately missing
            out_path=np_out,
        )
        assert result.n_checkpoints == 1, (result.n_checkpoints, result.n_failed)
        assert result.n_failed == 1
        ok = next(c for c in result.checkpoints if c.error is None)
        # numpy array coerced through .tolist() → list of floats → set comparator
        assert ok.comparator == "set"
        assert ok.expected["value"] == [1.5, 2.5, 3.5]
        bad = next(c for c in result.checkpoints if c.error is not None)
        assert "never_run" in bad.error and "kernel" in bad.error
        print("✓ numpy coercion + helpful error when teacher hasn't run a cell")

        # ----------------------------- Text + manual checkpoint types -----------------------------
        types_src = tmp_path / "types.ipynb"
        types_out = tmp_path / "types_registered.ipynb"
        nb = nbf.v4.new_notebook()
        nb.cells = [
            nbf.v4.new_markdown_cell("## Exercise: greeting\nReturn a polite greeting.\n"),
            nbf.v4.new_code_cell(
                "# cadence:checkpoint greet.basic\n"
                "greeting = 'hello'\n"
            ),
            nbf.v4.new_markdown_cell("## Exercise: ordered list\nReturn rows in order.\n"),
            nbf.v4.new_code_cell(
                "# cadence:checkpoint rows.ordered exact\n"
                "rows = [1, 2, 3]\n"
            ),
            nbf.v4.new_markdown_cell(
                "## Exercise: reflect\nWrite a short reflection on what you learned.\n"
            ),
            nbf.v4.new_code_cell(
                "# cadence:checkpoint reflection.notes manual\n"
                "# cadence:hint: 2-3 sentences is plenty\n"
                "# teacher's notes (no answer to extract for manual)\n"
            ),
        ]
        _changes, nb = nbf.validator.normalize(nb)
        nbf.write(nb, str(types_src))
        result = autoregister.autoregister(
            src_path=types_src,
            user_ns={"greeting": "hello", "rows": [1, 2, 3]},
            out_path=types_out,
        )
        assert result.n_checkpoints == 3, [(c.checkpoint_id, c.error) for c in result.checkpoints]
        assert result.n_failed == 0
        greet, ordered, reflect = result.checkpoints
        # String → exact comparator
        assert greet.comparator == "exact"
        assert greet.expected == {"value": "hello"}
        # List forced to `exact` via marker override (would default to `set`)
        assert ordered.comparator == "exact", ordered.comparator
        assert ordered.expected["value"] == [1, 2, 3]
        # Manual → no expected, no value extraction attempted (cell had none anyway)
        assert reflect.comparator == "manual"
        assert reflect.expected is None
        assert reflect.hint == "2-3 sentences is plenty"
        # Inline register lines reflect the types correctly.
        out_nb = nbf.read(str(types_out), as_version=4)
        greet_cell = next(c for c in out_nb.cells if c.cell_type == "code" and "greeting = 'hello'" in c.source)
        first = greet_cell.source.splitlines()[0]
        assert "--comparator exact" in first
        assert '"hello"' in first  # string round-trips as JSON-quoted
        reflect_cell = next(c for c in out_nb.cells if c.cell_type == "code" and "reflection" in c.source)
        reflect_register_line = reflect_cell.source.splitlines()[0]
        assert "--comparator manual" in reflect_register_line
        assert "--expected" not in reflect_register_line, "manual checkpoints shouldn't carry --expected"
        assert "--hint" in reflect_register_line
        print("✓ types: string→exact, list with `exact` override, manual reflection")

        # ----------------------------- Setup-cell skip + subheadings + autoregister→scaffold rewrite -----------------------------
        rich_src = tmp_path / "rich.ipynb"
        rich_out = tmp_path / "rich_registered.ipynb"
        nb = nbf.v4.new_notebook()
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3"}
        nb.cells = [
            # Heading + setup cell that should NOT become an exercise (no
            # primitive answer value — assigns an opaque object).
            nbf.v4.new_markdown_cell("## Setup\n"),
            nbf.v4.new_code_cell(
                "class _Generator: pass\n"
                "rng = _Generator()\n"
            ),
            # Section heading + subheading in the SAME markdown cell;
            # the last heading should win for slug id.
            nbf.v4.new_markdown_cell(
                "## Part A — Numerics\n"
                "### Exercise: mean\n"
                "Compute the mean.\n"
            ),
            nbf.v4.new_code_cell("mean_value = 5.0\n"),
            # Stray %cadence_autoregister cell — should get REPLACED with
            # %cadence_scaffold in the output; stray %load_ext stripped.
            nbf.v4.new_code_cell("%load_ext cadence\n%cadence_autoregister\n"),
        ]
        _changes, nb = nbf.validator.normalize(nb)
        nbf.write(nb, str(rich_src))
        result = autoregister.autoregister(
            src_path=rich_src,
            user_ns={"rng": object(), "mean_value": 5.0},
            out_path=rich_out,
        )
        # Setup cell silently dropped (Generator-like object — not an answer
        # type), so n_checkpoints == 1 and n_failed == 0.
        assert result.mode == "auto"
        assert result.n_checkpoints == 1, result.n_checkpoints
        assert result.n_failed == 0
        # Subheading wins over parent heading: id is `exercise-mean`.
        assert result.checkpoints[-1].checkpoint_id == "exercise-mean", \
            result.checkpoints[-1].checkpoint_id
        out_nb = nbf.read(str(rich_out), as_version=4)
        # No cell still contains %cadence_autoregister.
        assert not any(
            "%cadence_autoregister" in c.source for c in out_nb.cells if c.cell_type == "code"
        ), "autoregister line should have been replaced with scaffold"
        # Exactly one cell with %cadence_scaffold (the replacement).
        scaffold_cells = [c for c in out_nb.cells if c.cell_type == "code" and "%cadence_scaffold" in c.source]
        assert len(scaffold_cells) == 1, [c.source for c in scaffold_cells]
        # Setup `rng` cell is still in the output (copied verbatim).
        assert any("rng = _Generator()" in c.source for c in out_nb.cells if c.cell_type == "code")
        # Only ONE %load_ext cadence in the output (the top setup cell);
        # the stray copy was stripped.
        load_ext_count = sum(
            c.source.count("%load_ext cadence") for c in out_nb.cells if c.cell_type == "code"
        )
        assert load_ext_count == 1, load_ext_count
        print("✓ setup-cell skip, subheading-wins, autoregister→scaffold rewrite, load_ext dedupe")

        # ----------------------------- Course choice baked into setup cell -----------------------------
        course_src = tmp_path / "course.ipynb"
        course_out = tmp_path / "course_registered.ipynb"
        nb = nbf.v4.new_notebook()
        nb.cells = [
            nbf.v4.new_markdown_cell("## Exercise\n"),
            nbf.v4.new_code_cell("answer = 1\n"),
        ]
        _changes, nb = nbf.validator.normalize(nb)
        nbf.write(nb, str(course_src))
        result = autoregister.autoregister(
            src_path=course_src,
            user_ns={"answer": 1},
            out_path=course_out,
            lesson_name="Linked",
            course_choice=("new", "Fall 2026"),
        )
        out_nb = nbf.read(str(course_out), as_version=4)
        setup = out_nb.cells[0].source
        assert '%cadence_create_course "Fall 2026"' in setup, setup
        assert '%cadence_add_notebook "Linked"' in setup, setup
        assert "%cadence_create_lesson" not in setup, "new-course mode shouldn't emit create_lesson"
        print("✓ course_choice=('new', ...) emits create_course + add_notebook setup")

        # ----------------------------- Retention baked into setup cell -----------------------------
        ret_src = tmp_path / "ret.ipynb"
        ret_out = tmp_path / "ret_registered.ipynb"
        nb = nbf.v4.new_notebook()
        nb.cells = [
            nbf.v4.new_markdown_cell("## Exercise\n"),
            nbf.v4.new_code_cell("answer = 1\n"),
        ]
        _changes, nb = nbf.validator.normalize(nb)
        nbf.write(nb, str(ret_src))

        # Standalone with 30-day retention → goes on create_lesson.
        result = autoregister.autoregister(
            src_path=ret_src, user_ns={"answer": 1}, out_path=ret_out,
            lesson_name="L", retention_days=30,
        )
        setup = nbf.read(str(ret_out), as_version=4).cells[0].source
        assert "%cadence_create_lesson \"L\" --retention-days 30" in setup, setup

        # New course with 60-day retention → goes on create_course, NOT on
        # add_notebook (the notebook inherits the course's retention).
        ret_out.unlink()
        result = autoregister.autoregister(
            src_path=ret_src, user_ns={"answer": 1}, out_path=ret_out,
            lesson_name="L", retention_days=60,
            course_choice=("new", "C"),
        )
        setup = nbf.read(str(ret_out), as_version=4).cells[0].source
        assert "%cadence_create_course \"C\" --retention-days 60" in setup, setup
        assert "--retention-days" not in [l for l in setup.splitlines() if "add_notebook" in l][0]

        # Existing course → retention is ignored at the setup-cell level
        # (lesson inherits the course's existing retention).
        ret_out.unlink()
        result = autoregister.autoregister(
            src_path=ret_src, user_ns={"answer": 1}, out_path=ret_out,
            lesson_name="L", retention_days=30,
            course_choice=("existing", "C"),
        )
        setup = nbf.read(str(ret_out), as_version=4).cells[0].source
        assert "--retention-days" not in setup, \
            "existing-course path shouldn't override retention — lesson inherits course's"
        print("✓ retention prompt bakes --retention-days into the right magic per path")

    print("\nAll autoregister tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
