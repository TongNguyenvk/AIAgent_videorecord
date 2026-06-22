"""
App Launcher Module - Automatically launch applications for OS recording.

Supports:
  - Office apps: Excel, Word, PowerPoint
  - Browsers: Chrome, Edge, Firefox
  - Simple apps: Notepad, Calculator, Paint
  - Custom apps: Any .exe path

Features:
  - Auto-detect existing windows
  - Launch if not found
  - Open files for Office apps
  - Open URLs for browsers
  - Retry logic with timeout
  - Window verification

Usage:
    launcher = AppLauncher()
    
    # Launch Excel with file
    instance = launcher.launch("excel", file_path="C:/data.xlsx")
    
    # Launch Chrome with URL
    instance = launcher.launch("chrome", url="https://google.com")
    
    # Launch Notepad
    instance = launcher.launch("notepad")
"""

import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from .window_manager import get_visible_windows

logger = logging.getLogger(__name__)


@dataclass
class AppInstance:
    """Represents a launched application instance."""
    pid: int
    executable: str
    window_title: str
    hwnd: int
    app_type: str
    file_path: Optional[str] = None
    url: Optional[str] = None


class AppLaunchError(Exception):
    """Raised when app launch fails."""
    pass


class AppLauncher:
    """Launcher for Windows applications."""
    
    # App type configurations
    APP_CONFIGS = {
        "excel": {
            "executable": "excel.exe",
            "start_command": "start excel",
            "window_filter": lambda w: ("excel" in w["title"].lower() or "book" in w["title"].lower()),
            "label": "Microsoft Excel",
            "wait_seconds": 4,
        },
        "word": {
            "executable": "winword.exe",
            "start_command": "start winword",
            "window_filter": lambda w: ("word" in w["title"].lower() or "document" in w["title"].lower()),
            "label": "Microsoft Word",
            "wait_seconds": 4,
        },
        "powerpoint": {
            "executable": "powerpnt.exe",
            "start_command": "start powerpnt",
            "window_filter": lambda w: ("powerpoint" in w["title"].lower() or "presentation" in w["title"].lower()),
            "label": "Microsoft PowerPoint",
            "wait_seconds": 5,
        },
        "chrome": {
            "executable": "chrome.exe",
            "start_command": 'start chrome',
            "window_filter": lambda w: ("google chrome" in w["title"].lower() or ("chrome" in w["title"].lower() and "edge" not in w["title"].lower())),
            "label": "Google Chrome",
            "wait_seconds": 3,
        },
        "edge": {
            "executable": "msedge.exe",
            "start_command": 'start msedge',
            "window_filter": lambda w: ("edge" in w["title"].lower() or "msedge" in w["title"].lower()),
            "label": "Microsoft Edge",
            "wait_seconds": 3,
        },
        "firefox": {
            "executable": "firefox.exe",
            "start_command": 'start firefox',
            "window_filter": lambda w: ("firefox" in w["title"].lower() or "mozilla" in w["title"].lower()),
            "label": "Mozilla Firefox",
            "wait_seconds": 3,
        },
        "notepad": {
            "executable": "notepad.exe",
            "start_command": "notepad.exe",
            "window_filter": lambda w: "notepad" in w["title"].lower() and " - notepad" in w["title"].lower(),
            "label": "Notepad",
            "wait_seconds": 2,
        },
        "calculator": {
            "executable": "calc.exe",
            "start_command": "calc.exe",
            "window_filter": lambda w: "calculator" in w["title"].lower(),
            "label": "Calculator",
            "wait_seconds": 2,
        },
        "paint": {
            "executable": "mspaint.exe",
            "start_command": "mspaint.exe",
            "window_filter": lambda w: "paint" in w["title"].lower(),
            "label": "Paint",
            "wait_seconds": 2,
        },
    }
    
    def __init__(self, exclude_ide_windows: bool = True):
        """
        Initialize AppLauncher.
        
        Args:
            exclude_ide_windows: If True, filter out IDE windows (VS Code, Cursor, etc.)
        """
        self.exclude_ide_windows = exclude_ide_windows
    
    def _is_ide_window(self, title: str) -> bool:
        """Check if window title belongs to an IDE."""
        if not self.exclude_ide_windows:
            return False
        
        title_lower = title.lower()
        ide_keywords = ["visual studio code", "cursor", "kiro", ".py", "vscode", "code - "]
        return any(keyword in title_lower for keyword in ide_keywords)
    
    def _find_window(self, filter_fn: Callable, exclude_ide: bool = True) -> Optional[dict]:
        """
        Find a window matching the filter function.
        
        Args:
            filter_fn: Function that takes a window dict and returns True if it matches
            exclude_ide: If True, exclude IDE windows
            
        Returns:
            Window dict or None if not found
        """
        windows = get_visible_windows()
        
        for window in windows:
            # Skip IDE windows if requested
            if exclude_ide and self._is_ide_window(window["title"]):
                continue
            
            # Apply filter
            if filter_fn(window):
                return window
        
        return None
    
    def _launch_process(self, command: str, wait_seconds: float = 2) -> subprocess.Popen:
        """
        Launch a process and wait for it to start.
        
        Args:
            command: Command to execute
            wait_seconds: Seconds to wait after launch
            
        Returns:
            Popen object
        """
        logger.info(f"Launching: {command}")
        proc = subprocess.Popen(command, shell=True)
        time.sleep(wait_seconds)
        return proc
    
    def launch(
        self,
        app_type: str,
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        wait_seconds: Optional[int] = None,
        max_retries: int = 3,
        force_new: bool = False,
    ) -> AppInstance:
        """
        Launch an application.
        
        Args:
            app_type: Type of app ("excel", "word", "chrome", etc.)
            file_path: Optional file to open (for Office apps)
            url: Optional URL to open (for browsers)
            wait_seconds: Override default wait time
            max_retries: Maximum number of launch attempts
            force_new: If True, always launch new instance (don't reuse existing)
            
        Returns:
            AppInstance with PID and metadata
            
        Raises:
            AppLaunchError: If launch fails after retries
        """
        app_type = app_type.lower()
        
        # Get app configuration
        if app_type not in self.APP_CONFIGS:
            # Try custom app
            return self._launch_custom_app(app_type, file_path, wait_seconds, max_retries)
        
        config = self.APP_CONFIGS[app_type]
        executable = config["executable"]
        start_command = config["start_command"]
        window_filter = config["window_filter"]
        label = config["label"]
        default_wait = config["wait_seconds"]
        
        if wait_seconds is None:
            wait_seconds = default_wait

        if app_type in ["chrome", "edge", "firefox"] and url:
            force_new = True
        if app_type in ["excel", "word", "powerpoint"] and not file_path:
            force_new = True

        existing_hwnds = set()
        if force_new:
            existing_hwnds = {w["hwnd"] for w in get_visible_windows()}
        
        # Check for existing window (unless force_new)
        if not force_new:
            existing_window = self._find_window(window_filter)
            if existing_window:
                logger.info(f"Found existing {label} window (PID={existing_window['pid']})")
                return AppInstance(
                    pid=existing_window["pid"],
                    executable=executable,
                    window_title=existing_window["title"],
                    hwnd=existing_window["hwnd"],
                    app_type=app_type,
                    file_path=file_path,
                    url=url,
                )
        
        # Build launch command
        launch_cmd = self._build_launch_command(
            app_type, start_command, file_path, url
        )
        
        # Try to launch with retries
        for attempt in range(max_retries):
            try:
                logger.info(f"Launch attempt {attempt + 1}/{max_retries}: {label}")
                
                # Launch process
                self._launch_process(launch_cmd, wait_seconds)
                
                # Find the new window
                if force_new and existing_hwnds:
                    new_window = self._find_window(
                        lambda w: window_filter(w) and w["hwnd"] not in existing_hwnds
                    )
                    if not new_window:
                        logger.warning("New window not found, falling back to any matching window")
                        new_window = self._find_window(window_filter)
                else:
                    new_window = self._find_window(window_filter)
                
                if new_window:
                    logger.info(f"Successfully launched {label} (PID={new_window['pid']})")
                    return AppInstance(
                        pid=new_window["pid"],
                        executable=executable,
                        window_title=new_window["title"],
                        hwnd=new_window["hwnd"],
                        app_type=app_type,
                        file_path=file_path,
                        url=url,
                    )
                
                # Window not found, retry
                logger.warning(f"Window not found after launch, retrying...")
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Launch attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        # All retries failed
        raise AppLaunchError(
            f"Failed to launch {label} after {max_retries} attempts"
        )
    
    def _build_launch_command(
        self,
        app_type: str,
        base_command: str,
        file_path: Optional[str],
        url: Optional[str],
    ) -> str:
        """
        Build the launch command with file/URL if provided.
        
        Args:
            app_type: Type of app
            base_command: Base command to launch app
            file_path: Optional file path
            url: Optional URL
            
        Returns:
            Complete launch command
        """
        # Office apps: open with file
        if app_type in ["excel", "word", "powerpoint"] and file_path:
            # Validate file exists
            if not Path(file_path).exists():
                raise AppLaunchError(f"File not found: {file_path}")
            
            # Quote path for spaces
            quoted_path = f'"{file_path}"'
            return f'{base_command} {quoted_path}'
        
        # Browsers: open with URL
        if app_type in ["chrome", "edge", "firefox"] and url:
            quoted_url = f'"{url}"'
            if app_type in ["chrome", "edge"]:
                return f'{base_command} --new-window {quoted_url}'
            if app_type == "firefox":
                return f'{base_command} -new-window {quoted_url}'
            return f'{base_command} {quoted_url}'

        if app_type == "word" and not file_path:
            return f'{base_command} /w'
        
        # Default: just launch app
        return base_command
    
    def _launch_custom_app(
        self,
        app_name: str,
        file_path: Optional[str],
        wait_seconds: Optional[int],
        max_retries: int,
    ) -> AppInstance:
        """
        Launch a custom application by name or path.
        
        Args:
            app_name: App name (e.g., "mspaint.exe") or full path
            file_path: Optional file to open
            wait_seconds: Wait time after launch
            max_retries: Maximum retries
            
        Returns:
            AppInstance
            
        Raises:
            AppLaunchError: If launch fails
        """
        # Ensure .exe extension
        if not app_name.lower().endswith(".exe"):
            app_name += ".exe"
        
        # Extract base name for window detection
        base_name = Path(app_name).stem.lower()
        
        # Build command
        if file_path:
            if not Path(file_path).exists():
                raise AppLaunchError(f"File not found: {file_path}")
            command = f'start {app_name} "{file_path}"'
        else:
            command = f'start {app_name}'
        
        # Default wait time
        if wait_seconds is None:
            wait_seconds = 3
        
        # Window filter: match base name in title
        def custom_filter(w):
            return base_name in w["title"].lower()
        
        # Try to launch
        for attempt in range(max_retries):
            try:
                logger.info(f"Launching custom app: {app_name} (attempt {attempt + 1}/{max_retries})")
                
                self._launch_process(command, wait_seconds)
                
                # Find window
                new_window = self._find_window(custom_filter, exclude_ide=False)
                
                if new_window:
                    logger.info(f"Successfully launched {app_name} (PID={new_window['pid']})")
                    return AppInstance(
                        pid=new_window["pid"],
                        executable=app_name,
                        window_title=new_window["title"],
                        hwnd=new_window["hwnd"],
                        app_type="custom",
                        file_path=file_path,
                    )
                
                logger.warning(f"Window not found, retrying...")
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Launch attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        raise AppLaunchError(
            f"Failed to launch {app_name} after {max_retries} attempts"
        )
    
    def verify_instance(self, instance: AppInstance) -> bool:
        """
        Verify that an app instance is still running.
        
        Args:
            instance: AppInstance to verify
            
        Returns:
            True if window still exists, False otherwise
        """
        windows = get_visible_windows()
        
        for window in windows:
            if window["pid"] == instance.pid and window["hwnd"] == instance.hwnd:
                return True
        
        return False
    
    @staticmethod
    def get_supported_apps() -> list[str]:
        """Get list of supported app types."""
        return list(AppLauncher.APP_CONFIGS.keys())


# Convenience functions
def launch_excel(file_path: Optional[str] = None, **kwargs) -> AppInstance:
    """Launch Excel with optional file."""
    launcher = AppLauncher()
    return launcher.launch("excel", file_path=file_path, **kwargs)


def launch_word(file_path: Optional[str] = None, **kwargs) -> AppInstance:
    """Launch Word with optional file."""
    launcher = AppLauncher()
    return launcher.launch("word", file_path=file_path, **kwargs)


def launch_chrome(url: Optional[str] = None, **kwargs) -> AppInstance:
    """Launch Chrome with optional URL."""
    launcher = AppLauncher()
    return launcher.launch("chrome", url=url, **kwargs)


def launch_notepad(**kwargs) -> AppInstance:
    """Launch Notepad."""
    launcher = AppLauncher()
    return launcher.launch("notepad", **kwargs)


if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    
    print("Testing App Launcher...")
    print(f"Supported apps: {AppLauncher.get_supported_apps()}")
    
    launcher = AppLauncher()
    
    # Test Notepad
    print("\n1. Testing Notepad launch...")
    try:
        instance = launcher.launch("notepad")
        print(f"   Success! PID={instance.pid}, Title='{instance.window_title}'")
        
        # Verify
        if launcher.verify_instance(instance):
            print("   Verification: OK")
        else:
            print("   Verification: FAILED")
    except AppLaunchError as e:
        print(f"   Failed: {e}")
    
    print("\nTest complete!")
