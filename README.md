# pytest-glow-report

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-6.0+-green?logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-purple)

**HTML and JSON test reports for pytest and unittest**

[Features](#features) • [Installation](#installation) • [pytest](#pytest) • [unittest](#unittest) • [Configuration](#configuration) • [Test-context API](#test-context-api)

</div>

## Features

- Automatic report generation when the installed pytest plugin is enabled
- One result per pytest test, including setup, call, and teardown failures
- A `glow-report` wrapper for Python's built-in unittest runner
- HTML and JSON output, plus SQLite-backed history for the last 10 runs in the same report directory
- Result search and pass/fail/skip filters in the enhanced HTML view
- Custom report title, environment metadata, and logo hooks for pytest
- Test steps, logs, and embedded PNG/JPEG screenshots
- Dark and light themes

The HTML includes readable fallback styling for offline use. Tailwind CSS and Alpine.js are loaded from public CDNs for the full styling and interactive experience, so those enhancements require network access when the report is opened.

## Installation

Install the package:

```bash
pip install pytest-glow-report
```

pytest itself is an optional dependency. To install it with the plugin:

```bash
pip install "pytest-glow-report[pytest]"
```

Python 3.8 or newer and pytest 6.0 or newer are supported.

## pytest

The plugin is registered through pytest's `pytest11` entry point and is enabled by default after installation. Run pytest normally:

```bash
pytest
```

This writes:

```text
reports/
├── report.html
├── report.json
└── history.sqlite
```

Use another output directory or disable generation for a run:

```bash
pytest --report-dir=my_reports
pytest --no-glow-report
```

`--report-dir` and `--no-glow-report` are pytest options; they do not configure the unittest wrapper.

## unittest

Run unittest discovery through the installed CLI:

```bash
glow-report run -- unittest discover -s tests
```

The wrapper uses `BeautifulTestRunner`, preserves unittest's process exit status, and writes to `reports/`. It records passes, failures, errors, skips, subtests, expected failures, and unexpected successes. Expected failures are represented as skipped results; unexpected successes are represented as failures.

## Configuration

### Environment variables

The pytest integration reads these variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `GLOW_REPORT_TITLE` | Report header title | `Glow Test Report` | `My Project CI` |
| `GLOW_TEST_TYPE` | Test-run label | — | `Regression` |
| `GLOW_BROWSER` | Browser label | — | `Chrome 120` |
| `GLOW_DEVICE` | Device or platform label | — | `iPhone 15` |
| `GLOW_ENVIRONMENT` | Target-environment label | — | `Staging` |
| `GLOW_BUILD` | Build or version label | — | `v2.1.0` |

POSIX shell example:

```bash
export GLOW_REPORT_TITLE="E-Commerce Regression"
export GLOW_TEST_TYPE="Regression"
export GLOW_BROWSER="Chrome 120"
export GLOW_ENVIRONMENT="Staging"
pytest
```

PowerShell example:

```powershell
$env:GLOW_TEST_TYPE = "Smoke"
$env:GLOW_BROWSER = "Edge 120"
$env:GLOW_DEVICE = "Windows 11"
pytest
```

### pytest customization hooks

Add a logo URL or image data URI in `conftest.py`:

```python
def pytest_html_logo():
    return "https://example.com/logo.png"
```

Add environment metadata:

```python
import os


def pytest_html_environment():
    return {
        "Browser": "Chrome 120",
        "Environment": os.environ.get("ENV", "local"),
        "Build": os.environ.get("CI_BUILD_ID", "dev"),
        "Branch": os.environ.get("GIT_BRANCH", "main"),
    }
```

The report always includes the Python version and platform. Hook values are merged into the Environment section.

## Test-context API

The context API records data only while a test is running under the pytest plugin or `BeautifulTestRunner`. Calls made outside an active test still print their console message but are not attached to a report result.

### Steps

Use `report.step(title)` with synchronous or asynchronous functions. The report records the step name, duration, and passed/failed status, then re-raises any exception.

```python
from beautiful_report import report


@report.step("Opening login page")
def open_login(driver):
    driver.get("/login")


@report.step("Loading account")
async def load_account(client):
    return await client.get("/account")
```

### Logs

```python
from beautiful_report import report

report.log("User created successfully")
```

### Screenshots

Attach an existing PNG or JPEG file:

```python
from beautiful_report import report

report.screenshot("login page", path="screenshots/login.png")
```

Or capture from a synchronous Selenium- or Playwright-style object:

```python
report.screenshot("after submit", driver=driver)
```

The driver must provide either `get_screenshot_as_png()` or a synchronous `screenshot()` method that returns bytes. Screenshots are embedded as data URIs in both `report.html` and `report.json`; large screenshots therefore increase both artifact sizes.

## Output and history behavior

- `report.html` is the human-readable report.
- `report.json` contains the same summary, test results, environment metadata, history snapshot, and pytest session exit status when applicable.
- `history.sqlite` stores aggregate run counts and duration. The HTML and JSON outputs show up to the 10 most recent rows from that database.
- Reusing a report directory updates its history. Deleting or changing the directory starts a new history database.
- Each run replaces `report.html` and `report.json` in the selected directory.

Generated reports can contain test names, tracebacks, captured output, custom logs, metadata, and screenshots. Treat them as potentially sensitive CI artifacts and review them before sharing.

## Development

```bash
pip install -e ".[dev]"
pytest tests/
ruff check .
mypy src/
python -m build
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

MIT License. See [LICENSE](LICENSE).
