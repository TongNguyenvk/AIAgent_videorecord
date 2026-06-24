"""
Chrome CDP Wrapper - Kết nối browser-use vào Chrome đang chạy
Thay vì launch Chrome mới, kết nối vào Chrome instance của user
"""

import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import logging

logger = logging.getLogger(__name__)


class ChromeCDPWrapper:
    """Wrapper để kết nối browser-use vào Chrome đang chạy qua CDP"""
    
    def __init__(self, cdp_url: str = "http://localhost:9222"):
        """
        Args:
            cdp_url: URL của Chrome DevTools Protocol endpoint
        """
        self.cdp_url = cdp_url
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def connect(self) -> tuple[Browser, BrowserContext, Page]:
        """
        Kết nối vào Chrome đang chạy
        
        Returns:
            Tuple of (browser, context, page)
        """
        logger.info(f"Connecting to Chrome via CDP: {self.cdp_url}")
        
        self.playwright = await async_playwright().start()
        
        try:
            # Kết nối vào Chrome
            self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
            logger.info("✓ Connected to Chrome successfully")
            
            # Lấy hoặc tạo context
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                logger.info(f"Using existing context with {len(self.context.pages)} pages")
            else:
                self.context = await self.browser.new_context()
                logger.info("Created new context")
            
            # Lấy hoặc tạo page
            pages = self.context.pages
            if pages:
                self.page = pages[0]
                logger.info(f"Using existing page: {self.page.url}")
            else:
                self.page = await self.context.new_page()
                logger.info("Created new page")
            
            return self.browser, self.context, self.page
            
        except Exception as e:
            logger.error(f"Failed to connect to Chrome: {e}")
            logger.error("Make sure Chrome is running with --remote-debugging-port=9222")
            logger.error("Run start_chrome_debug.bat first")
            raise
    
    async def disconnect(self):
        """Ngắt kết nối (không đóng Chrome)"""
        if self.browser:
            await self.browser.close()
            logger.info("Disconnected from Chrome")
        
        if self.playwright:
            await self.playwright.stop()
    
    async def create_new_page(self) -> Page:
        """Tạo tab mới để automation (không động vào tabs của user)"""
        if not self.context:
            raise RuntimeError("Not connected. Call connect() first")
        
        page = await self.context.new_page()
        logger.info("Created new page for automation")
        return page


async def patch_browser_use_with_cdp(agent, cdp_url: str = "http://localhost:9222"):
    """
    Patch browser-use agent để dùng Chrome đang chạy thay vì launch mới
    
    Args:
        agent: browser-use Agent instance
        cdp_url: Chrome CDP endpoint URL
    """
    logger.info("Patching browser-use to use existing Chrome via CDP")
    
    # Tạo wrapper
    wrapper = ChromeCDPWrapper(cdp_url)
    
    # Kết nối
    browser, context, page = await wrapper.connect()
    
    # Patch agent's browser
    if hasattr(agent, 'browser'):
        # Đóng browser cũ nếu có
        if agent.browser.browser:
            await agent.browser.browser.close()
        
        # Thay thế bằng browser mới
        agent.browser.browser = browser
        agent.browser.context = context
        
        # Tạo page mới cho automation
        automation_page = await wrapper.create_new_page()
        
        logger.info("✓ Successfully patched browser-use with CDP connection")
        return wrapper, automation_page
    else:
        raise RuntimeError("Agent doesn't have browser attribute")


# Example usage
async def example_usage():
    """Example: Sử dụng CDP wrapper với browser-use"""
    from browser_use import Agent
    
    # Tạo agent như bình thường
    agent = Agent(
        task="Go to Google Drive and list files",
        llm=None  # Your LLM here
    )
    
    # Patch để dùng Chrome đang chạy
    wrapper, page = await patch_browser_use_with_cdp(agent)
    
    try:
        # Chạy agent - nó sẽ dùng Chrome đang chạy
        result = await agent.run()
        print(f"Result: {result}")
    finally:
        # Cleanup
        await wrapper.disconnect()


if __name__ == "__main__":
    # Test basic connection
    async def test():
        wrapper = ChromeCDPWrapper()
        try:
            browser, context, page = await wrapper.connect()
            print(f"Connected! Current page: {page.url}")
            
            # Test navigation
            await page.goto("https://www.google.com")
            print(f"Navigated to: {page.url}")
            
            await asyncio.sleep(3)
        finally:
            await wrapper.disconnect()
    
    asyncio.run(test())
