import unittest
import time

class TestSimple(unittest.TestCase):
    def test_pass(self):
        time.sleep(0.1)
        self.assertTrue(True)

    def test_fail(self):
        time.sleep(0.1)
        self.fail("This validation failed")

    @unittest.skip("Skipping for demo")
    def test_skip(self):
        pass
