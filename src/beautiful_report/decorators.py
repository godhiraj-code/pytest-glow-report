"""
Decorators for custom test steps and screenshot capture.

Usage:
    from beautiful_report import report

    @report.step("Logging in")
    def login():
        ...

    report.screenshot("login_page")
    report.log("Custom message")
"""
import base64
import contextvars
import functools
import inspect
import os
import time
from datetime import datetime
from typing import Callable, List, Dict, Any, Optional

# Context-local storage keeps concurrent or nested test execution isolated.
_current_test_context: contextvars.ContextVar[Optional["TestContext"]] = contextvars.ContextVar(
    "glow_test_context", default=None
)


class TestContext:
    """Context manager for tracking steps and screenshots within a test."""
    
    def __init__(self) -> None:
        self.steps: List[Dict[str, Any]] = []
        self.screenshots: List[str] = []
        self.logs: List[str] = []
        self._step_counter = 0
    
    def add_step(self, name: str, status: str, duration: float) -> None:
        self._step_counter += 1
        self.steps.append({
            "number": self._step_counter,
            "name": name,
            "status": status,
            "duration": round(duration, 4),
            "timestamp": datetime.now().isoformat()
        })
    
    def add_screenshot(self, path_or_base64: str) -> None:
        """Add a screenshot (file path or base64 string)."""
        self.screenshots.append(path_or_base64)
    
    def add_log(self, message: str) -> None:
        self.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": self.steps,
            "screenshots": self.screenshots,
            "logs": self.logs
        }


def get_current_context() -> Optional[TestContext]:
    """Get the current test context (if any)."""
    return _current_test_context.get()


def set_current_context(ctx: Optional[TestContext]) -> None:
    """Set the current test context."""
    _current_test_context.set(ctx)


class report:
    """Static class providing decorators and methods for report customization."""
    
    @staticmethod
    def step(title: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator to mark a function as a test step.
        
        The step will be logged with its duration and pass/fail status.
        
        Example:
            @report.step("Uploading file")
            def upload_file():
                ...
        """
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    ctx = get_current_context()
                    start = time.time()
                    print(f"STEP: {title}")

                    try:
                        result = await func(*args, **kwargs)
                        duration = time.time() - start
                        if ctx:
                            ctx.add_step(title, "passed", duration)
                        print(f"   PASSED ({duration:.4f}s)")
                        return result
                    except Exception as e:
                        duration = time.time() - start
                        if ctx:
                            ctx.add_step(title, "failed", duration)
                        print(f"   FAILED ({duration:.4f}s): {str(e)}")
                        raise

                return async_wrapper

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                ctx = get_current_context()
                start = time.time()
                
                # Log step start
                print(f"STEP: {title}")
                
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start
                    
                    if ctx:
                        ctx.add_step(title, "passed", duration)
                    
                    print(f"   PASSED ({duration:.4f}s)")
                    return result
                    
                except Exception as e:
                    duration = time.time() - start
                    
                    if ctx:
                        ctx.add_step(title, "failed", duration)
                    
                    print(f"   FAILED ({duration:.4f}s): {str(e)}")
                    raise
                    
            return wrapper
        return decorator
    
    @staticmethod
    def screenshot(name: str = "screenshot", driver: Any = None, path: Optional[str] = None) -> Optional[str]:
        """
        Capture and add a screenshot to the current test.
        
        Args:
            name: Name for the screenshot file
            driver: Selenium/Playwright driver (optional, if you want auto-capture)
            path: Existing file path to use instead of capturing
        
        Example:
            # Using existing file
            report.screenshot("login_page", path="screenshots/login.png")
            
            # Auto-capture from Selenium driver
            report.screenshot("after_click", driver=selenium_driver)
        """
        ctx = get_current_context()
        
        if path and os.path.exists(path):
            # Use existing file - convert to base64
            with open(path, "rb") as f:
                content = f.read()
            ext = os.path.splitext(path)[1].lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            b64 = base64.b64encode(content).decode("utf-8")
            data_uri = f"data:{mime};base64,{b64}"
            
            if ctx:
                ctx.add_screenshot(data_uri)
            print(f"Screenshot added: {name}")
            return data_uri
            
        elif driver:
            # Auto-capture from Selenium/Playwright driver
            try:
                # Try Selenium-style
                screenshot_bytes = driver.get_screenshot_as_png()
            except AttributeError:
                try:
                    # Try Playwright-style
                    screenshot_bytes = driver.screenshot()
                except Exception:
                    print("Could not capture screenshot from driver")
                    return None
            
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            data_uri = f"data:image/png;base64,{b64}"
            
            if ctx:
                ctx.add_screenshot(data_uri)
            print(f"Screenshot captured: {name}")
            return data_uri
        
        else:
            print(f"Screenshot '{name}': No path or driver provided")
            return None
    
    @staticmethod
    def log(message: str) -> None:
        """
        Add a custom log message to the current test.
        
        Example:
            report.log("User created successfully")
        """
        ctx = get_current_context()
        if ctx:
            ctx.add_log(message)
        print(f"LOG: {message}")
    
    @staticmethod
    def attach(name: str, content: str, content_type: str = "text/plain") -> None:
        """
        Attach arbitrary content to the current test.
        
        Args:
            name: Name of the attachment
            content: String content or base64 data
            content_type: MIME type
        
        Example:
            report.attach("api_response", json.dumps(response), "application/json")
        """
        ctx = get_current_context()
        if ctx:
            ctx.logs.append(f"[ATTACHMENT: {name}] {content[:100]}{'...' if len(content) > 100 else ''}")
        print(f"Attached: {name} ({content_type})")
