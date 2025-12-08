import pytest
import time
import logging

def test_pass():
    """A simple passing test."""
    time.sleep(0.1)
    assert True

def test_fail():
    """A simple failing test."""
    time.sleep(0.1)
    print("This will be printed to stdout")
    logging.warning("This is a warning log")
    assert False, "This test failed on purpose"

@pytest.mark.skip(reason="Skipping this one")
def test_skip():
    assert False

@pytest.mark.parametrize("i", range(3))
def test_params(i):
    """Parametrized test."""
    time.sleep(0.05)
    assert i in [0, 1, 2]
