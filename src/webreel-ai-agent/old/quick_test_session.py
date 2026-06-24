"""
Quick test để verify Google session hoạt động.
Script này đơn giản mở browser với profile đã lưu và để bạn tự kiểm tra.

Cách dùng:
    python quick_test_session.py
"""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright


def quick_test():
    profile_dir = Path(__file__).parent / "output" / "browser_profile"
    
    print("\n" + "="*60)
    print("QUICK TEST GOOGLE SESSION")
    print("="*60)
    
    if not profile_dir.exists():
        print("\nCHUA CO PROFILE!")
        print(f"   Profile directory: {profile_dir}")
        print("\nChay setup truoc:")
        print("   python webreel-ai-agent/setup_auth.py")
        return
    
    print(f"\nProfile ton tai: {profile_dir}")
    print("\nDang mo Chrome voi profile da luu...")
    print("Kiem tra xem ban co da dang nhap Google khong")
    print("Dong cua so Chrome khi xong\n")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process"
            ]
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        # Apply stealth
        try:
            from playwright_stealth import stealth_sync
            stealth_sync(page)
            print("Da ap dung playwright-stealth")
        except ImportError:
            print("Chua cai playwright-stealth (khong bat buoc tren Windows)")
        
        # Vao Google Drive
        print("Dang vao Google Drive...")
        page.goto("https://drive.google.com", wait_until="networkidle")
        
        # Doi 2s de page load
        page.wait_for_timeout(2000)
        
        # Kiem tra xem co phai trang dang nhap khong
        current_url = page.url
        print(f"URL hien tai: {current_url}")
        
        if "accounts.google.com" in current_url:
            print("\nBI REDIRECT DEN TRANG DANG NHAP!")
            print("   Session khong hoat dong, can setup lai")
        elif "drive.google.com" in current_url:
            print("\nDA VAO DUOC GOOGLE DRIVE!")
            print("   Session hoat dong tot")
            
            # Thu lay ten file dau tien
            try:
                page.wait_for_timeout(3000)  # Doi Drive load
                print("\nDang tim files trong Drive...")
            except:
                pass
        
        print("\nHay tu kiem tra trinh duyet va dong cua so khi xong")
        
        try:
            page.wait_for_event("close", timeout=0)
        except:
            pass
        
        try:
            context.close()
        except:
            pass
    
    print("\nTest hoan tat!")


if __name__ == "__main__":
    quick_test()
