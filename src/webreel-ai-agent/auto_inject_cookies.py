#!/usr/bin/env python3
"""
Tự động inject OneDrive cookies vào browser từ MSAL token.

Cách hoạt động (TRICK):
1. Lấy MSAL token từ token_cache.bin
2. Dùng token để gọi Graph API endpoint đặc biệt
3. Graph API trả về cookies hoặc session info
4. Inject cookies vào Chrome profile
5. Browser tự động authenticated!

Lưu ý: Đây là workaround, Microsoft không official support cách này.
"""

import asyncio
import os
import sys
from pathlib import Path
import json

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

from shared.graph_api import get_access_token
import requests

async def inject_cookies_via_playwright(cdp_url: str = "http://localhost:9222"):
    """
    Method 1: Dùng Playwright để inject cookies trực tiếp.
    
    Trick: Tạo cookies giả từ MSAL token info.
    """
    from playwright.async_api import async_playwright
    
    print("🔐 Auto Cookie Injector - Method 1 (Playwright)\n")
    
    # Get MSAL token
    print("1️⃣  Getting MSAL token...")
    token = get_access_token()
    print(f"   ✅ Token: {token[:20]}...{token[-10:]}\n")
    
    # Connect to Chrome
    print(f"2️⃣  Connecting to Chrome: {cdp_url}")
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        
        print("   ✅ Connected\n")
        
        # Method 1A: Navigate với token trong header (không work vì browser không support)
        # Method 1B: Navigate với token trong URL fragment (có thể work)
        # Method 1C: Inject cookies manually (best approach)
        
        print("3️⃣  Method: Manual cookie injection")
        print("   Analyzing MSAL token to extract user info...\n")
        
        # Get user info from Graph API
        headers = {'Authorization': f'Bearer {token}'}
        
        # Try to get user email/ID
        try:
            r = requests.get('https://graph.microsoft.com/v1.0/me/drive', headers=headers)
            if r.status_code == 200:
                drive_info = r.json()
                owner = drive_info.get('owner', {}).get('user', {})
                user_email = owner.get('email', 'unknown')
                user_id = owner.get('id', 'unknown')
                print(f"   User: {user_email}")
                print(f"   ID: {user_id}\n")
            else:
                print("   ⚠️  Cannot get user info from Graph API\n")
                user_email = "unknown"
                user_id = "unknown"
        except Exception as e:
            print(f"   ⚠️  Error getting user info: {e}\n")
            user_email = "unknown"
            user_id = "unknown"
        
        # Inject essential cookies for OneDrive
        # These are the minimum cookies needed for authentication
        print("4️⃣  Injecting cookies...")
        
        cookies_to_inject = [
            {
                "name": "MSAL_TOKEN",
                "value": token[:50],  # Truncated for security
                "domain": ".live.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "None"
            },
            {
                "name": "wla42",  # OneDrive auth cookie
                "value": f"user={user_email}",
                "domain": ".onedrive.live.com",
                "path": "/",
                "httpOnly": False,
                "secure": True,
                "sameSite": "Lax"
            }
        ]
        
        try:
            await context.add_cookies(cookies_to_inject)
            print(f"   ✅ Injected {len(cookies_to_inject)} cookies\n")
        except Exception as e:
            print(f"   ❌ Failed to inject cookies: {e}\n")
            return False
        
        # Verify by navigating to OneDrive
        print("5️⃣  Verifying authentication...")
        try:
            await page.goto('https://onedrive.live.com/', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            current_url = page.url
            print(f"   Current URL: {current_url}")
            
            if 'login.live.com' in current_url:
                print("   ❌ Still redirected to login - cookies not working\n")
                return False
            else:
                print("   ✅ Authentication successful!\n")
                return True
                
        except Exception as e:
            print(f"   ⚠️  Navigation error: {e}\n")
            return False

async def inject_cookies_via_oauth_trick(cdp_url: str = "http://localhost:9222"):
    """
    Method 2: OAuth Implicit Flow Trick
    
    Dùng MSAL token để trigger OAuth flow, Microsoft sẽ tự set cookies.
    """
    from playwright.async_api import async_playwright
    
    print("🔐 Auto Cookie Injector - Method 2 (OAuth Trick)\n")
    
    # Get MSAL token
    print("1️⃣  Getting MSAL token...")
    token = get_access_token()
    print(f"   ✅ Token: {token[:20]}...{token[-10:]}\n")
    
    # Get client ID
    client_id = os.getenv('MS_CLIENT_ID', '')
    if not client_id:
        print("   ❌ MS_CLIENT_ID not found in .env\n")
        return False
    
    # Connect to Chrome
    print(f"2️⃣  Connecting to Chrome: {cdp_url}")
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()
        
        print("   ✅ Connected\n")
        
        # Build special URL that includes token hint
        # This tricks Microsoft into setting cookies
        print("3️⃣  Building OAuth URL with token hint...")
        
        # Method 2A: Use login_hint with token
        oauth_url = (
            f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize"
            f"?client_id={client_id}"
            f"&response_type=token"
            f"&redirect_uri=https://onedrive.live.com"
            f"&scope=Files.ReadWrite.All offline_access"
            f"&prompt=none"  # Don't show login UI
            f"&state=auto_inject"
        )
        
        print(f"   URL: {oauth_url[:80]}...\n")
        
        print("4️⃣  Navigating to OAuth URL...")
        try:
            # Set extra headers with token
            await context.set_extra_http_headers({
                'Authorization': f'Bearer {token}'
            })
            
            await page.goto(oauth_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)
            
            current_url = page.url
            print(f"   Current URL: {current_url}\n")
            
            # Check if redirected to OneDrive (success) or login page (fail)
            if 'onedrive.live.com' in current_url:
                print("   ✅ OAuth flow successful! Cookies set.\n")
                
                # Verify cookies
                cookies = await context.cookies()
                onedrive_cookies = [c for c in cookies if 'live.com' in c.get('domain', '')]
                print(f"   Found {len(onedrive_cookies)} OneDrive cookies\n")
                
                return True
            elif 'login.live.com' in current_url or 'login.microsoftonline.com' in current_url:
                print("   ⚠️  Still on login page - OAuth trick didn't work\n")
                print("   Reason: prompt=none requires existing session\n")
                return False
            else:
                print(f"   ⚠️  Unexpected URL: {current_url}\n")
                return False
                
        except Exception as e:
            print(f"   ❌ Navigation error: {e}\n")
            return False

async def inject_cookies_via_graph_session(cdp_url: str = "http://localhost:9222"):
    """
    Method 3: Graph API Session Endpoint (nếu có)
    
    Một số Microsoft API có endpoint để convert token → cookies.
    """
    from playwright.async_api import async_playwright
    
    print("🔐 Auto Cookie Injector - Method 3 (Graph Session)\n")
    
    # Get MSAL token
    print("1️⃣  Getting MSAL token...")
    token = get_access_token()
    print(f"   ✅ Token: {token[:20]}...{token[-10:]}\n")
    
    # Try to find session endpoint
    print("2️⃣  Looking for Graph API session endpoint...")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Try different endpoints that might return session info
    endpoints = [
        'https://graph.microsoft.com/v1.0/me',
        'https://graph.microsoft.com/v1.0/me/drive',
        'https://api.onedrive.com/v1.0/drive',  # Legacy endpoint
    ]
    
    for endpoint in endpoints:
        try:
            r = requests.get(endpoint, headers=headers, allow_redirects=True)
            
            # Check if response sets cookies
            if 'Set-Cookie' in r.headers:
                print(f"   ✅ Found cookies in response from: {endpoint}")
                print(f"      Cookies: {r.headers['Set-Cookie'][:100]}...\n")
                
                # Extract cookies
                # TODO: Parse Set-Cookie header and inject into browser
                return True
            else:
                print(f"   ⚠️  No cookies from: {endpoint}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n   ❌ No session endpoint found\n")
    return False

async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║  WebReel - Auto Cookie Injector                             ║
║  Tự động inject OneDrive cookies từ MSAL token              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    cdp_url = os.getenv('CHROME_CDP_URL', 'http://localhost:9222')
    
    # Try Method 2 first (OAuth trick - most likely to work)
    print("Trying Method 2: OAuth Implicit Flow Trick\n")
    success = await inject_cookies_via_oauth_trick(cdp_url)
    
    if success:
        print("\n" + "="*60)
        print("🎉 SUCCESS!")
        print("="*60)
        print("""
Cookies đã được inject thành công!

Next steps:
1. Navigate to any OneDrive link
2. Browser sẽ tự động authenticated
3. Không cần login manual nữa!

Note: Cookies sẽ persist trong Chrome profile.
        """)
        return True
    
    # Fallback to Method 1
    print("\nMethod 2 failed. Trying Method 1: Manual Cookie Injection\n")
    success = await inject_cookies_via_playwright(cdp_url)
    
    if success:
        print("\n" + "="*60)
        print("🎉 SUCCESS (Method 1)!")
        print("="*60)
        return True
    
    # All methods failed
    print("\n" + "="*60)
    print("❌ ALL METHODS FAILED")
    print("="*60)
    print("""
Không thể tự động inject cookies.

Lý do:
- Microsoft không cho phép convert API token → Browser cookies
- OAuth flow yêu cầu existing session (prompt=none)
- Graph API không expose session endpoint

Giải pháp:
1. Login manual một lần qua noVNC/CDP
2. Cookies sẽ được lưu trong Chrome profile
3. Lần sau tự động dùng cookies (không cần login lại)

Đây là one-time setup, không thể tránh được.
    """)
    
    return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
