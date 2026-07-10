"""Core report building and history functionality."""
import json
import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape


_ANSI_ESCAPE = re.compile(
    r"\x1b(?:"
    r"\[[0-?]*[ -/]*[@-~]"
    r"|\][^\x07]*(?:\x07|\x1b\\)"
    r"|[@-Z\\-_]"
    r")"
)
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _clean_text(value: str) -> str:
    """Remove terminal-only escape sequences while preserving text layout."""
    return _CONTROL_CHARACTERS.sub("", _ANSI_ESCAPE.sub("", value))


def _clean_for_output(value: Any) -> Any:
    """Recursively sanitize strings before serializing report data."""
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, dict):
        return {_clean_for_output(key): _clean_for_output(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_for_output(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_clean_for_output(item) for item in value)
    return value


class HistoryManager:
    """Manage test run history in a SQLite database."""

    def __init__(self, db_path: str = "reports/history.sqlite"):
        self.db_path = db_path
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA user_version")
            version = cur.fetchone()[0]
            if version == 0:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        passed INTEGER,
                        failed INTEGER,
                        skipped INTEGER,
                        duration REAL
                    )
                    """
                )
                conn.execute("PRAGMA user_version = 1")

    def add_run(self, passed: int, failed: int, skipped: int, duration: float) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO runs (timestamp, passed, failed, skipped, duration) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), passed, failed, skipped, duration),
            )

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cur.fetchall()]


class ReportBuilder:
    """Collect test results and generate HTML and JSON reports."""

    _OUTCOME_PRIORITY = {"passed": 0, "skipped": 1, "failed": 2}

    def __init__(self, output_dir: str = "reports", embed_threshold_kb: int = 50):
        self.output_dir = output_dir
        self.embed_threshold_bytes = embed_threshold_kb * 1024
        self.tests: List[Dict[str, Any]] = []
        self._test_indexes: Dict[str, int] = {}
        self.start_time = datetime.now()
        self.env_info: Dict[str, str] = {}
        self.context: Dict[str, Any] = {}

        os.makedirs(output_dir, exist_ok=True)
        self.history = HistoryManager(os.path.join(output_dir, "history.sqlite"))

    def set_environment_info(self, info: Dict[str, str]) -> None:
        self.env_info = info

    def add_test_result(self, result: Dict[str, Any]) -> None:
        """Add or merge a phase result, keeping one final row per pytest node."""
        nodeid = str(result["nodeid"])
        if nodeid not in self._test_indexes:
            self._test_indexes[nodeid] = len(self.tests)
            self.tests.append(result)
            return

        current = self.tests[self._test_indexes[nodeid]]
        current["duration"] = round(float(current.get("duration", 0)) + float(result.get("duration", 0)), 12)
        if self._OUTCOME_PRIORITY.get(result.get("outcome", "passed"), 0) > self._OUTCOME_PRIORITY.get(
            current.get("outcome", "passed"), 0
        ):
            current["outcome"] = result["outcome"]

        new_repr = result.get("longrepr")
        if new_repr and new_repr not in (current.get("longrepr") or ""):
            current["longrepr"] = "\n\n".join(filter(None, [current.get("longrepr"), new_repr]))

        for key in ("sections", "steps", "screenshots", "logs"):
            existing = current.setdefault(key, [])
            for item in result.get(key, []):
                if item not in existing:
                    existing.append(item)

    def build_report(self) -> None:
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        passed = sum(1 for test in self.tests if test["outcome"] == "passed")
        failed = sum(1 for test in self.tests if test["outcome"] == "failed")
        skipped = sum(1 for test in self.tests if test["outcome"] == "skipped")

        self.history.add_run(passed, failed, skipped, duration)
        context: Dict[str, Any] = {
            "title": "Glow Test Report",
            "generated_at": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": duration,
            "summary": {"passed": passed, "failed": failed, "skipped": skipped, "total": len(self.tests)},
            "tests": self.tests,
            "environment": self.env_info,
            "history": self.history.get_history(),
        }
        context.update(self.context)
        safe_context = _clean_for_output(context)

        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(default=True),
        )
        template = env.get_template("report.html.jinja2")
        html_out = template.render(safe_context)

        output_path = os.path.join(self.output_dir, "report.html")
        with open(output_path, "w", encoding="utf-8") as file_handle:
            file_handle.write(html_out)

        json_path = os.path.join(self.output_dir, "report.json")
        with open(json_path, "w", encoding="utf-8") as file_handle:
            json.dump(safe_context, file_handle, default=str, indent=2, ensure_ascii=False)

        print("Report generated: {}".format(output_path))
