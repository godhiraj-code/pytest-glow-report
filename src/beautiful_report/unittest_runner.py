import unittest
import sys
import time
from .core import ReportBuilder

class BeautifulTestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity, builder):
        super().__init__(stream, descriptions, verbosity)
        self.builder = builder
        self._start_time = None

    def startTest(self, test):
        super().startTest(test)
        self._start_time = time.time()

    def addSuccess(self, test):
        super().addSuccess(test)
        self._add_result(test, "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._add_result(test, "failed", err)

    def addError(self, test, err):
        super().addError(test, err)
        self._add_result(test, "failed", err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._add_result(test, "skipped", reason=reason)

    def _add_result(self, test, outcome, err=None, reason=None):
        duration = time.time() - self._start_time if self._start_time else 0
        
        longrepr = None
        if err:
            try:
                longrepr = str(err[1]) # Just the error message for now
            except:
                longrepr = str(err)
        if reason:
            longrepr = reason

        result = {
            "nodeid": str(test),
            "outcome": outcome,
            "duration": duration,
            "longrepr": longrepr,
            "sections": [] # Capture stdout/stderr if possible
        }
        self.builder.add_test_result(result)

class BeautifulTestRunner(unittest.TextTestRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.builder = ReportBuilder()
        # Environment info could be added here
    
    def _makeResult(self):
        return BeautifulTestResult(self.stream, self.descriptions, self.verbosity, self.builder)
    
    def run(self, test):
        result = super().run(test)
        self.builder.build_report()
        return result
