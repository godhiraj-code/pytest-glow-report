import json
import sqlite3
import base64
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader

class HistoryManager:
    def __init__(self, db_path: str = "reports/history.sqlite"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Migration logic using user_version
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
    
    def add_run(self, passed: int, failed: int, skipped: int, duration: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO runs (timestamp, passed, failed, skipped, duration) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), passed, failed, skipped, duration)
            )

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cur.fetchall()]

class ReportBuilder:
    def __init__(self, output_dir: str = "reports", embed_threshold_kb: int = 50):
        self.output_dir = output_dir
        self.embed_threshold_bytes = embed_threshold_kb * 1024
        self.tests: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.env_info: Dict[str, str] = {}
        
        os.makedirs(output_dir, exist_ok=True)
        self.history = HistoryManager(os.path.join(output_dir, "history.sqlite"))

    def set_environment_info(self, info: Dict[str, str]):
        self.env_info = info

    def add_test_result(self, result: Dict[str, Any]):
        # Sanitize inputs here if needed
        # Logic to handle large attachments
        if "attachments" in result:
            for attachment in result["attachments"]:
                self._process_attachment(attachment)
        self.tests.append(result)

    def _process_attachment(self, attachment: Dict[str, Any]):
        # Check size, if > threshold, write to file and link
        content = attachment.get("content", "")
        if len(content) > self.embed_threshold_bytes:
             # Logic to save to file and update attachment to be a link
             # For now, just truncating or keeping as is for simplicity of first pass
             pass

    def build_report(self):
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        passed = sum(1 for t in self.tests if t['outcome'] == 'passed')
        failed = sum(1 for t in self.tests if t['outcome'] == 'failed')
        skipped = sum(1 for t in self.tests if t['outcome'] == 'skipped')
        
        # Save to history
        self.history.add_run(passed, failed, skipped, duration)
        
        context = {
            "title": "Test Report",
            "generated_at": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": duration,
            "summary": {"passed": passed, "failed": failed, "skipped": skipped, "total": len(self.tests)},
            "tests": self.tests,
            "environment": self.env_info,
            "history": self.history.get_history()
        }
        
        # Render
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("report.html.jinja2")
        
        html_out = template.render(context)
        
        output_path = os.path.join(self.output_dir, "report.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_out)
        
        # Also save JSON
        json_path = os.path.join(self.output_dir, "report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(context, f, default=str, indent=2)

        print(f"Report generated: {output_path}")
