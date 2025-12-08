"""
Core report building functionality.

Contains ReportBuilder for collecting test results and generating HTML reports,
and HistoryManager for SQLite-based test run history tracking.
"""
import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader


class HistoryManager:
    """Manages test run history in SQLite database."""
    
    def __init__(self, db_path: str = "reports/history.sqlite"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with schema migrations."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA user_version")
            version = cur.fetchone()[0]
            
            if version == 0:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        passed INTEGER,
                        failed INTEGER,
                        skipped INTEGER,
                        duration REAL
                    )
                """)
                conn.execute("PRAGMA user_version = 1")
    
    def add_run(self, passed: int, failed: int, skipped: int, duration: float) -> None:
        """Record a test run."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO runs (timestamp, passed, failed, skipped, duration) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), passed, failed, skipped, duration)
            )

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent test runs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cur.fetchall()]


class ReportBuilder:
    """Builds HTML test reports from collected test results."""
    
    def __init__(self, output_dir: str = "reports", embed_threshold_kb: int = 50):
        self.output_dir = output_dir
        self.embed_threshold_bytes = embed_threshold_kb * 1024
        self.tests: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.env_info: Dict[str, str] = {}
        self.context: Dict[str, Any] = {}
        
        os.makedirs(output_dir, exist_ok=True)
        self.history = HistoryManager(os.path.join(output_dir, "history.sqlite"))

    def set_environment_info(self, info: Dict[str, str]) -> None:
        """Set environment information to display in report."""
        self.env_info = info

    def add_test_result(self, result: Dict[str, Any]) -> None:
        """Add a test result to the report."""
        self.tests.append(result)

    def build_report(self) -> None:
        """Generate the HTML and JSON reports."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        passed = sum(1 for t in self.tests if t['outcome'] == 'passed')
        failed = sum(1 for t in self.tests if t['outcome'] == 'failed')
        skipped = sum(1 for t in self.tests if t['outcome'] == 'skipped')
        
        self.history.add_run(passed, failed, skipped, duration)
        
        base_context = {
            "title": "Glow Test Report",
            "generated_at": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": duration,
            "summary": {"passed": passed, "failed": failed, "skipped": skipped, "total": len(self.tests)},
            "tests": self.tests,
            "environment": self.env_info,
            "history": self.history.get_history()
        }
        base_context.update(self.context)
        context = base_context
        
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("report.html.jinja2")
        
        html_out = template.render(context)
        
        output_path = os.path.join(self.output_dir, "report.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_out)
        
        json_path = os.path.join(self.output_dir, "report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(context, f, default=str, indent=2)

        print(f"Report generated: {output_path}")
