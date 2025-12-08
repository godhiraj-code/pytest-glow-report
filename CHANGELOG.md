# Changelog

All notable changes to this project will be documented in this file.

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
