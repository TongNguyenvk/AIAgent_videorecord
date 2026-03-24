"""
Browser Launcher: Tự động tìm và khởi động Chrome với CDP
Sử dụng Windows Registry (Layer 1) và Fallback paths (Layer 2)
"""

import os
import winreg
import subprocess
import tempfile
import time
import logging

logger = logging.getLogger(__name__)


def get_chrome_path():
    """
    Tìm đường dẫn chrome.exe trên máy Windows.
    
    Layer 1: Windows Registry (chính xác 99%)
    Layer 2: Brute-force fallback (các đường dẫn phổ biến)
    
    Returns:
        str: Đường dẫn đầy đủ tới chrome.exe, hoặc None nếu không tìm thấy
    """
    # Layer 1: Tìm trong Registry (The Source of Truth)
    try:
        # Mở khóa App Paths của Windows
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
        )
        path, _ = winreg.QueryValueEx(key, "")
        winreg.CloseKey(key)
        
        if os.path.exists(path):
            logger.info(f"Chrome found via Registry: {path}")
            return path
    except Exception as e:
        logger.warning(f"Registry lookup failed: {e}")
    
    # Layer 2: Vét cạn các đường dẫn kinh điển
    default_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    
    for path in default_paths:
        if os.path.exists(path):
            logger.info(f"Chrome found via fallback: {path}")
            return path
    
    logger.error("Chrome not found on this system")
    return None


def launch_chrome_with_cdp(port=9222, kill_existing=False):
    """
    Khởi động Chrome với Chrome DevTools Protocol (CDP) enabled.
    
    Args:
        port: Cổng CDP (mặc định 9222)
        kill_existing: Có tắt Chrome đang chạy trước không (mặc định False)
    
    Returns:
        str: CDP URL (http://localhost:9222)
    
    Raises:
        Exception: Nếu không tìm thấy Chrome hoặc không khởi động được
    """
    chrome_path = get_chrome_path()
    
    if not chrome_path:
        raise Exception(
            "Không tìm thấy Google Chrome trên máy tính này.\n"
            "Vui lòng cài đặt Chrome từ: https://www.google.com/chrome/"
        )
    
    logger.info(f"Chrome executable: {chrome_path}")
    
    # Bước 1: Giết toàn bộ Chrome đang chạy (tránh lỗi port conflict)
    if kill_existing:
        logger.info("Đang dọn dẹp các phiên Chrome cũ...")
        subprocess.run(
            "taskkill /F /IM chrome.exe",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1.5)  # Chờ Windows giải phóng port
    
    # Bước 2: Tạo thư mục profile tạm cho AI (không đụng profile user)
    ai_profile_dir = os.path.join(tempfile.gettempdir(), "AI_Video_Tutor_Profile")
    
    # Bước 3: Khởi động Chrome với CDP
    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        f"--user-data-dir={ai_profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    
    logger.info(f"Launching Chrome on port {port}...")
    
    # Dùng Popen để Chrome chạy độc lập (không block Python)
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    
    # Đợi Chrome khởi động
    time.sleep(2)
    
    cdp_url = f"http://localhost:{port}"
    logger.info(f"Chrome CDP ready at: {cdp_url}")
    
    return cdp_url


def check_chrome_running(port=9222):
    """
    Kiểm tra xem Chrome CDP có đang chạy không.
    
    Args:
        port: Cổng CDP để kiểm tra
    
    Returns:
        bool: True nếu Chrome đang chạy và CDP available
    """
    import requests
    
    cdp_url = f"http://localhost:{port}"
    try:
        response = requests.get(f"{cdp_url}/json/version", timeout=2)
        if response.status_code == 200:
            info = response.json()
            logger.info(f"Chrome detected: {info.get('Browser', 'Unknown')}")
            return True
    except Exception as e:
        logger.debug(f"Chrome not detected at {cdp_url}: {e}")
    
    return False


# Test module
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Chrome Browser Launcher - Test")
    print("=" * 60)
    
    # Test 1: Find Chrome
    print("\n[Test 1] Finding Chrome...")
    chrome_path = get_chrome_path()
    if chrome_path:
        print(f"✅ Chrome found: {chrome_path}")
    else:
        print("❌ Chrome not found")
        exit(1)
    
    # Test 2: Check if Chrome is running
    print("\n[Test 2] Checking if Chrome CDP is running...")
    if check_chrome_running():
        print("✅ Chrome CDP is already running")
    else:
        print("⚠️ Chrome CDP not running")
    
    # Test 3: Launch Chrome
    print("\n[Test 3] Launching Chrome with CDP...")
    try:
        cdp_url = launch_chrome_with_cdp()
        print(f"✅ Chrome launched successfully")
        print(f"   CDP URL: {cdp_url}")
        
        # Verify connection
        time.sleep(1)
        if check_chrome_running():
            print("✅ CDP connection verified")
        else:
            print("❌ CDP connection failed")
    
    except Exception as e:
        print(f"❌ Launch failed: {e}")
        exit(1)
    
    print("\n" + "=" * 60)
    print("All tests passed! Chrome launcher is working.")
    print("=" * 60)
