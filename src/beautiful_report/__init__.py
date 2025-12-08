"""
pytest-glow-report: Beautiful, glowing HTML test reports.
"""

__version__ = "0.1.0"

from .core import ReportBuilder
from .decorators import report

__all__ = ["ReportBuilder", "report"]
