import pytest
import time
import sys
from typing import Optional, Dict, Any, Generator
from .core import ReportBuilder

# Guarded import for type checking if needed, though pytest is imported at runtime here.
# Since this file IS the plugin, it will only be imported by pytest (or when pytest is available).

builder: len = None

def pytest_addoption(parser):
    group = parser.getgroup("beautiful-report")
    group.addoption(
        "--beautiful-report",
        action="store_true",
        default=True, # Auto-enabled as per requirements "One-line set-up"
        help="Enable Beautiful HTML Report"
    )

def pytest_configure(config):
    # Only register if not disabled (if we add a disable flag later)
    global builder
    builder = ReportBuilder()
    
    # Capture environment info
    # In a real app we'd capture git info, python version etc.
    builder.set_environment_info({
        "Python": sys.version,
        "Platform": sys.platform
    })

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    
    # We only care about the actual call phase for pass/fail, 
    # but we might need setup/teardown errors too.
    if report.when == "call":
        # Capture stdout/stderr/log if needed (pytest captures it in report.sections usually)
        pass

def pytest_runtest_logreport(report):
    global builder
    if not builder:
        return

    # We process the report here to add to builder
    if report.when == "call":
        result = {
            "nodeid": report.nodeid,
            "outcome": report.outcome,
            "duration": report.duration,
            "longrepr": str(report.longrepr) if report.longrepr else None,
            "sections": report.sections
        }
        builder.add_test_result(result)
    elif report.outcome == "skipped":
         # Handle skips (often happen in setup)
         result = {
            "nodeid": report.nodeid,
            "outcome": "skipped",
            "duration": 0, # Skips might not have duration in call
            "longrepr": str(report.longrepr) if report.longrepr else None,
            "sections": report.sections
         }
         builder.add_test_result(result)

def pytest_sessionfinish(session, exitstatus):
    global builder
    if builder:
        builder.build_report()
