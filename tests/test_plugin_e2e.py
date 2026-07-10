import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run_pytest(tmp_path, source, *extra_args):
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(source, encoding="utf-8")
    report_dir = tmp_path / "glow-output"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "beautiful_report.plugin",
        str(test_file),
        "--report-dir",
        str(report_dir),
        "-q",
        *extra_args,
    ]
    completed = subprocess.run(command, cwd=tmp_path, env=env, text=True, capture_output=True)
    return completed, report_dir


def load_report(report_dir):
    return json.loads((report_dir / "report.json").read_text(encoding="utf-8"))


def test_pytest_records_call_context_once(tmp_path):
    completed, report_dir = run_pytest(
        tmp_path,
        """
from beautiful_report import report

@report.step("unsafe <step>")
def action():
    report.log("custom log")
    class Driver:
        def get_screenshot_as_png(self):
            return b"png bytes"
    report.screenshot("inline", driver=Driver())

def test_ok():
    action()
""",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    data = load_report(report_dir)
    assert data["summary"] == {"passed": 1, "failed": 0, "skipped": 0, "total": 1}
    assert len(data["tests"]) == 1
    assert data["tests"][0]["steps"][0]["name"] == "unsafe <step>"
    assert "custom log" in data["tests"][0]["logs"][0]
    assert data["tests"][0]["screenshots"][0].startswith("data:image/png;base64,")


def test_context_spans_fixture_setup_call_and_teardown(tmp_path):
    completed, report_dir = run_pytest(
        tmp_path,
        """
import pytest
from beautiful_report import report

@pytest.fixture
def resource():
    report.log("fixture setup")
    yield
    report.log("fixture teardown")

def test_ok(resource):
    report.log("test call")
""",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    data = load_report(report_dir)
    assert len(data["tests"]) == 1
    assert [entry.rsplit(" ", 2)[-2:] for entry in data["tests"][0]["logs"]] == [
        ["fixture", "setup"],
        ["test", "call"],
        ["fixture", "teardown"],
    ]


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
def test_pytest_records_each_failure_phase_without_duplicates(tmp_path, phase):
    fixture_body = {
        "setup": "raise RuntimeError('setup boom')\n    yield",
        "call": "yield",
        "teardown": "yield\n    raise RuntimeError('teardown boom')",
    }[phase]
    call_body = "raise RuntimeError('call boom')" if phase == "call" else "pass"
    completed, report_dir = run_pytest(
        tmp_path,
        f"""
import pytest

@pytest.fixture
def resource():
    {fixture_body}

def test_failure(resource):
    {call_body}
""",
    )

    assert completed.returncode != 0
    data = load_report(report_dir)
    assert data["summary"]["failed"] == 1
    assert data["summary"]["total"] == 1
    assert len(data["tests"]) == 1
    assert f"{phase} boom" in data["tests"][0]["longrepr"]


def test_pytest_setup_skip_is_recorded_once(tmp_path):
    completed, report_dir = run_pytest(
        tmp_path,
        """
import pytest

@pytest.fixture
def resource():
    pytest.skip("not available")

def test_skip(resource):
    pass
""",
    )

    assert completed.returncode == 0
    data = load_report(report_dir)
    assert data["summary"] == {"passed": 0, "failed": 0, "skipped": 1, "total": 1}
    assert "All Tests Passing" not in (report_dir / "report.html").read_text(encoding="utf-8")


def test_no_glow_report_disables_all_artifacts(tmp_path):
    completed, report_dir = run_pytest(tmp_path, "def test_ok(): pass", "--no-glow-report")

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert not report_dir.exists()


def test_zero_collected_tests_cannot_report_all_passing(tmp_path):
    completed, report_dir = run_pytest(tmp_path, "# no tests here")

    assert completed.returncode == pytest.ExitCode.NO_TESTS_COLLECTED
    data = load_report(report_dir)
    assert data["summary"]["failed"] == 1
    assert data["session_exitstatus"] == int(pytest.ExitCode.NO_TESTS_COLLECTED)
    assert "All Tests Passing" not in (report_dir / "report.html").read_text(encoding="utf-8")


def test_collection_error_cannot_report_all_passing(tmp_path):
    completed, report_dir = run_pytest(tmp_path, "def broken(:\n    pass")

    assert completed.returncode != 0
    data = load_report(report_dir)
    assert data["summary"]["failed"] == 1
    assert "pytest session" in data["tests"][0]["nodeid"]
