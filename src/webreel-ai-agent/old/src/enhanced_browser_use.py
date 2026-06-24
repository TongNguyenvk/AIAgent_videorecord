"""
Enhanced Browser Use - Detect Shadow DOM và iframe
Giải quyết vấn đề Browser Use không thấy được UI đặc biệt của Google
"""

from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


async def inject_shadow_dom_detector(page: Page):
    """
    Inject script để expose Shadow DOM elements ra light DOM
    để Browser Use có thể detect được
    """
    
    script = """
    (function() {
        // Hàm đệ quy để traverse Shadow DOM
        function exposeShadowDOM(root, depth = 0) {
            if (depth > 5) return; // Giới hạn độ sâu
            
            const elements = root.querySelectorAll('*');
            elements.forEach(el => {
                if (el.shadowRoot) {
                    // Mark shadow host
                    el.setAttribute('data-has-shadow', 'true');
                    
                    // Expose shadow children
                    const shadowChildren = el.shadowRoot.querySelectorAll('*');
                    shadowChildren.forEach((child, index) => {
                        // Clone attributes to make them visible
                        if (child.getAttribute('contenteditable')) {
                            el.setAttribute('data-shadow-contenteditable', 'true');
                            el.setAttribute('data-shadow-role', child.getAttribute('role') || '');
                            el.setAttribute('data-shadow-aria-label', child.getAttribute('aria-label') || '');
                        }
                        
                        // Mark input fields
                        if (child.tagName === 'INPUT' || child.tagName === 'TEXTAREA') {
                            el.setAttribute('data-shadow-input', 'true');
                            el.setAttribute('data-shadow-input-type', child.type || '');
                        }
                    });
                    
                    // Đệ quy vào shadow root
                    exposeShadowDOM(el.shadowRoot, depth + 1);
                }
            });
        }
        
        // Chạy ngay
        exposeShadowDOM(document);
        
        // Chạy lại khi DOM thay đổi
        const observer = new MutationObserver(() => {
            exposeShadowDOM(document);
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log('[Shadow DOM Detector] Injected successfully');
    })();
    """
    
    try:
        await page.evaluate(script)
        logger.info("✓ Shadow DOM detector injected")
        return True
    except Exception as e:
        logger.error(f"Failed to inject Shadow DOM detector: {e}")
        return False


async def inject_accessibility_enhancer(page: Page):
    """
    Enhance accessibility tree để Browser Use detect được elements tốt hơn
    """
    
    script = """
    (function() {
        // Thêm aria-label cho các contenteditable divs
        function enhanceAccessibility() {
            // Gmail compose body
            const contentEditables = document.querySelectorAll('div[contenteditable="true"]');
            contentEditables.forEach((el, index) => {
                if (!el.getAttribute('aria-label')) {
                    // Detect context
                    const parent = el.closest('[role="dialog"]') || el.closest('[role="main"]');
                    if (parent) {
                        el.setAttribute('aria-label', `Editable content area ${index + 1}`);
                        el.setAttribute('role', 'textbox');
                    }
                }
            });
            
            // Iframe bodies
            document.querySelectorAll('iframe').forEach((iframe, index) => {
                try {
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    const body = iframeDoc.querySelector('body[contenteditable="true"]');
                    if (body && !body.getAttribute('aria-label')) {
                        body.setAttribute('aria-label', `Iframe editor ${index + 1}`);
                        body.setAttribute('role', 'textbox');
                    }
                } catch (e) {
                    // Cross-origin iframe, skip
                }
            });
        }
        
        // Chạy ngay
        enhanceAccessibility();
        
        // Chạy lại khi DOM thay đổi
        const observer = new MutationObserver(() => {
            enhanceAccessibility();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['contenteditable']
        });
        
        console.log('[Accessibility Enhancer] Injected successfully');
    })();
    """
    
    try:
        await page.evaluate(script)
        logger.info("✓ Accessibility enhancer injected")
        return True
    except Exception as e:
        logger.error(f"Failed to inject accessibility enhancer: {e}")
        return False


async def get_gmail_compose_selector():
    """
    Trả về selector cho ô soạn email Gmail
    Sử dụng nhiều fallback strategies
    """
    
    selectors = [
        # Strategy 1: ContentEditable div với aria-label
        "div[contenteditable='true'][aria-label*='Message']",
        "div[contenteditable='true'][aria-label*='Body']",
        "div[contenteditable='true'][role='textbox']",
        
        # Strategy 2: Gmail specific classes
        "div.Am.Al.editable.LW-avf",
        "div[aria-label='Message Body']",
        "div.editable[contenteditable='true']",
        
        # Strategy 3: Shadow DOM exposed
        "[data-shadow-contenteditable='true']",
        
        # Strategy 4: Iframe fallback
        "iframe[title*='Message']",
        
        # Strategy 5: Generic contenteditable trong compose dialog
        "div[role='dialog'] div[contenteditable='true']",
        
        # Strategy 6: Generic contenteditable
        "div[contenteditable='true']",
    ]
    
    return selectors


async def wait_for_gmail_compose(page: Page, timeout: int = 10000):
    """
    Đợi ô soạn email xuất hiện và trả về selector
    """
    
    selectors = await get_gmail_compose_selector()
    
    for selector in selectors:
        try:
            await page.wait_for_selector(selector, timeout=timeout, state='visible')
            logger.info(f"✓ Found Gmail compose box: {selector}")
            return selector
        except:
            continue
    
    raise TimeoutError("Cannot find Gmail compose box")


async def type_in_gmail_compose(page: Page, text: str):
    """
    Type text vào ô soạn email Gmail
    Xử lý cả Shadow DOM và contenteditable
    """
    
    # Inject detectors trước
    await inject_shadow_dom_detector(page)
    await inject_accessibility_enhancer(page)
    
    # Đợi một chút để scripts chạy
    await page.wait_for_timeout(1000)
    
    # Đợi compose box xuất hiện
    selector = await wait_for_gmail_compose(page)
    
    # Click để focus
    await page.click(selector)
    await page.wait_for_timeout(500)
    
    # Type text
    # Sử dụng keyboard.type thay vì fill vì contenteditable không support fill
    await page.keyboard.type(text, delay=50)
    
    logger.info(f"✓ Typed text in Gmail compose: {text[:50]}...")
    
    return True


async def get_element_in_shadow_dom(page: Page, shadow_host_selector: str, inner_selector: str):
    """
    Lấy element bên trong Shadow DOM
    
    Args:
        page: Playwright page
        shadow_host_selector: Selector của shadow host element
        inner_selector: Selector của element bên trong shadow root
    
    Returns:
        Element handle hoặc None
    """
    
    script = f"""
    (function() {{
        const host = document.querySelector('{shadow_host_selector}');
        if (!host || !host.shadowRoot) return null;
        
        const element = host.shadowRoot.querySelector('{inner_selector}');
        return element;
    }})();
    """
    
    try:
        element = await page.evaluate_handle(script)
        return element
    except Exception as e:
        logger.error(f"Failed to get element in shadow DOM: {e}")
        return None


async def click_in_shadow_dom(page: Page, shadow_host_selector: str, inner_selector: str):
    """
    Click element bên trong Shadow DOM
    """
    
    script = f"""
    (function() {{
        const host = document.querySelector('{shadow_host_selector}');
        if (!host || !host.shadowRoot) return false;
        
        const element = host.shadowRoot.querySelector('{inner_selector}');
        if (!element) return false;
        
        element.click();
        return true;
    }})();
    """
    
    try:
        result = await page.evaluate(script)
        if result:
            logger.info(f"✓ Clicked element in shadow DOM: {inner_selector}")
        return result
    except Exception as e:
        logger.error(f"Failed to click in shadow DOM: {e}")
        return False


async def type_in_shadow_dom(page: Page, shadow_host_selector: str, inner_selector: str, text: str):
    """
    Type text vào element bên trong Shadow DOM
    """
    
    script = f"""
    (function() {{
        const host = document.querySelector('{shadow_host_selector}');
        if (!host || !host.shadowRoot) return false;
        
        const element = host.shadowRoot.querySelector('{inner_selector}');
        if (!element) return false;
        
        element.focus();
        element.textContent = `{text}`;
        
        // Trigger input event
        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
        
        return true;
    }})();
    """
    
    try:
        result = await page.evaluate(script)
        if result:
            logger.info(f"✓ Typed in shadow DOM: {text[:50]}...")
        return result
    except Exception as e:
        logger.error(f"Failed to type in shadow DOM: {e}")
        return False


async def enhance_page_for_browser_use(page: Page):
    """
    Enhance page để Browser Use hoạt động tốt hơn với Google services
    
    Gọi function này sau khi navigate đến trang Google
    """
    
    logger.info("Enhancing page for Browser Use...")
    
    # Inject all enhancers
    await inject_shadow_dom_detector(page)
    await inject_accessibility_enhancer(page)
    
    # Wait for scripts to run
    await page.wait_for_timeout(1000)
    
    logger.info("✓ Page enhanced successfully")
    
    return True


# Example usage
async def example_usage():
    """Example: Sử dụng enhanced browser use"""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Navigate to Gmail
        await page.goto("https://mail.google.com")
        
        # Enhance page
        await enhance_page_for_browser_use(page)
        
        # Click compose
        await page.click("div[role='button'][gh='cm']")
        await page.wait_for_timeout(2000)
        
        # Type in compose box
        await type_in_gmail_compose(page, "Hello from enhanced browser use!")
        
        await browser.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
