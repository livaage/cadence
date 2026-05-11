"""
Jupyter Integration for Code Cadence

This package provides seamless integration between Jupyter notebooks
and the Code Cadence, allowing students to submit solutions
directly from their notebooks and teachers to create problem templates.
"""

__version__ = "0.1.0"
__author__ = "Code Cadence Team"
__email__ = "support@competition-platform.com"

from .api import CadenceAPI
from .notebook import ProblemNotebook, create_problem_notebook
from .magic import CadenceMagic
from .extension import CadenceExtension, load_ipython_extension
from .progress import check, CheckResult, current_session

__all__ = [
    "CadenceAPI",
    "ProblemNotebook",
    "create_problem_notebook",
    "CadenceMagic",
    "CadenceExtension",
    "load_ipython_extension",
    "check",
    "CheckResult",
    "current_session",
]
