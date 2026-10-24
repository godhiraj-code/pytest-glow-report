# Changelog

All notable changes to this project will be documented in this file.

## [0.1.4] - Unreleased

### Fixed
- Mark all custom hook examples optional. Users who copied older README examples must add `@pytest.hookimpl(optionalhook=True)` (and `import pytest`) to each hook.
- Handle successful setup/call retries from pytest-rerunfailures without crashing on transient `rerun` outcomes.
- Count setup/teardown errors separately from failed calls and display plain skip reasons.
- Preserve errors in SQLite history with schema version 2; existing version 1 rows retain their data and receive zero errors. Runs with errors are not stable.
- Count tests rather than phases in `summary.total`, including a test whose passing call has a teardown error.
- Include errors in failure metrics and banners, align risk labels/colors, and do not give runs without passes 100% quality, Low risk, or confetti.
- Highlight Errors/Xfailed/Xpassed filters and result badges consistently.
- Wrap the mobile header and constrain its search field so the theme toggle stays reachable.
- Remove the stale generated `_version.py` from the source and wheel; package version remains 0.1.4.
- Clarify that HTML styles and interactive controls require internet access to public CDNs.

### JSON compatibility
- New summary keys: `error`, `xfailed`, and `xpassed`, alongside `passed`, `failed`, `skipped`, and `total`. The earlier 0.1.4 preview's plural `errors` key is now singular `error`.
- New final outcome values: `error`, `xfailed`, and `xpassed`. Setup/teardown errors no longer count as `failed`.
- Each pytest result includes `phase_outcomes`, mapping each reported phase to its latest outcome, including passing setup/teardown. Later retries replace earlier values for that phase. Transient plugin outcomes such as `rerun` are excluded from summary counts.
- Passing setup/teardown phases do not override a call outcome or contribute to counts. A call result plus a teardown error can contribute to two outcome counts, while `total` remains the number of test rows.
- Pass rate uses `passed / (passed + failed + error)`; an empty denominator displays 0% and Not assessed risk.

## [0.1.3]

### Changed
- Added async step support and rendered-report copy/log regression coverage.

## [0.1.2]

### Changed
- Updated package metadata and documentation links.

## [0.1.1] - Unreleased

### Fixed
- Correct package dependency metadata so source distributions build and install.
- Capture pytest setup, call, and teardown failures without duplicate test rows.
- Preserve step, screenshot, and custom-log context during test execution.
- Implement `--no-glow-report` and prevent false all-passing reports on abnormal pytest exits.
- Escape untrusted report content, safely copy rendered errors, and strip terminal escape/control characters.
- Keep report content readable when optional CDN enhancements are unavailable.
- Exercise package builds, wheel installs, and the real unittest runner in CI.

## [0.1.0] - 2025-12-08

### Added
- Initial release of `pytest-glow-report`
- Core ReportBuilder with SQLite history tracking
- PyTest plugin with automatic report generation
- Unittest support via `glow-report run` CLI
- Beautiful HTML template with:
  - Glassmorphism design
  - Dark/light mode toggle
  - Animated floating orb backgrounds
  - Clickable summary cards for filtering
  - Test run history visualization
  - Step tracking with `@report.step()` decorator
  - Screenshot capture support
- Custom logo and environment hooks
- JSON report output alongside HTML
