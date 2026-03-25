"""
Window Manager - Quet tat ca cua so dang mo tren Windows.
Su dung pygetwindow + ctypes Win32 API de lay thong tin PID va bounding box.
"""

import ctypes
import ctypes.wintypes
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Win32 API constants
GW_OWNER = 4
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
DWMWA_CLOAKED = 14

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

# System/background window titles to filter out
SYSTEM_TITLES = {
    "Program Manager",
    "MSCTFIME UI",
    "Default IME",
    "Windows Input Experience",
    "Settings",
    "Microsoft Text Input Application",
    "CiceroUIWndFrame",
}


def _is_alt_tab_window(hwnd: int) -> bool:
    """Check if a window would appear in Alt-Tab (real visible app window)."""
    # Must be visible
    if not user32.IsWindowVisible(hwnd):
        return False

    # Skip tool windows (no owner, not app window)
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if ex_style & WS_EX_TOOLWINDOW and not (ex_style & WS_EX_APPWINDOW):
        return False

    # Skip owned windows (child/popup windows)
    if user32.GetWindow(hwnd, GW_OWNER):
        return False

    # Check if cloaked (hidden by OS, e.g. virtual desktop)
    cloaked = ctypes.c_int(0)
    dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
    )
    if cloaked.value:
        return False

    return True


def _get_pid_from_hwnd(hwnd: int) -> int:
    """Get the process ID for a window handle."""
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def get_visible_windows() -> list[dict]:
    """
    Quet tat ca cua so dang hien thi tren desktop.

    Returns:
        List[dict]: Moi item co dang:
            {
                'title': 'Ten cua so',
                'pid': 1234,
                'hwnd': 56789
            }
    """
    windows = []

    def _enum_callback(hwnd, _lparam):
        if not _is_alt_tab_window(hwnd):
            return True

        # Get window title
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True

        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.strip()

        if not title or title in SYSTEM_TITLES:
            return True

        pid = _get_pid_from_hwnd(hwnd)

        windows.append({
            "title": title,
            "pid": pid,
            "hwnd": hwnd,
        })
        return True

    # Enumerate all top-level windows
    WNDENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )
    user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)

    logger.info(f"Found {len(windows)} visible window(s)")
    return windows


def get_window_rect_by_pid(pid: int) -> tuple[int, int, int, int] | None:
    """
    Lay bounding box cua cua so theo PID.

    Args:
        pid: Process ID cua cua so can lay.

    Returns:
        Tuple (left, top, width, height) hoac None neu khong tim thay.
    """
    result = None

    def _enum_callback(hwnd, _lparam):
        nonlocal result
        if not user32.IsWindowVisible(hwnd):
            return True

        window_pid = _get_pid_from_hwnd(hwnd)
        if window_pid != pid:
            return True

        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))

        left = rect.left
        top = rect.top
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        if width > 0 and height > 0:
            result = (left, top, width, height)
            return False  # Stop enumerating

        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )
    user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)

    return result


def get_window_rect_by_hwnd(hwnd: int) -> tuple[int, int, int, int] | None:
    """
    Lay bounding box cua cua so theo HWND (chinh xac hon PID).

    Returns:
        Tuple (left, top, width, height) hoac None.
    """
    rect = ctypes.wintypes.RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        left = rect.left
        top = rect.top
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if width > 0 and height > 0:
            return (left, top, width, height)
    return None


def cleanup_workspace(workspace_dir: str = "workspace"):
    """Don dep thu muc workspace sau khi xuat xong video."""
    import shutil
    from pathlib import Path

    ws = Path(workspace_dir)
    if ws.exists():
        shutil.rmtree(ws)
        logger.info(f"Cleaned up workspace: {ws}")
    ws.mkdir(parents=True, exist_ok=True)
    logger.info(f"Workspace ready: {ws}")
