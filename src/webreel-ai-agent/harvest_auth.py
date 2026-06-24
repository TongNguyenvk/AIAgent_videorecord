"""
Auth State Harvester: Manual login -> JSON session export.

Run this script ONCE on your Windows machine (or any machine with a display).
It opens a Chromium browser, lets you log in by hand, then saves the session
(cookies + localStorage) to a JSON file that the Docker pipeline can reuse.

Usage:
    python harvest_auth.py                       # default: lms_auth.json
    python harvest_auth.py --url https://lms.tvu.edu.vn/ --output lms_auth.json
    python harvest_auth.py --url https://drive.google.com --output gdrive_auth.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path


async def harvest(url: str, output: str) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright is not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    async with async_playwright() as p:
        # Launch headed browser so you can interact with it
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        print(f"\n  Opening: {url}")
        print("  Please log in manually in the browser window.")
        print("  When you are fully logged in, come back here and press Enter.\n")

        await page.goto(url)

        # Wait for user to finish logging in
        try:
            input("  Press Enter after you have logged in... ")
        except (EOFError, KeyboardInterrupt):
            print("\n  Aborted.")
            await browser.close()
            return

        # Export storage state (cookies + localStorage + sessionStorage)
        state = await context.storage_state()

        output_path = Path(output)
        output_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

        cookie_count = len(state.get("cookies", []))
        origin_count = len(state.get("origins", []))
        print(f"\n  Saved {cookie_count} cookies and {origin_count} origin(s) to: {output_path.resolve()}")
        print("  Copy this file into your Docker project and set AUTH_STATE_PATH in .env.\n")

        await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Harvest browser auth state for Docker reuse.")
    parser.add_argument("--url", default="https://lms.tvu.edu.vn/", help="URL to open for login (default: LMS TVU)")
    parser.add_argument("--output", "-o", default="lms_auth.json", help="Output JSON file (default: lms_auth.json)")
    args = parser.parse_args()

    asyncio.run(harvest(args.url, args.output))


if __name__ == "__main__":
    main()
