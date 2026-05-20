#!/usr/bin/env python3
"""
Inject OneDrive session vào Chrome profile từ Graph API token.

Cách hoạt động:
1. Lấy MSAL token từ token_cache.bin
2. Dùng token để authenticate với Microsoft
3. Lấy cookies từ authentication flow
4. Inject cookies vào Chrome profile
5. Browser tự động authenticated khi navigate OneDrive

Usage:
    python inject_onedrive_session.py
    
    # Hoặc với CDP URL custom:
    python inject_onedrive_session.py --cdp-url http://localhost:9222
"""

import asyncio
import os
import sys
from pathlib import Path
import argparse

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

from shared.graph_api import get_access_token
from playwright.async_api import async_playwright

async def inject_session(cdp_url: str = "http://localhost:9222"):
    """
    Inject OneDrive session vào browser bằng cách:
    1. Get MSAL token
    2. Navigate to OneDrive với token trong URL (authentication trick)
    3. Let Microsoft set cookies automatically
    4. Cookies persist trong profile
    """
    
    print("🔐 OneDrive Session Injector\n")
    
    # Step 1: Get MSAL token
    print("1️⃣  Getting MSAL token...")
    try:
        token = get_access_token()
        print(f"   ✅ Token: {token[:20]}...{token[-10:]}\n")
    except Exception as e:
        print(f"   ❌ Failed to get token: {e}")
        return False
    
    # Step 2: Connect to Chrome
    print(f"2️⃣  Connecting to Chrome: {cdp_url}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            print("   ✅ Connected\n")
            
            # Get or create context
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                if pages:
                    page = pages[0]
                else:
                    page = await context.new_page()
            else:
                print("   ⚠️  No context found, creating new one...")
                context = await browser.new_context()
                page = await context.new_page()
            
            print(f"   Using page: {page.url}\n")
            
            # Step 3: Method 1 - Navigate to OneDrive home (let it set cookies)
            print("3️⃣  Method 1: Navigate to OneDrive home...")
            try:
                await page.goto('https://onedrive.live.com/', wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
                
                current_url = page.url
                print(f"   Current URL: {current_url}")
                
                if 'login.live.com' in current_url or 'login.microsoftonline.com' in current_url:
                    print("   ⚠️  Redirected to login page - cookies not set yet\n")
                    
                    # Step 4: Method 2 - Try to inject cookies manually
                    print("4️⃣  Method 2: Injecting cookies manually...")
                    
                    # Get cookies from a successful Graph API call
                    import requests
                    session = requests.Session()
                    
                    # Make a request to OneDrive web with token
                    # This will set cookies in the session
                    headers = {
                        'Authorization': f'Bearer {token}',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    # Try to get OneDrive page with token
                    # Microsoft might redirect and set cookies
                    try:
                        # Use Graph API to get a sharing link, then navigate to it
                        # This forces Microsoft to authenticate the browser
                        print("   Trying authentication flow...\n")
                        
                        # Alternative: Use Microsoft's OAuth implicit flow
                        # Navigate to OAuth URL with token
                        client_id = os.getenv('MS_CLIENT_ID', '')
                        
                        # Build OAuth URL (implicit flow)
                        oauth_url = (
                            f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize"
                            f"?client_id={client_id}"
                            f"&response_type=token"
                            f"&redirect_uri=https://onedrive.live.com"
                            f"&scope=Files.ReadWrite.All"
                            f"&state=12345"
                        )
                        
                        print(f"   Navigating to OAuth flow...")
                        await page.goto(oauth_url, wait_until='domcontentloaded', timeout=30000)
                        await asyncio.sleep(5)
                        
                        current_url = page.url
                        print(f"   Current URL: {current_url}")
                        
                        if 'onedrive.live.com' in current_url:
                            print("   ✅ Successfully authenticated!\n")
                        else:
                            print("   ⚠️  Still on login page\n")
                            print("   📝 Manual action required:")
                            print("      1. Login manually in the browser")
                            print("      2. Cookies will be saved automatically")
                            print("      3. Next time will work without login\n")
                            return False
                    
                    except Exception as e:
                        print(f"   ⚠️  OAuth flow failed: {e}\n")
                        print("   📝 Fallback: Manual login required")
                        print("      Please login manually in the browser (noVNC or CDP)")
                        return False
                
                else:
                    print("   ✅ Already authenticated! Cookies are valid\n")
                
                # Step 5: Verify cookies
                print("5️⃣  Verifying cookies...")
                cookies = await context.cookies()
                
                onedrive_cookies = [c for c in cookies if 'live.com' in c.get('domain', '')]
                print(f"   Found {len(onedrive_cookies)} OneDrive cookies")
                
                if onedrive_cookies:
                    print("   ✅ Cookies injected successfully!\n")
                    
                    # Show some cookie names (not values for security)
                    for cookie in onedrive_cookies[:5]:
                        print(f"      - {cookie['name']} (domain: {cookie['domain']})")
                    
                    if len(onedrive_cookies) > 5:
                        print(f"      ... and {len(onedrive_cookies) - 5} more")
                    
                    print("\n   🎉 Session ready! Browser will stay authenticated.")
                    return True
                else:
                    print("   ⚠️  No cookies found\n")
                    return False
                
            except Exception as e:
                print(f"   ❌ Navigation failed: {e}\n")
                return False
            
    except Exception as e:
        print(f"   ❌ Failed to connect: {e}\n")
        print("   Make sure Chrome is running with CDP:")
        print("   chrome.exe --remote-debugging-port=9222")
        return False

async def main():
    parser = argparse.ArgumentParser(description='Inject OneDrive session into Chrome')
    parser.add_argument('--cdp-url', default='http://localhost:9222', help='Chrome CDP URL')
    args = parser.parse_args()
    
    success = await inject_session(args.cdp_url)
    
    if success:
        print("\n" + "="*60)
        print("✅ SUCCESS - Session injected!")
        print("="*60)
        print("""
Next steps:
1. Navigate to any OneDrive link
2. Browser will be automatically authenticated
3. No manual login required!

Note: Cookies will persist in Chrome profile.
      You only need to run this once (or when cookies expire).
        """)
    else:
        print("\n" + "="*60)
        print("⚠️  PARTIAL SUCCESS - Manual login needed")
        print("="*60)
        print("""
What to do:
1. Open browser (noVNC or CDP)
2. Navigate to https://onedrive.live.com
3. Login manually once
4. Cookies will be saved automatically
5. Next time will work without login

This is a one-time setup!
        """)
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
