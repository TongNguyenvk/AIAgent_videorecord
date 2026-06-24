"""
Advanced setup auth voi cac tricks manh hon de vuot Google bot detection.

Cach dung:
    python setup_auth_advanced.py https://drive.google.com
"""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright


def setup_auth_advanced(domain="https://google.com"):
    print("\n=============================================")
    print("TRINH DUYET DANG NHAP (ADVANCED)")
    print("=============================================")
    print("1. Chrome se mo ra voi cac thiet lap chong bot detection")
    print("2. Hay dang nhap vao Google binh thuong")
    print("3. SAU KHI DANG NHAP XONG, DONG cua so Chrome")
    print("4. Profile se tu dong luu\n")
    
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    profile_dir = output_dir / "browser_profile"

    with sync_playwright() as p:
        # Cac args de giam bot detection
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--disable-features=BlockInsecurePrivateNetworkRequests",
            # Tat automation flags
            "--disable-automation",
            "--disable-infobars",
            # User agent
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ]
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            args=args,
            viewport={"width": 1920, "height": 1080},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            permissions=["geolocation", "notifications"],
            color_scheme="light",
            accept_downloads=True,
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        # Apply stealth
        try:
            from playwright_stealth import stealth_sync
            stealth_sync(page)
            print("Da ap dung playwright-stealth\n")
        except ImportError:
            print("Khong co playwright-stealth (pip install playwright-stealth)\n")
        
        # Override navigator.webdriver
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override chrome property
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['vi-VN', 'vi', 'en-US', 'en']
            });
        """)
        
        print(f"Dang vao: {domain}")
        page.goto(domain, wait_until="networkidle")
        
        print("\nHay dang nhap va DONG cua so khi xong...")
        
        try:
            page.wait_for_event("close", timeout=0)
        except:
            pass
            
        print(f"\nDa luu profile tai: {profile_dir}")
        
        try:
            context.close()
        except:
            pass


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://google.com"
    setup_auth_advanced(url)
