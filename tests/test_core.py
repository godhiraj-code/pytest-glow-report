import json
import os
from pathlib import Path

from beautiful_report.core import ReportBuilder


def _result(**overrides):
    result = {
        "nodeid": "test_one",
        "outcome": "passed",
        "duration": 0.1,
        "longrepr": None,
        "sections": [],
        "steps": [],
        "screenshots": [],
        "logs": [],
    }
    result.update(overrides)
    return result


def test_builder_initialization(tmp_path):
    report_dir = tmp_path / "report"
    ReportBuilder(output_dir=str(report_dir))
    assert os.path.exists(report_dir)
    assert os.path.exists(report_dir / "history.sqlite")


def test_add_test_result_updates_duplicate_node(tmp_path):
    builder = ReportBuilder(output_dir=str(tmp_path))
    builder.add_test_result(_result())
    builder.add_test_result(_result(outcome="failed", duration=0.2, longrepr="teardown failed"))

    assert len(builder.tests) == 1
    assert builder.tests[0]["nodeid"] == "test_one"
    assert builder.tests[0]["outcome"] == "failed"
    assert builder.tests[0]["duration"] == 0.3
    assert builder.tests[0]["longrepr"] == "teardown failed"


def test_build_report(tmp_path):
    builder = ReportBuilder(output_dir=str(tmp_path))
    builder.add_test_result(_result())
    builder.build_report()

    assert (tmp_path / "report.html").exists()
    assert (tmp_path / "report.json").exists()


def test_build_report_escapes_error_details_and_uses_dom_copy(tmp_path):
    payload = "</pre><script>window.pwned = true</script>${alert(1)}`"
    builder = ReportBuilder(output_dir=str(tmp_path))
    builder.add_test_result(_result(outcome="failed", longrepr=payload, nodeid="test_'quoted"))
    builder.context["title"] = "<img src=x onerror=alert(1)>"
    builder.build_report()

    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert payload not in html
    assert "&lt;script&gt;window.pwned = true&lt;/script&gt;" in html
    assert "navigator.clipboard.writeText(`" not in html
    assert 'data-copy-target="error-details-1"' in html
    assert "copyErrorDetails(this)" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_build_report_strips_ansi_escape_sequences_from_sections(tmp_path):
    colored = "\x1b]8;;https://example.test\x07\x1b[35mDEBUG\x1b[0m log_api:test_api.py:186\x00 clean\x1b]8;;\x07"
    builder = ReportBuilder(output_dir=str(tmp_path))
    builder.add_test_result(_result(sections=[("Captured log call", colored)]))
    builder.build_report()

    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert "\x1b" not in html
    assert "\x00" not in html
    assert data["tests"][0]["sections"][0][1] == "DEBUG log_api:test_api.py:186 clean"


def test_report_has_readable_offline_fallback(tmp_path):
    builder = ReportBuilder(output_dir=str(tmp_path))
    builder.add_test_result(_result())
    builder.build_report()

    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert '<div x-data="reportApp()" class="relative">' in html
    assert "Offline fallback styles" in html


def test_history_manager_supports_filename_without_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from beautiful_report.core import HistoryManager

    HistoryManager("history.sqlite")
    assert Path("history.sqlite").exists()
