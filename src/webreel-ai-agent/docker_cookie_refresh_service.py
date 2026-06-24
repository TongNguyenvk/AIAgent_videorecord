#!/usr/bin/env python3
"""
Docker service để tự động refresh cookies trong background.

Chạy như một daemon trong Docker container:
- Check cookies mỗi ngày
- Tự động refresh nếu sắp expire (< 7 days)
- Log kết quả
- Alert nếu cookies expired (cần manual login)

Usage:
    # Standalone
    python docker_cookie_refresh_service.py
    
    # Docker
    CMD ["python", "docker_cookie_refresh_service.py"]
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import time

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [cookie-refresh] %(levelname)s - %(message)s"
)
logger = logging.getLogger("cookie_refresh_service")

# Configuration
CHECK_INTERVAL_HOURS = int(os.getenv("COOKIE_CHECK_INTERVAL_HOURS", "24"))  # Check daily
REFRESH_THRESHOLD_DAYS = int(os.getenv("COOKIE_REFRESH_THRESHOLD_DAYS", "7"))  # Refresh if < 7 days left
CDP_URL = os.getenv("CHROME_CDP_URL", "http://localhost:9222")

async def check_and_refresh_cookies():
    """
    Check cookies expiry and refresh if needed.
    
    Returns:
        - "ok": Cookies are fresh, no action needed
        - "refreshed": Cookies were refreshed successfully
        - "expired": Cookies expired, manual login required
        - "error": Error occurred
    """
    from playwright.async_api import async_playwright
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            
            # Get current cookies
            cookies = await context.cookies()
            onedrive_cookies = [c for c in cookies if 'live.com' in c.get('domain', '')]
            
            if len(onedrive_cookies) == 0:
                logger.warning("No OneDrive cookies found - manual login required")
                return "expired"
            
            # Check expiry of key cookies
            min_days_left = 999
            for cookie in onedrive_cookies:
                expires = cookie.get('expires', -1)
                if expires > 0:
                    expiry_date = datetime.fromtimestamp(expires)
                    days_left = (expiry_date - datetime.now()).days
                    
                    if days_left < min_days_left:
                        min_days_left = days_left
            
            logger.info(f"Cookies status: {min_days_left} days until expiry")
            
            # If cookies are fresh, no action needed
            if min_days_left > REFRESH_THRESHOLD_DAYS:
                logger.info(f"Cookies are fresh ({min_days_left} days left), no refresh needed")
                return "ok"
            
            # If cookies already expired
            if min_days_left < 0:
                logger.error("Cookies already expired - manual login required!")
                return "expired"
            
            # Refresh cookies
            logger.info(f"Cookies expiring soon ({min_days_left} days), refreshing...")
            
            await page.goto('https://onedrive.live.com/', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            current_url = page.url
            
            if 'login.live.com' in current_url or 'login.microsoftonline.com' in current_url:
                logger.error("Redirected to login page - cookies expired!")
                return "expired"
            
            logger.info("Cookies refreshed successfully")
            return "refreshed"
            
    except Exception as e:
        logger.error(f"Error checking/refreshing cookies: {e}")
        return "error"

async def run_service():
    """Main service loop"""
    logger.info("="*60)
    logger.info("OneDrive Cookie Refresh Service Started")
    logger.info("="*60)
    logger.info(f"Check interval: {CHECK_INTERVAL_HOURS} hours")
    logger.info(f"Refresh threshold: {REFRESH_THRESHOLD_DAYS} days")
    logger.info(f"CDP URL: {CDP_URL}")
    logger.info("="*60)
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while True:
        try:
            logger.info("Running cookie check...")
            
            result = await check_and_refresh_cookies()
            
            if result == "ok":
                consecutive_errors = 0
                logger.info("✅ Status: OK")
                
            elif result == "refreshed":
                consecutive_errors = 0
                logger.info("✅ Status: Refreshed")
                
            elif result == "expired":
                consecutive_errors = 0
                logger.error("❌ Status: EXPIRED - Manual login required!")
                logger.error("Action: SSH to VPS and login via noVNC")
                logger.error("Command: ssh -L 6080:localhost:6080 user@vps")
                logger.error("URL: http://localhost:6080/vnc.html")
                
            elif result == "error":
                consecutive_errors += 1
                logger.error(f"❌ Status: ERROR (consecutive: {consecutive_errors}/{max_consecutive_errors})")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical("Too many consecutive errors! Service may be broken.")
                    logger.critical("Check Chrome CDP connection and logs.")
            
            # Wait before next check
            next_check = datetime.now() + timedelta(hours=CHECK_INTERVAL_HOURS)
            logger.info(f"Next check: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("-"*60)
            
            await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
            
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
            break
            
        except Exception as e:
            logger.error(f"Unexpected error in service loop: {e}")
            consecutive_errors += 1
            
            if consecutive_errors >= max_consecutive_errors:
                logger.critical("Service crashed! Exiting...")
                sys.exit(1)
            
            # Wait a bit before retry
            await asyncio.sleep(60)

def main():
    try:
        asyncio.run(run_service())
    except KeyboardInterrupt:
        logger.info("Service stopped")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Service crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
