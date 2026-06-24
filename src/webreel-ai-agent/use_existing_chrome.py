"""
Su dung Chrome profile THAT cua ban (da dang nhap san).
Khong copy, chi link truc tiep den profile that.

CANH BAO: Dong tat ca cua so Chrome truoc khi chay script nay!

Cach dung:
    1. Dong tat ca Chrome
    2. python use_existing_chrome.py
"""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright


def find_chrome_profile():
    """Tim Chrome profile mac dinh."""
    possible_paths = [
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")),
        Path(os.path.expandvars(r"%APPDATA%\Google\Chrome\User Data")),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None


def test_with_real_profile():
    print("\n=============================================")
    print("TEST VOI CHROME PROFILE THAT")
    print("=============================================\n")
    
    profile_path = find_chrome_profile()
    
    if not profile_path:
        print("Khong tim thay Chrome profile!")
        return False
    
    print(f"Chrome profile: {profile_path}")
    print("\nCANH BAO: Dong tat ca cua so Chrome truoc khi tiep tuc!")
    print("Nhan Enter de tiep tuc...")
    input()
    
    with sync_playwright() as p:
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-automation",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
        
        print("\nDang mo Chrome voi profile that cua ban...")
        
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_path),
                headless=False,
                args=args,
                channel="chrome",  # Su dung Chrome that, khong phai Chromium
            )
            
            page = context.pages[0] if context.pages else context.new_page()
            
            # Apply stealth
            try:
                from playwright_stealth import stealth_sync
                stealth_sync(page)
            except:
                pass
            
            print("Dang vao Google Drive...")
            page.goto("https://drive.google.com", wait_until="networkidle")
            
            time.sleep(3)
            
            current_url = page.url
            print(f"\nURL hien tai: {current_url}")
            
            if "accounts.google.com" in current_url:
                print("\n[THAT BAI] Van bi redirect den trang dang nhap")
                print("Google phat hien automation browser")
            elif "drive.google.com" in current_url:
                print("\n[THANH CONG] Da vao duoc Google Drive!")
                print("Session tu Chrome that hoat dong!")
            
            print("\nNhan Enter de dong...")
            input()
            
            context.close()
            
        except Exception as e:
            print(f"\nLoi: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


if __name__ == "__main__":
    import time
    test_with_real_profile()
