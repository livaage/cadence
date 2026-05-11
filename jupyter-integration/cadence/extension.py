"""
IPython extension entry point.

Loaded via `%load_ext cadence` inside a notebook.
"""

from .magic import CadenceMagic


class CadenceExtension:
    """Thin handle kept for symmetry with the package __all__."""

    def __init__(self, ipython):
        self.ipython = ipython
        self.magics = CadenceMagic(ipython)
        ipython.register_magics(self.magics)


def load_ipython_extension(ipython):
    CadenceExtension(ipython)


def unload_ipython_extension(ipython):
    pass
