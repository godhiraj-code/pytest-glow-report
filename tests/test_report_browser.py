from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from beautiful_report.core import ReportBuilder


def _result(**overrides):
    result = {
        "nodeid": "test_browser_report",
        "outcome": "failed",
        "duration": 0.1,
        "longrepr": None,
        "sections": [],
        "steps": [],
        "screenshots": [],
        "logs": [],
    }
    result.update(overrides)
    return result


def test_rendered_report_copies_literal_error_and_cleans_log_control_codes(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    error_text = "AssertionError: expected `${value}` and </pre><script>literal()</script>"
    colored_log = "\x1b[35mDEBUG\x1b[0m log_api:test_api.py:186\x00 clean"

    builder = ReportBuilder(output_dir=str(tmp_path))
    builder.add_test_result(
        _result(
            longrepr=error_text,
            sections=[("Captured log call", colored_log)],
        )
    )
    builder.build_report()

    handler = partial(SimpleHTTPRequestHandler, directory=str(tmp_path))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch()
            context = browser.new_context()
            context.grant_permissions(["clipboard-read", "clipboard-write"], origin=f"http://127.0.0.1:{server.server_port}")
            page = context.new_page()
            page.goto(f"http://127.0.0.1:{server.server_port}/report.html", wait_until="domcontentloaded")

            assert page.locator("#error-details-1").text_content() == error_text
            captured_log = page.locator("details", has_text="Captured log call").locator("pre").text_content()
            assert captured_log == "DEBUG log_api:test_api.py:186 clean"

            page.locator('div[data-nodeid="test_browser_report"] > div').first.click()
            copy_button = page.locator('button[data-copy-target="error-details-1"]')
            copy_button.wait_for(state="visible")
            copy_button.click()
            assert page.evaluate("navigator.clipboard.readText()") == error_text
            assert page.locator('button[data-copy-target="error-details-1"] .copy-label').text_content() == "✓ Copied!"
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
