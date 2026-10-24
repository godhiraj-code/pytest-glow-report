import json
import re
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from beautiful_report.core import ReportBuilder

pytest_plugins = ["pytester"]
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("phase", ["setup", "call"])
def test_successful_retry_replaces_transient_outcomes(pytester, phase):
    pytest.importorskip("pytest_rerunfailures")
    pytester.makepyfile(f'''
        import pytest
        attempts = 0

        def flaky():
            global attempts
            attempts += 1
            assert attempts > 1

        @pytest.fixture
        def resource():
            {"flaky()" if phase == "setup" else "pass"}

        def test_retry(resource):
            {"flaky()" if phase == "call" else "pass"}
    ''')
    result = pytester.runpytest_subprocess("-q", "--reruns=1", "--report-dir=output")
    assert result.ret == 0
    assert result.parseoutcomes() == {"passed": 1, "rerun": 1}
    data = json.loads((pytester.path / "output/report.json").read_text(encoding="utf-8"))
    assert (pytester.path / "output/report.html").exists()
    assert data["summary"] == dict(passed=1, failed=0, error=0, skipped=0, xfailed=0, xpassed=0, total=1)
    assert data["tests"][0]["outcome"] == "passed"
    assert data["tests"][0]["phase_outcomes"] == dict(setup="passed", call="passed", teardown="passed")


def test_unknown_phase_outcomes_do_not_crash_summary(tmp_path):
    builder = ReportBuilder(str(tmp_path))
    builder.add_test_result(dict(nodeid="test_retry", outcome="rerun", duration=0,
                                 phase_outcomes={"setup": "rerun"}))
    builder.add_test_result(dict(nodeid="test_retry", outcome="passed", duration=0,
                                 phase_outcomes={"teardown": "passed"}))
    assert builder.tests[0]["outcome"] == "rerun"
    builder.build_report()
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert data["summary"] == dict(passed=0, failed=0, error=0, skipped=0, xfailed=0, xpassed=0, total=1)


def test_history_v1_migration_preserves_rows_and_error_stability(tmp_path):
    path = tmp_path / "history.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE runs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, "
                     "passed INTEGER, failed INTEGER, skipped INTEGER, duration REAL)")
        conn.execute("INSERT INTO runs VALUES (1, '2026-10-23T12:00:00', 3, 0, 1, 2.5)")
        conn.execute("PRAGMA user_version = 1")
    builder = ReportBuilder(str(tmp_path))
    builder.add_test_result(dict(nodeid="test_error", outcome="error", duration=0.1))
    builder.build_report()
    rows = builder.history.get_history()
    assert rows[1] == dict(id=1, timestamp="2026-10-23T12:00:00", passed=3, failed=0,
                           skipped=1, duration=2.5, errors=0)
    assert rows[0]["errors"] == 1 and rows[0]["failed"] == 0
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert 'text-teal-600 dark:text-teal-400">50%</div>' in html
    assert "0 failed, 1 errors" in html
    # Opening an already migrated database remains safe.
    assert ReportBuilder(str(tmp_path)).history.get_history() == rows


@pytest.mark.parametrize("outcome", ["skipped", "xfailed", "xpassed"])
def test_runs_without_passes_are_not_assessed_or_celebrated(tmp_path, outcome):
    builder = ReportBuilder(str(tmp_path))
    builder.add_test_result(dict(nodeid="test_not_passed", outcome=outcome, duration=0))
    builder.build_report()
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "0.0% pass rate" in html
    assert "Risk Level: Not assessed" in html
    assert 'text-slate-700 dark:text-slate-300">Not assessed' in html
    assert "confetti.className" not in html


def test_failure_metric_banner_and_risk_include_errors(tmp_path):
    builder = ReportBuilder(str(tmp_path))
    for i, outcome in enumerate(["passed"] * 100 + ["failed"] * 3 + ["error"]):
        builder.add_test_result(dict(nodeid=f"test_{i}", outcome=outcome, duration=0))
    builder.build_report()
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert 'text-red-600 dark:text-red-400">4</div>' in html
    assert "3 failed, 1 error</p>" in html
    assert "Risk Level: High" in html
    assert 'text-red-700 dark:text-red-300">High' in html
    assert "confetti.className" not in html


def test_readme_documents_network_requirement():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Internet access is required for the report styles and interactive controls" in readme
    assert "readable fallback styling for offline use" not in readme


def test_wheel_has_current_version_and_no_stale_module(tmp_path):
    pytest.importorskip("build")
    result = subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    wheel = next(tmp_path.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        assert "beautiful_report/_version.py" not in archive.namelist()
        metadata = archive.read("pytest_glow_report-0.1.4.dist-info/METADATA").decode()
        assert "Version: 0.1.4\n" in metadata
        assert b'__version__ = "0.1.4"' in archive.read("beautiful_report/__init__.py")
    assert not (ROOT / "src/beautiful_report/_version.py").exists()
    for source in (ROOT / "src").rglob("*.py"):
        assert not re.search(r"(?:from|import)\s+[.\w]*_version\b", source.read_text(encoding="utf-8"))


def test_documented_hooks_allow_disabling_glow(pytester):
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    examples = re.findall(r"```python\n(.*?)```", readme, re.DOTALL)
    hooks = [example for example in examples if "def pytest_html_" in example]
    assert len(hooks) == 2
    pytester.makeconftest("\n".join(hooks))
    pytester.makepyfile("def test_ok(): pass")
    result = pytester.runpytest_subprocess("-p", "no:glow_report", "-q")
    assert result.ret == 0
    result.assert_outcomes(passed=1)


def test_summary_matches_pytest_outcomes(pytester):
    pytester.makepyfile('''
        import pytest

        def test_pass(): pass
        def test_fail(): assert False
        def test_skip(): pytest.skip("not ready")

        @pytest.mark.xfail(reason="known bug")
        def test_xfail(): assert False

        @pytest.mark.xfail(reason="fixed bug")
        def test_xpass(): pass

        @pytest.fixture
        def broken_setup(): raise RuntimeError("setup boom")

        def test_setup_error(broken_setup): pass

        @pytest.fixture
        def broken_teardown():
            yield
            raise RuntimeError("teardown boom")

        def test_teardown_error(broken_teardown): pass
    ''')
    result = pytester.runpytest_subprocess("-q", "--report-dir=output")
    result.assert_outcomes(passed=2, failed=1, skipped=1, xfailed=1, xpassed=1, errors=2)
    data = json.loads((pytester.path / "output/report.json").read_text(encoding="utf-8"))
    counts = result.parseoutcomes()
    counts["error"] = counts.pop("errors")
    assert data["summary"] == dict(counts, total=7)
    assert all(test["outcome"] != "errors" for test in data["tests"])
    assert len(data["tests"]) == 7
    skipped = next(test for test in data["tests"] if test["outcome"] == "skipped")
    assert skipped["longrepr"] == "not ready"
    html = (pytester.path / "output/report.html").read_text(encoding="utf-8")
    for label, count in (("Errors", 2), ("Xfailed", 1), ("Xpassed", 1)):
        assert f"<span>{label}</span>: <strong" in html
        assert f">{count}</strong>" in html


@pytest.mark.parametrize("source, rate, success", [
    ("def test_a(): pass\ndef test_b(): pass\ndef test_c(): pytest.skip('later')", "100.0", True),
    ("def test_a(): pytest.skip('later')", "0.0", True),
    ("def test_a(): pass\ndef test_b(): assert False", "50.0", False),
])
def test_success_and_rate_ignore_skips(pytester, source, rate, success):
    pytester.makepyfile("import pytest\n" + source)
    result = pytester.runpytest_subprocess("-q", "--report-dir=output")
    assert result.ret == (0 if success else 1)
    html = (pytester.path / "output/report.html").read_text(encoding="utf-8")
    assert f"{rate}% pass rate" in html
    assert ("No Failures or Errors" in html) is success
    assert "No Tests Passed" not in html
    color = "emerald" if success else "red"
    assert f'mt-6 p-4 rounded-xl bg-{color}-50' in html


@pytest.mark.parametrize("width", [360, 390, 768])
def test_mobile_header_stays_inside_viewport(tmp_path, width):
    playwright = pytest.importorskip("playwright.sync_api")
    builder = ReportBuilder(output_dir=str(tmp_path))
    builder.add_test_result({"nodeid": "test_ok", "outcome": "passed", "duration": 0.1})
    builder.build_report()
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": width, "height": 844}, reduced_motion="reduce")
            page.goto((tmp_path / "report.html").as_uri())
            # Require the actual CDN-enhanced layout and interactive controls.
            page.wait_for_function("window.Alpine && getComputedStyle(document.querySelector('.report-header')).display === 'flex'")
            toggle = page.get_by_role("button", name="Toggle dark mode")
            for focused in (False, True):
                if focused:
                    page.get_by_placeholder("Search tests...").focus()
                    page.wait_for_timeout(400)
                assert page.evaluate("document.documentElement.scrollWidth") <= width
                box = toggle.bounding_box()
                assert box is not None
                assert 0 <= box["x"] and box["x"] + box["width"] <= width
                assert box["width"] >= 44 and box["height"] >= 44
                header = page.locator("header").bounding_box()
                assert box["y"] + box["height"] <= header["y"] + header["height"]
            was_dark = page.evaluate("document.documentElement.classList.contains('dark')")
            toggle.click()
            assert page.evaluate("document.documentElement.classList.contains('dark')") is not was_dark
        finally:
            browser.close()
