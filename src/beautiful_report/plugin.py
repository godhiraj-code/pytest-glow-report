"""Pytest plugin for Glow Report."""
import os
import sys
from typing import Any, Dict, Optional

import pytest

from .core import ReportBuilder

_builder: Optional[ReportBuilder] = None


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("glow-report")
    group.addoption(
        "--glow-report",
        action="store_true",
        default=True,
        dest="glow_report",
        help="Enable Glow HTML report generation (enabled by default)",
    )
    group.addoption(
        "--no-glow-report",
        action="store_false",
        dest="glow_report",
        help="Disable Glow HTML report generation",
    )
    group.addoption(
        "--report-dir",
        action="store",
        default="reports",
        dest="report_dir",
        help="Directory to save reports (default: reports/)",
    )


def pytest_addhooks(pluginmanager: pytest.PytestPluginManager) -> None:
    from . import hooks

    pluginmanager.add_hookspecs(hooks)


def pytest_configure(config: pytest.Config) -> None:
    global _builder
    _builder = None
    if not config.getoption("glow_report"):
        return

    _builder = ReportBuilder(output_dir=config.getoption("report_dir"))
    _builder.context["title"] = os.environ.get("GLOW_REPORT_TITLE", "Glow Test Report")


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: Optional[pytest.Item]):
    """Keep report context active across setup, call, and teardown."""
    del nextitem
    if _builder is None:
        yield
        return

    from .decorators import TestContext, set_current_context

    context = TestContext()
    setattr(item, "_glow_report_context", context)
    set_current_context(context)
    try:
        yield
    finally:
        set_current_context(None)


@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Transfer execution context from the item to each serializable TestReport."""
    del call
    outcome = yield
    test_report = outcome.get_result()
    context = getattr(item, "_glow_report_context", None)
    if context is not None:
        setattr(test_report, "_glow_report_context", context.to_dict())


def _make_result(report: pytest.TestReport) -> Dict[str, Any]:
    context = getattr(report, "_glow_report_context", {}) or {}
    return {
        "nodeid": report.nodeid,
        "outcome": report.outcome,
        "duration": report.duration,
        "longrepr": str(report.longrepr) if report.longrepr else None,
        "sections": list(report.sections),
        "steps": list(context.get("steps", [])),
        "screenshots": list(context.get("screenshots", [])),
        "logs": list(context.get("logs", [])),
        "phase": report.when,
    }


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Capture call results and setup/teardown failures without duplicate rows."""
    if _builder is None:
        return

    # Every phase contributes duration, captured sections, and execution context.
    # ReportBuilder merges them into one row and gives failures/skips precedence.
    _builder.add_test_result(_make_result(report))


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    global _builder
    if _builder is None:
        return

    numeric_exitstatus = int(exitstatus)
    _builder.context["session_exitstatus"] = numeric_exitstatus
    if numeric_exitstatus != int(pytest.ExitCode.OK) and not any(
        test.get("outcome") == "failed" for test in _builder.tests
    ):
        _builder.add_test_result(
            {
                "nodeid": "pytest session",
                "outcome": "failed",
                "duration": 0.0,
                "longrepr": "pytest exited with status {} before recording a test failure".format(numeric_exitstatus),
                "sections": [],
                "steps": [],
                "screenshots": [],
                "logs": [],
                "phase": "session",
            }
        )

    try:
        logo = session.config.hook.pytest_html_logo()
        if logo:
            _builder.context["logo"] = logo
    except Exception:
        pass

    base_env: Dict[str, str] = {"Python": sys.version.split()[0], "Platform": sys.platform}
    environment_fields = (
        ("GLOW_TEST_TYPE", "Test Type"),
        ("GLOW_BROWSER", "Browser"),
        ("GLOW_DEVICE", "Device"),
        ("GLOW_ENVIRONMENT", "Environment"),
        ("GLOW_BUILD", "Build"),
    )
    for variable, label in environment_fields:
        value = os.environ.get(variable)
        if value:
            base_env[label] = value

    try:
        custom_env = session.config.hook.pytest_html_environment()
        if custom_env:
            base_env.update(custom_env)
    except Exception:
        pass

    _builder.set_environment_info(base_env)
    _builder.build_report()
    _builder = None
