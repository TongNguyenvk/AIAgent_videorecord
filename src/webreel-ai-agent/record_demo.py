"""
Script to record demo video of the Streamlit app using Playwright.
This avoids the nested browser-use conflict issue.

Usage:
    python record_demo.py
"""
import asyncio
from playwright.async_api import async_playwright

async def record_demo():
    async with async_playwright() as p:
        # Launch browser with video recording
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir='output/demo-recording',
            record_video_size={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Navigate to Streamlit app
        await page.goto('http://localhost:8501')
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        
        # Show sidebar
        print("Showing sidebar...")
        await asyncio.sleep(1)
        
        # Fill in script
        print("Filling script...")
        script_box = page.locator('textarea').first
        await script_box.click()
        await script_box.fill("Vào wikipedia.org tìm kiếm Python programming language và đọc phần giới thiệu")
        await asyncio.sleep(1)
        
        # Fill video name
        print("Filling video name...")
        name_box = page.locator('input[type="text"]').filter(has_text='demo')
        await name_box.click()
        await name_box.fill("demo-wikipedia-search")
        await asyncio.sleep(1)
        
        # Click Generate button
        print("Clicking Generate button...")
        generate_btn = page.get_by_role('button', name='Tạo Video')
        await generate_btn.click()
        await asyncio.sleep(2)
        
        # Wait for completion (check for success message)
        print("Waiting for completion...")
        try:
            await page.wait_for_selector('text=Video tạo thành công', timeout=300000)  # 5 min
            print("Video generation completed!")
        except:
            print("Timeout waiting for completion")
        
        await asyncio.sleep(2)
        
        # Switch to Results tab
        print("Switching to Results tab...")
        results_tab = page.get_by_role('tab', name='Kết quả')
        await results_tab.click()
        await asyncio.sleep(3)
        
        # Close
        await context.close()
        await browser.close()
        
        print("Demo recording saved to output/demo-recording/")

if __name__ == '__main__':
    asyncio.run(record_demo())
