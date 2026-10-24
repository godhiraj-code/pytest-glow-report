"""
pytest-glow-report: Beautiful, glowing HTML test reports.
"""

__version__ = "0.1.4"
from .core import ReportBuilder
from .decorators import report

__all__ = ["__version__", "ReportBuilder", "report"]
