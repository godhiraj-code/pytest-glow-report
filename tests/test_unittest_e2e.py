import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def test_cli_uses_glow_unittest_runner_and_preserves_exit_code(tmp_path):
    (tmp_path / "test_unittest_sample.py").write_text(
        """
import unittest
from beautiful_report import report

class Sample(unittest.TestCase):
    def test_context(self):
        report.log("unittest context")
        self.assertTrue(True)
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    completed = subprocess.run(
        [sys.executable, "-m", "beautiful_report.cli", "run", "--", "unittest", "discover", "-s", "."],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Running unittest with GlowReport" in completed.stdout
    data = json.loads((tmp_path / "reports" / "report.json").read_text(encoding="utf-8"))
    assert data["summary"] == {"passed": 1, "failed": 0, "skipped": 0, "total": 1}
    assert "unittest context" in data["tests"][0]["logs"][0]


def test_unittest_subtests_and_expected_outcomes_are_reported(tmp_path):
    (tmp_path / "test_unittest_outcomes.py").write_text(
        """
import unittest

class Outcomes(unittest.TestCase):
    def test_subtests(self):
        for value in (0, 1):
            with self.subTest(value=value):
                self.assertEqual(value, 0)

    @unittest.expectedFailure
    def test_expected_failure(self):
        self.fail("expected boom")

    @unittest.expectedFailure
    def test_unexpected_success(self):
        pass
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")

    completed = subprocess.run(
        [sys.executable, "-m", "beautiful_report.cli", "run", "--", "unittest", "discover", "-s", "."],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1, completed.stdout + completed.stderr
    data = json.loads((tmp_path / "reports" / "report.json").read_text(encoding="utf-8"))
    assert data["summary"] == {"passed": 1, "failed": 2, "skipped": 1, "total": 4}
    assert any("value=0" in item["nodeid"] and item["outcome"] == "passed" for item in data["tests"])
    assert any("value=1" in item["nodeid"] and item["outcome"] == "failed" for item in data["tests"])
    assert any(item["longrepr"] == "Unexpected success" for item in data["tests"])
    assert any("Expected failure" in item["longrepr"] for item in data["tests"])
