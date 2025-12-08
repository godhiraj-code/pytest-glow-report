"""
Custom pytest hooks for report customization.

These hooks allow users to customize the report logo and environment info
by implementing them in their conftest.py.
"""
from typing import Dict, Optional

import pytest


@pytest.hookspec(firstresult=True)
def pytest_html_logo() -> Optional[str]:
    """
    Return a URL or base64-encoded image string for the report logo.
    
    Example in conftest.py:
        def pytest_html_logo():
            return "https://example.com/logo.png"
    """


@pytest.hookspec(firstresult=True)
def pytest_html_environment() -> Optional[Dict[str, str]]:
    """
    Return a dictionary of environment info to display in the report.
    
    Example in conftest.py:
        def pytest_html_environment():
            return {"Browser": "Chrome", "Environment": "staging"}
    """
