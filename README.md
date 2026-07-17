# pytest-glow-report ✨

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![PyTest](https://img.shields.io/badge/PyTest-6.0+-green?logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-purple)

**Beautiful, glowing HTML test reports for PyTest and unittest**

*Stunning visuals • Zero configuration • Infinite customization*

[See the report proof and architecture case study](https://www.dhirajdas.dev/project/pytest-glow-report) · [Install from PyPI](https://pypi.org/project/pytest-glow-report/)

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Configuration](#%EF%B8%8F-configuration) • [Customization](#-customization)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🚀 **Zero Config** | Just install and run — reports generate automatically |
| 🎨 **Stunning Design** | Glassmorphism UI, animated backgrounds, dark/light mode |
| 📊 **History Tracking** | SQLite-backed test run history with trend charts |
| 🔍 **Interactive Filtering** | Click summary cards to filter Pass/Fail/Skip |
|  **Screenshot Support** | Embed screenshots from Selenium, Playwright, or files |
| 📋 **Step Tracking** | Log individual test steps with timing |
| 🎯 **Fully Customizable** | Custom logo, title, environment info, and hooks |

---

## 📦 Installation

```bash
pip install pytest-glow-report
```

---

## 🚀 Quick Start

### PyTest (Automatic)

Simply run your tests — reports generate automatically:

```bash
pytest
```

Report saved to: `reports/report.html`

### Unittest

Use the CLI wrapper:

```bash
glow-report run -- unittest discover tests
```

---

## ⚙️ Configuration

### Environment Variables

Configure the report using environment variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `GLOW_REPORT_TITLE` | Title shown in the report header | `Glow Test Report` | `My Project CI` |
| `GLOW_TEST_TYPE` | Type of test run | — | `Regression`, `Smoke`, `Sanity` |
| `GLOW_BROWSER` | Browser under test | — | `Chrome 120`, `Firefox 121` |
| `GLOW_DEVICE` | Device/platform under test | — | `iPhone 15`, `Pixel 8`, `Web` |
| `GLOW_ENVIRONMENT` | Target environment | — | `Production`, `Staging`, `QA` |
| `GLOW_BUILD` | Build/version number | — | `v2.1.0`, `#12345` |

**Usage Examples:**

```bash
# Regression test on Chrome
export GLOW_REPORT_TITLE="E-Commerce Regression"
export GLOW_TEST_TYPE="Regression"
export GLOW_BROWSER="Chrome 120"
export GLOW_ENVIRONMENT="Staging"
pytest

# Mobile smoke test
export GLOW_TEST_TYPE="Smoke"
export GLOW_DEVICE="iPhone 15 Pro"
export GLOW_ENVIRONMENT="Production"
pytest tests/mobile/

# Windows PowerShell
$env:GLOW_TEST_TYPE="Smoke"
$env:GLOW_BROWSER="Edge 120"
$env:GLOW_DEVICE="Windows 11"
pytest
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--report-dir` | Directory to save reports | `reports` |
| `--glow-report` / `--no-glow-report` | Enable/disable report generation | Enabled |

**Usage:**

```bash
# Custom output directory
pytest --report-dir=my_reports/

# Disable report generation
pytest --no-glow-report
```

---

## 🎨 Customization

### Custom Logo

Add a logo to your report by implementing the `pytest_html_logo` hook in your `conftest.py`:

```python
# conftest.py

def pytest_html_logo():
    """Return a URL or base64-encoded image for the report logo."""
    # Option 1: URL
    return "https://your-company.com/logo.png"
    
    # Option 2: Base64 (for offline reports)
    # import base64
    # with open("logo.png", "rb") as f:
    #     return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
```

### Custom Environment Info

Add custom metadata to the Environment section:

```python
# conftest.py
import os

def pytest_html_environment():
    """Add custom key-value pairs to the Environment section."""
    return {
        "Browser": "Chrome 120",
        "Environment": os.environ.get("ENV", "local"),
        "Build": os.environ.get("CI_BUILD_ID", "dev"),
        "Branch": os.environ.get("GIT_BRANCH", "main"),
    }
```

**Result:** The Environment panel in your report will show:

| Key | Value |
|-----|-------|
| Python | 3.11.5 |
| Platform | linux |
| Browser | Chrome 120 |
| Environment | staging |
| Build | 12345 |
| Branch | main |

---

## 📸 Screenshots

Capture and embed screenshots in your tests:

```python
from beautiful_report import report

def test_login_page(driver):
    driver.get("https://example.com/login")
    
    # Option 1: Capture from Selenium/Playwright driver
    report.screenshot("login_page", driver=driver)
    
    # Option 2: Use an existing file
    report.screenshot("saved_screenshot", path="screenshots/login.png")
    
    # Screenshots appear as thumbnails in the expanded test view
```

---

## 📋 Step Tracking

Log individual steps within your tests:

```python
from beautiful_report import report

@report.step("Opening login page")
def open_login(driver):
    driver.get("/login")

@report.step("Entering credentials")
def enter_credentials(driver, user, password):
    driver.find_element("id", "username").send_keys(user)
    driver.find_element("id", "password").send_keys(password)

@report.step("Clicking submit button")
def submit(driver):
    driver.find_element("css selector", "button[type='submit']").click()

def test_login_flow(driver):
    open_login(driver)
    enter_credentials(driver, "admin", "secret123")
    submit(driver)
    assert "Dashboard" in driver.title
```

**Result:** The report shows numbered steps with:
- Step name
- Duration
- Pass/fail status

---

## 🎯 Interactive Features

### Clickable Summary Cards

Click any summary card to filter results:

- **Total Tests** (teal gradient) → Shows all tests
- **Passed** (green) → Shows only passed tests
- **Failed** (red, pulsing) → Shows only failed tests
- **Skipped** (amber) → Shows only skipped tests

### Dark Mode

Toggle with the sun/moon button in the header. Your preference is saved in local storage.

### Expandable Test Details

Click any test to expand and see:
- Error tracebacks (with copy button)
- Captured stdout/stderr
- Test steps with timing
- Embedded screenshots

---

## 📁 Output Structure

```
reports/
├── report.html      # Interactive HTML report
├── report.json      # Machine-readable JSON results
└── history.sqlite   # Test run history database
```

---

## 🔧 API Reference

### `report.step(title)`

Decorator to mark a function as a test step.

```python
@report.step("Doing something important")
def my_function():
    pass
```

### `report.screenshot(name, driver=None, path=None)`

Capture or attach a screenshot.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | str | Name for the screenshot |
| `driver` | WebDriver | Selenium/Playwright driver (optional) |
| `path` | str | Path to existing image file (optional) |

### `report.log(message)`

Add a custom log message.

```python
report.log("User created successfully")
```

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

If this report saves your team from translating terminal output into status spreadsheets, [star the repository](https://github.com/godhiraj-code/pytest-glow-report). The [full case study](https://www.dhirajdas.dev/project/pytest-glow-report) covers the architecture, trade-offs, and implementation.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">
<p>Made with ❤️ for the testing community</p>
</div>
