"""
Unittest runner integration for pytest-glow-report.

Provides BeautifulTestRunner and BeautifulTestResult to generate
HTML reports when running tests with Python's unittest framework.
"""
import sys
import time
import unittest
from typing import Any, Dict, Optional, Tuple, Union

from .core import ReportBuilder
from .decorators import TestContext, set_current_context


class BeautifulTestResult(unittest.TextTestResult):
    """Custom TestResult that reports to ReportBuilder."""
    
    def __init__(self, stream: Any, descriptions: bool, verbosity: int, builder: ReportBuilder):
        super().__init__(stream, descriptions, verbosity)
        self.builder = builder
        self._start_time: Optional[float] = None
        self._context: Optional[TestContext] = None
        self._subtest_results = 0

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self._start_time = time.time()
        self._context = TestContext()
        self._subtest_results = 0
        set_current_context(self._context)

    def stopTest(self, test: unittest.TestCase) -> None:
        set_current_context(None)
        self._context = None
        super().stopTest(test)

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        if self._subtest_results == 0:
            self._add_result(test, "passed")

    def addFailure(self, test: unittest.TestCase, err: Tuple[Any, ...]) -> None:
        super().addFailure(test, err)
        self._add_result(test, "failed", err)

    def addError(self, test: unittest.TestCase, err: Tuple[Any, ...]) -> None:
        super().addError(test, err)
        self._add_result(test, "failed", err)

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self._add_result(test, "skipped", reason=reason)

    def addSubTest(
        self,
        test: unittest.TestCase,
        subtest: unittest.TestCase,
        err: Optional[Tuple[Any, ...]],
    ) -> None:
        super().addSubTest(test, subtest, err)
        self._subtest_results += 1
        if err is None:
            self._add_result(subtest, "passed")
        elif err and err[0] is unittest.SkipTest:
            self._add_result(subtest, "skipped", reason=str(err[1]))
        else:
            self._add_result(subtest, "failed", err)

    def addExpectedFailure(self, test: unittest.TestCase, err: Tuple[Any, ...]) -> None:
        super().addExpectedFailure(test, err)
        self._add_result(test, "skipped", reason=f"Expected failure: {err[1]}")

    def addUnexpectedSuccess(self, test: unittest.TestCase) -> None:
        super().addUnexpectedSuccess(test)
        self._add_result(test, "failed", reason="Unexpected success")

    def _add_result(
        self, 
        test: unittest.TestCase, 
        outcome: str, 
        err: Optional[Tuple[Any, ...]] = None, 
        reason: Optional[str] = None
    ) -> None:
        """Record a test result to the builder."""
        duration = time.time() - self._start_time if self._start_time else 0
        
        longrepr = None
        if err:
            try:
                longrepr = str(err[1])
            except (IndexError, TypeError):
                longrepr = str(err)
        if reason:
            longrepr = reason

        result: Dict[str, Any] = {
            "nodeid": str(test),
            "outcome": outcome,
            "duration": duration,
            "longrepr": longrepr,
            "sections": [],
            "steps": [],
            "screenshots": [],
            "logs": [],
        }
        if self._context is not None:
            result.update(self._context.to_dict())
        self.builder.add_test_result(result)


class BeautifulTestRunner(unittest.TextTestRunner):
    """Custom TestRunner that generates HTML reports."""
    
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.builder = ReportBuilder()
        self.builder.set_environment_info({
            "Python": sys.version.split()[0],
            "Platform": sys.platform,
        })
    
    def _makeResult(self) -> BeautifulTestResult:
        return BeautifulTestResult(self.stream, self.descriptions, self.verbosity, self.builder)
    
    def run(
        self, test: Union[unittest.TestSuite, unittest.TestCase]
    ) -> unittest.TextTestResult:
        result = super().run(test)
        self.builder.build_report()
        return result
