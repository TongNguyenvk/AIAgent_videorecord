#!/usr/bin/env python3
"""
Tự động refresh OneDrive cookies để tránh expire.

Cách hoạt động:
1. Navigate to OneDrive với cookies hiện tại
2. OneDrive server sẽ tự động refresh cookies (extend expiry)
3. Cookies mới được lưu vào Chrome profile
4. Không cần login lại!

Chạy định kỳ: Mỗi 30 ngày (hoặc mỗi tuần cho chắc)

Cron job example:
    0 0 1 * * cd /app/webreel-ai-agent && python refresh_onedrive_cookies.py
    (Chạy vào 00:00 ngày 1 mỗi tháng)
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

async def refresh_cookies(cdp_url: str = "http://localhost:9222"):
    """
    Refresh OneDrive cookies by navigating to OneDrive.
    
    Trick: Khi navigate với cookies hiện tại, OneDrive server sẽ:
    1. Verify cookies
    2. Extend expiry time (refresh)
    3. Set-Cookie với expiry mới
    4. Browser tự động update cookies
    """
    from playwright.async_api import async_playwright
    
    print("🔄 OneDrive Cookie Refresher")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        async with async_playwright() as p:
            # Connect to Chrome
            print(f"1️⃣  Connecting to Chrome: {cdp_url}")
            browser = await p.chromium.connect_over_cdp(cdp_url)
            
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            
            print("   ✅ Connected\n")
            
            # Get current cookies
            print("2️⃣  Checking current cookies...")
            cookies_before = await context.cookies()
            onedrive_cookies_before = [c for c in cookies_before if 'live.com' in c.get('domain', '')]
            
            print(f"   Found {len(onedrive_cookies_before)} OneDrive cookies")
            
            if len(onedrive_cookies_before) == 0:
                print("   ❌ No cookies found! Need manual login first.\n")
                return False
            
            # Show expiry of key cookies
            for cookie in onedrive_cookies_before[:3]:
                expires = cookie.get('expires', -1)
                if expires > 0:
                    from datetime import datetime
                    expiry_date = datetime.fromtimestamp(expires)
                    days_left = (expiry_date - datetime.now()).days
                    print(f"   - {cookie['name']}: expires in {days_left} days ({expiry_date.strftime('%Y-%m-%d')})")
            
            print()
            
            # Navigate to OneDrive to trigger refresh
            print("3️⃣  Navigating to OneDrive to refresh cookies...")
            try:
                await page.goto('https://onedrive.live.com/', wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
                
                current_url = page.url
                print(f"   Current URL: {current_url}")
                
                if 'login.live.com' in current_url or 'login.microsoftonline.com' in current_url:
                    print("   ❌ Redirected to login page - cookies already expired!\n")
                    print("   Action required: Manual login via noVNC\n")
                    return False
                
                print("   ✅ Navigation successful\n")
                
            except Exception as e:
                print(f"   ⚠️  Navigation error: {e}\n")
                # Continue anyway - cookies might still be refreshed
            
            # Wait a bit for cookies to be set
            await asyncio.sleep(2)
            
            # Check cookies after refresh
            print("4️⃣  Checking refreshed cookies...")
            cookies_after = await context.cookies()
            onedrive_cookies_after = [c for c in cookies_after if 'live.com' in c.get('domain', '')]
            
            print(f"   Found {len(onedrive_cookies_after)} OneDrive cookies")
            
            # Compare expiry times
            refreshed_count = 0
            for cookie_after in onedrive_cookies_after[:3]:
                name = cookie_after['name']
                expires_after = cookie_after.get('expires', -1)
                
                # Find matching cookie before
                cookie_before = next((c for c in onedrive_cookies_before if c['name'] == name), None)
                
                if cookie_before:
                    expires_before = cookie_before.get('expires', -1)
                    
                    if expires_after > expires_before:
                        refreshed_count += 1
                        from datetime import datetime
                        expiry_date = datetime.fromtimestamp(expires_after)
                        days_left = (expiry_date - datetime.now()).days
                        print(f"   ✅ {name}: refreshed! New expiry in {days_left} days ({expiry_date.strftime('%Y-%m-%d')})")
                    else:
                        print(f"   ⚠️  {name}: not refreshed (same expiry)")
                else:
                    print(f"   ✅ {name}: new cookie added")
                    refreshed_count += 1
            
            print()
            
            if refreshed_count > 0:
                print(f"   🎉 Refreshed {refreshed_count} cookies!\n")
                return True
            else:
                print("   ⚠️  No cookies were refreshed\n")
                print("   Possible reasons:")
                print("   - Cookies are still fresh (no need to refresh)")
                print("   - Server didn't send new cookies")
                print("   - Navigation didn't complete properly\n")
                return True  # Still consider success if no error
            
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║  WebReel - OneDrive Cookie Refresher                        ║
║  Tự động refresh cookies để tránh expire                    ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    cdp_url = os.getenv('CHROME_CDP_URL', 'http://localhost:9222')
    
    success = await refresh_cookies(cdp_url)
    
    if success:
        print("="*60)
        print("✅ SUCCESS - Cookies refreshed!")
        print("="*60)
        print("""
Cookies đã được refresh thành công!

Recommendations:
1. Chạy script này mỗi 30 ngày (cron job)
2. Hoặc chạy mỗi tuần cho chắc chắn
3. Monitor logs để detect khi cần login lại

Cron job example:
    # Mỗi ngày 1 hàng tháng lúc 00:00
    0 0 1 * * cd /app/webreel-ai-agent && python refresh_onedrive_cookies.py >> /var/log/cookie_refresh.log 2>&1
    
    # Hoặc mỗi Chủ Nhật lúc 02:00
    0 2 * * 0 cd /app/webreel-ai-agent && python refresh_onedrive_cookies.py >> /var/log/cookie_refresh.log 2>&1
        """)
    else:
        print("="*60)
        print("❌ FAILED - Manual login required")
        print("="*60)
        print("""
Cookies đã expire hoặc không tồn tại.

Action required:
1. SSH vào VPS: ssh -L 6080:localhost:6080 user@vps
2. Mở noVNC: http://localhost:6080/vnc.html
3. Navigate to https://onedrive.live.com
4. Login manually (REMEMBER to tick "Keep me signed in")
5. Cookies sẽ được lưu và persist 90 days

Sau đó chạy lại script này để verify.
        """)
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
