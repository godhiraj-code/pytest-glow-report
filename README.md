# pytest-beautiful-report

A modern, zero-config HTML reporting plugin for PyTest and unittest.

## Features
- **Zero Config**: Just install and run.
- **Beautiful**: Responsive, dark code, search, filter, and sort out-of-the-box.
- **Rich Media**: Embed screenshots, logs, and videos.
- **History**: Track test results over time with built-in SQLite history.
- **Unittest Support**: Works with standard `unittest` without requiring pytest.

## Installation

```bash
# For PyTest users
pip install pytest-beautiful-report[pytest]

# For Unittest users
pip install pytest-beautiful-report
```

## Usage

### PyTest
```bash
pytest
```
The report will be generated in `reports/report.html`.

### Unittest
```bash
beautiful-report run -- unittest discover tests
```

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md).
