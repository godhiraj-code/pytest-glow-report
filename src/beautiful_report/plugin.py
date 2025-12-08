"""
PyTest plugin for Glow Report.

This module provides pytest hooks to automatically generate beautiful HTML reports.
"""
import os
import sys
from typing import Dict, Optional

import pytest

from .core import ReportBuilder

_builder: Optional[ReportBuilder] = None


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command-line options for the report plugin."""
    group = parser.getgroup("glow-report")
    group.addoption(
        "--glow-report",
        action="store_true",
        default=True,
        dest="glow_report",
        help="Enable Glow HTML Report generation (enabled by default)",
    )
    group.addoption(
        "--report-dir",
        action="store",
        default="reports",
        dest="report_dir",
        help="Directory to save reports (default: reports/)",
    )


def pytest_addhooks(pluginmanager: pytest.PytestPluginManager) -> None:
    """Register custom hooks for report customization."""
    from . import hooks
    pluginmanager.add_hookspecs(hooks)


def pytest_configure(config: pytest.Config) -> None:
    """Initialize the report builder at session start."""
    global _builder
    
    if not config.option.glow_report:
        return
    
    report_dir = config.option.report_dir
    _builder = ReportBuilder(output_dir=report_dir)
    
    title = os.environ.get("GLOW_REPORT_TITLE", "Glow Test Report")
    _builder.context["title"] = title


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Generate the report at session end."""
    global _builder
    
    if _builder is None:
        return
    
    try:
        logo = session.config.hook.pytest_html_logo()
        if logo:
            _builder.context["logo"] = logo
    except Exception:
        pass
    
    base_env: Dict[str, str] = {
        "Python": sys.version.split()[0],
        "Platform": sys.platform,
    }
    
    # Add optional enterprise fields from environment
    if os.environ.get("GLOW_TEST_TYPE"):
        base_env["Test Type"] = os.environ.get("GLOW_TEST_TYPE")
    if os.environ.get("GLOW_BROWSER"):
        base_env["Browser"] = os.environ.get("GLOW_BROWSER")
    if os.environ.get("GLOW_DEVICE"):
        base_env["Device"] = os.environ.get("GLOW_DEVICE")
    if os.environ.get("GLOW_ENVIRONMENT"):
        base_env["Environment"] = os.environ.get("GLOW_ENVIRONMENT")
    if os.environ.get("GLOW_BUILD"):
        base_env["Build"] = os.environ.get("GLOW_BUILD")
    
    try:
        custom_env = session.config.hook.pytest_html_environment()
        if custom_env:
            base_env.update(custom_env)
    except Exception:
        pass
    
    _builder.set_environment_info(base_env)
    _builder.build_report()
    _builder = None


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    """Manage test context for steps and screenshots."""
    from .decorators import TestContext, set_current_context

    if call.when == "call":
        ctx = TestContext()
        set_current_context(ctx)
        item._glow_report_context = ctx
    
    outcome = yield
    
    if call.when == "call":
        set_current_context(None)
    
    _ = outcome.get_result()


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Capture individual test results with steps and screenshots."""
    global _builder
    
    if _builder is None:
        return
    
    if report.when == "call":
        ctx = getattr(report, "_glow_report_context", None)
        
        result = {
            "nodeid": report.nodeid,
            "outcome": report.outcome,
            "duration": report.duration,
            "longrepr": str(report.longrepr) if report.longrepr else None,
            "sections": list(report.sections),
            "steps": ctx.steps if ctx else [],
            "screenshots": ctx.screenshots if ctx else [],
        }
        _builder.add_test_result(result)
    
    elif report.when == "setup" and report.outcome == "skipped":
        result = {
            "nodeid": report.nodeid,
            "outcome": "skipped",
            "duration": 0.0,
            "longrepr": str(report.longrepr) if report.longrepr else None,
            "sections": list(report.sections),
            "steps": [],
            "screenshots": [],
        }
        _builder.add_test_result(result)
