"""
Start Chrome with remote debugging port
Python version - more reliable than batch file
"""

import subprocess
import sys
import time
import os
import requests

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEBUG_PORT = 9222
USER_DATA_DIR = os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data")

def kill_existing_chrome():
    """Kill all existing Chrome processes"""
    print("Closing existing Chrome instances...")
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], 
                      capture_output=True, 
                      timeout=5)
        time.sleep(2)
    except:
        pass

def start_chrome_debug():
    """Start Chrome with remote debugging"""
    print(f"Starting Chrome with debug port {DEBUG_PORT}...")
    
    cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--profile-directory=Default"
    ]
    
    # Start Chrome in background
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    
    return process

def wait_for_chrome(timeout=10):
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
    print("Starting Chrome with Remote Debugging")
    print("=" * 60)
    print()
    
    # Kill existing Chrome
    kill_existing_chrome()
    
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
        print("Chrome is running. You can now run your automation script.")
        print("Press Ctrl+C to stop.")
        print()
        
        # Keep script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping Chrome...")
            kill_existing_chrome()
            print("Done!")
    else:
        print()
        print("ERROR: Chrome failed to start or debug port not accessible")
        print("Please check:")
        print(f"1. Chrome path: {CHROME_PATH}")
        print(f"2. Port {DEBUG_PORT} is not in use")
        print(f"3. User data dir: {USER_DATA_DIR}")
        sys.exit(1)

if __name__ == "__main__":
    main()
