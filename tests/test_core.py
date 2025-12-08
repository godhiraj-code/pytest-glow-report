import os
import pytest
from beautiful_report.core import ReportBuilder

def test_builder_initialization(tmp_path):
    report_dir = tmp_path / "report"
    builder = ReportBuilder(output_dir=str(report_dir))
    assert os.path.exists(report_dir)
    assert os.path.exists(report_dir / "history.sqlite")

def test_add_test_result(tmp_path):
    builder = ReportBuilder(output_dir=str(tmp_path))
    result = {
        "nodeid": "test_one",
        "outcome": "passed",
        "duration": 0.1,
        "sections": []
    }
    builder.add_test_result(result)
    assert len(builder.tests) == 1
    assert builder.tests[0]["nodeid"] == "test_one"

def test_build_report(tmp_path):
    builder = ReportBuilder(output_dir=str(tmp_path))
    result = {
        "nodeid": "test_one",
        "outcome": "passed",
        "duration": 0.1,
        "sections": []
    }
    builder.add_test_result(result)
    builder.build_report()
    
    assert (tmp_path / "report.html").exists()
    assert (tmp_path / "report.json").exists()
