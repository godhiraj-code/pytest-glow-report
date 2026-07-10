"""
pytest-glow-report: Beautiful, glowing HTML test reports.
"""

from ._version import __version__
from .core import ReportBuilder
from .decorators import report

__all__ = ["__version__", "ReportBuilder", "report"]
