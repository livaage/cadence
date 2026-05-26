"""
Cadence — live student progress dashboards for Jupyter teaching.

A teacher registers checkpoints in their notebook; students submit answers
from theirs via `check("id", value)`; the teacher watches a real-time
dashboard. See https://cadence-dash.com for the hosted dashboard and the
Setup Guide.
"""

__version__ = "0.2.26"
__author__ = "Liv Vage"
__email__ = "contact@cadence-dash.com"

from .api import CadenceAPI
from .notebook import ProblemNotebook, create_problem_notebook
from .magic import CadenceMagic
from .extension import CadenceExtension, load_ipython_extension
from .progress import check, CheckResult, current_session, show_hint, show_solution, mark_done, submit_image

__all__ = [
    "CadenceAPI",
    "ProblemNotebook",
    "create_problem_notebook",
    "CadenceMagic",
    "CadenceExtension",
    "load_ipython_extension",
    "check",
    "CheckResult",
    "show_hint",
    "show_solution",
    "mark_done",
    "submit_image",
    "current_session",
]
