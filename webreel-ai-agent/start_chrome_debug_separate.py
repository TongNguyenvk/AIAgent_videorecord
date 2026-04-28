"""
Start Chrome with remote debugging using SEPARATE profile
Tránh conflict với Chrome đang chạy
"""

import subprocess
import sys
import time
import os
import requests
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEBUG_PORT = 9222

# Sử dụng profile riêng để tránh conflict với Chrome đang chạy
TEMP_PROFILE_DIR = Path(__file__).parent / "chrome_debug_profile"

def start_chrome_debug():
    """Start Chrome with remote debugging using separate profile"""
    print(f"Starting Chrome with debug port {DEBUG_PORT}...")
    print(f"Using profile: {TEMP_PROFILE_DIR}")
    
    # Tạo thư mục profile nếu chưa có
    TEMP_PROFILE_DIR.mkdir(exist_ok=True)
    
    cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={TEMP_PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    
    # Start Chrome in background
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    
    return process

def wait_for_chrome(timeout=15):
    """Wait for Chrome to be ready"""
    print("Waiting for Chrome to start...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://localhost:{DEBUG_PORT}/json/version", timeout=1)
            if response.status_code == 200:
                chrome_info = response.json()
                print(f"Chrome ready: {chrome_info.get('Browser', 'Unknown')}")
                return True
        except:
            pass
        time.sleep(0.5)
    
    return False

def main():
    print("=" * 60)
    print("Starting Chrome with Remote Debugging (Separate Profile)")
    print("=" * 60)
    print()
    print("NOTE: This Chrome instance uses a separate profile.")
    print("You will need to login to Google/Facebook/etc. again.")
    print()
    
    # Start Chrome
    process = start_chrome_debug()
    
    # Wait for Chrome to be ready
    if wait_for_chrome():
        print()
        print("=" * 60)
        print("Chrome started successfully!")
        print("=" * 60)
        print()
        print(f"Debug port: {DEBUG_PORT}")
        print(f"Test connection: http://localhost:{DEBUG_PORT}/json")
        print()
        print("IMPORTANT: Please login to services you need:")
        print("  1. Google Drive: https://drive.google.com")
        print("  2. Gmail: https://mail.google.com")
        print("  3. Facebook: https://facebook.com")
        print()
        print("After logging in, you can run your automation script.")
        print("Press Ctrl+C to stop Chrome.")
        print()
        
        # Keep script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping Chrome...")
            process.terminate()
            time.sleep(2)
            print("Done!")
    else:
        print()
        print("ERROR: Chrome failed to start or debug port not accessible")
        print()
        print("Possible issues:")
        print(f"1. Chrome path incorrect: {CHROME_PATH}")
        print(f"2. Port {DEBUG_PORT} already in use")
        print("3. Another Chrome with debug port is running")
        print()
        print("Try:")
        print("1. Close ALL Chrome windows")
        print("2. Run this script again")
        print()
        sys.exit(1)

if __name__ == "__main__":
    main()
