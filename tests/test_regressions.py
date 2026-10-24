import json
import re
from pathlib import Path

import pytest

from beautiful_report.core import ReportBuilder

pytest_plugins = ["pytester"]
ROOT = Path(__file__).resolve().parents[1]


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
    assert data["summary"] == dict(counts, total=sum(counts.values()))
    assert len(data["tests"]) == 7
    skipped = next(test for test in data["tests"] if test["outcome"] == "skipped")
    assert skipped["longrepr"] == "not ready"
    html = (pytester.path / "output/report.html").read_text(encoding="utf-8")
    for label, count in (("Errors", 2), ("Xfailed", 1), ("Xpassed", 1)):
        assert f"<span>{label}</span>: <strong>{count}</strong>" in html


@pytest.mark.parametrize("source, rate, success", [
    ("def test_a(): pass\ndef test_b(): pass\ndef test_c(): pytest.skip('later')", "100.0", True),
    ("def test_a(): pytest.skip('later')", "100.0", True),
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
