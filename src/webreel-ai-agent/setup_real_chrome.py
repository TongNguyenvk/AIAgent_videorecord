"""
Setup session bang cach su dung Chrome THAT (khong phai Playwright).
Sau do copy profile sang cho Playwright dung.

Cach dung:
    python setup_real_chrome.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_chrome_path():
    """Tim Chrome executable tren Windows."""
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def setup_with_real_chrome():
    print("\n=============================================")
    print("SETUP SESSION VOI CHROME THAT")
    print("=============================================\n")
    
    chrome_path = find_chrome_path()
    
    if not chrome_path:
        print("Khong tim thay Chrome!")
        print("Hay cai dat Chrome tu: https://www.google.com/chrome/")
        return False
    
    print(f"Tim thay Chrome: {chrome_path}\n")
    
    # Tao profile directory
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Su dung profile rieng cho webreel
    profile_dir = output_dir / "browser_profile"
    profile_dir.mkdir(exist_ok=True)
    
    print("BUOC 1: Dang nhap voi Chrome that")
    print("---------------------------------------")
    print("1. Chrome se mo ra voi profile rieng")
    print("2. Dang nhap vao Google Drive")
    print("3. Dam bao da vao duoc trang Drive chinh")
    print("4. DONG Chrome khi xong\n")
    
    # Mo Chrome voi profile rieng
    cmd = [
        chrome_path,
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://drive.google.com"
    ]
    
    print(f"Dang mo Chrome...\n")
    
    try:
        # Mo Chrome va doi no dong
        process = subprocess.Popen(cmd)
        process.wait()
        
        print("\n---------------------------------------")
        print("BUOC 2: Kiem tra profile")
        print("---------------------------------------")
        
        # Kiem tra xem co cookies khong
        cookies_db = profile_dir / "Default" / "Cookies"
        if cookies_db.exists():
            print(f"Tim thay Cookies database: {cookies_db}")
            print(f"Kich thuoc: {cookies_db.stat().st_size} bytes")
        else:
            print("CANH BAO: Khong tim thay Cookies database!")
            print("Co the ban chua dang nhap hoac dong Chrome qua nhanh")
            return False
        
        print("\n---------------------------------------")
        print("HOAN THANH!")
        print("---------------------------------------")
        print(f"Profile da luu tai: {profile_dir}")
        print("\nBay gio chay test:")
        print("  python quick_test_session.py")
        print("hoac:")
        print("  python test_google_session.py")
        
        return True
        
    except Exception as e:
        print(f"\nLoi: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://drive.google.com"
    success = setup_with_real_chrome()
    sys.exit(0 if success else 1)
