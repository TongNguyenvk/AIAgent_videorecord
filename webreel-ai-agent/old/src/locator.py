from playwright.sync_api import Page

_TARGET_SELECTOR_JS = """
(args) => {
    const { x, y, targetDescription = '', preferInput = false, preferClickable = false } = args;
    const stopWords = new Set([
        'o', 'ô', 'nut', 'nút', 'button', 'link', 'field', 'input', 'hop', 'hộp',
        'the', 'thẻ', 'vao', 'vào', 'tren', 'trên', 'duoi', 'dưới', 'ben', 'bên',
        'phia', 'phía', 'goc', 'góc', 'tai', 'tại', 'de', 'để', 'click', 'nhan',
        'nhấn', 'go', 'gõ', 'chon', 'chọn', 'cua', 'của', 'trong'
    ]);

    function cssEscape(value) {
        if (window.CSS && window.CSS.escape) return window.CSS.escape(value);
        return String(value).replace(/[^a-zA-Z0-9_-]/g, (ch) => `\\\\${ch}`);
    }

    function normalize(text) {
        return (text || '')
            .normalize('NFD')
            .replace(/\\p{M}+/gu, '')
            .toLowerCase()
            .replace(/\\s+/g, ' ')
            .trim();
    }

    function getWords(text) {
        return normalize(text)
            .split(/[^\\p{L}\\p{N}]+/u)
            .filter((word) => word.length > 1 && !stopWords.has(word));
    }

    function isVisible(elem) {
        if (!elem) return false;
        const rect = elem.getBoundingClientRect();
        if (!rect || rect.width <= 0 || rect.height <= 0) return false;
        const style = window.getComputedStyle(elem);
        return style.visibility !== 'hidden' && style.display !== 'none' && style.pointerEvents !== 'none';
    }

    function isTextInput(elem) {
        if (!elem) return false;
        if (elem.tagName === 'TEXTAREA') return true;
        if (elem.tagName !== 'INPUT') return false;
        const type = (elem.getAttribute('type') || 'text').toLowerCase();
        return ['text', 'search', 'email', 'password', 'tel', 'url', 'number'].includes(type);
    }

    function isInteractive(elem) {
        if (!elem) return false;
        const tag = elem.tagName.toLowerCase();
        if (['button', 'a', 'input', 'textarea', 'select', 'label', 'summary'].includes(tag)) {
            return true;
        }
        const role = (elem.getAttribute('role') || '').toLowerCase();
        if (['button', 'link', 'tab', 'menuitem', 'option', 'checkbox', 'radio', 'switch'].includes(role)) {
            return true;
        }
        const tabIndex = elem.getAttribute('tabindex');
        if (tabIndex && tabIndex !== '-1') return true;
        return window.getComputedStyle(elem).cursor === 'pointer';
    }

    function elementLabel(elem) {
        const parts = [
            elem.getAttribute('aria-label'),
            elem.getAttribute('placeholder'),
            elem.getAttribute('title'),
            elem.getAttribute('alt'),
        ];
        if (elem.tagName === 'INPUT' || elem.tagName === 'TEXTAREA') {
            parts.push(elem.getAttribute('value'));
        }
        const text = elem.textContent ? elem.textContent.trim() : '';
        if (text) parts.push(text);
        return normalize(parts.filter(Boolean).join(' '));
    }

    function uniqueSelector(candidate) {
        try {
            return document.querySelectorAll(candidate).length === 1 ? candidate : null;
        } catch (_) {
            return null;
        }
    }

    function selectorByAttribute(elem, tag, attr) {
        const value = elem.getAttribute(attr);
        if (!value) return null;
        const escaped = String(value).replace(/["\\\\]/g, '\\\\$&');
        const candidate = attr === 'id'
            ? `#${cssEscape(value)}`
            : `${tag}[${attr}="${escaped}"]`;
        return uniqueSelector(candidate);
    }

    function selectorByClasses(elem, tag) {
        if (!elem.className || typeof elem.className !== 'string') return null;
        const classes = elem.className.trim().split(/\\s+/).filter(Boolean).slice(0, 3);
        if (!classes.length) return null;
        const candidate = `${tag}.${classes.map(cssEscape).join('.')}`;
        return uniqueSelector(candidate);
    }

    function buildPath(node) {
        if (!node || node === document.body) return 'body';
        if (node.id) return `#${cssEscape(node.id)}`;

        const parent = node.parentElement;
        if (!parent) return node.tagName.toLowerCase();

        const siblings = Array.from(parent.children).filter((child) => child.tagName === node.tagName);
        const suffix = siblings.length > 1
            ? `:nth-of-type(${siblings.indexOf(node) + 1})`
            : '';
        return `${buildPath(parent)} > ${node.tagName.toLowerCase()}${suffix}`;
    }

    function getSelector(elem) {
        if (!elem || !isVisible(elem)) return null;
        const tag = elem.tagName.toLowerCase();

        for (const attr of ['id', 'data-testid', 'data-test', 'data-id', 'data-cy', 'name']) {
            const selector = selectorByAttribute(elem, tag, attr);
            if (selector) return selector;
        }

        const classSelector = selectorByClasses(elem, tag);
        if (classSelector) return classSelector;

        for (const attr of ['aria-label', 'placeholder', 'title']) {
            const selector = selectorByAttribute(elem, tag, attr);
            if (selector) return selector;
        }

        return buildPath(elem);
    }

    function candidateScore(elem, depth, sampleX, sampleY, targetWords, wantsInput, wantsClickable) {
        if (!isVisible(elem)) return null;
        const rect = elem.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const distance = Math.hypot(sampleX - centerX, sampleY - centerY);
        const area = rect.width * rect.height;
        const label = elementLabel(elem);
        const tag = elem.tagName.toLowerCase();
        let score = 0;

        if (isInteractive(elem)) score += 90;
        if (isTextInput(elem)) score += wantsInput ? 130 : 25;
        if (wantsInput && !isTextInput(elem)) score -= 70;
        if (wantsClickable && ['button', 'a', 'label'].includes(tag)) score += 50;
        if (wantsClickable && !wantsInput && (tag === 'input' || tag === 'textarea')) score += 40;

        if (targetWords.length) {
            const matches = targetWords.filter((word) => label.includes(word)).length;
            score += matches * 30;
            if (matches === targetWords.length) score += 35;
        }

        if (sampleX >= rect.left && sampleX <= rect.right && sampleY >= rect.top && sampleY <= rect.bottom) {
            score += 15;
        }

        score -= distance * 0.7;
        score -= Math.min(area / 7000, 55);
        score -= depth * 8;
        return score;
    }

    function addCandidate(store, elem, depth, sampleX, sampleY, targetWords, wantsInput, wantsClickable) {
        const selector = getSelector(elem);
        if (!selector) return;
        const score = candidateScore(elem, depth, sampleX, sampleY, targetWords, wantsInput, wantsClickable);
        if (score === null) return;
        const existing = store.get(selector);
        if (!existing || existing.score < score) {
            store.set(selector, { selector, score });
        }
    }

    const targetWords = getWords(targetDescription);
    const wantsInput = preferInput || /(input|field|textbox|textarea|search|email|password|username|ô|nhập|nhap|tim|tìm)/i.test(targetDescription);
    const wantsClickable = preferClickable || !wantsInput;
    const samples = [
        [x, y],
        [x + 8, y], [x - 8, y], [x, y + 8], [x, y - 8],
        [x + 16, y], [x - 16, y], [x, y + 16], [x, y - 16],
    ];
    const store = new Map();

    for (const [sampleX, sampleY] of samples) {
        let elem = document.elementFromPoint(sampleX, sampleY);
        let depth = 0;
        while (elem && depth < 6) {
            addCandidate(store, elem, depth, sampleX, sampleY, targetWords, wantsInput, wantsClickable);

            const descendants = elem.querySelectorAll('button, a, input, textarea, select, label, [role], [tabindex]');
            for (const child of descendants) {
                if (!isVisible(child)) continue;
                const rect = child.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                if (Math.hypot(x - centerX, y - centerY) <= 180) {
                    addCandidate(store, child, depth + 1, sampleX, sampleY, targetWords, wantsInput, wantsClickable);
                }
            }

            elem = elem.parentElement;
            depth += 1;
        }
    }

    if (targetWords.length) {
        const searchPool = document.querySelectorAll('button, a, input, textarea, select, label, [role], [tabindex]');
        for (const elem of searchPool) {
            const label = elementLabel(elem);
            if (!label) continue;
            if (targetWords.some((word) => label.includes(word))) {
                addCandidate(store, elem, 3, x, y, targetWords, wantsInput, wantsClickable);
            }
        }
    }

    const ranked = Array.from(store.values()).sort((a, b) => b.score - a.score);
    return ranked.length ? ranked[0].selector : null;
}
"""


def extract_selector_from_coordinates(
    page: Page,
    x: int,
    y: int,
    target_description: str | None = None,
    prefer_input: bool = False,
    prefer_clickable: bool = False,
) -> str | None:
    """
    Use document.elementFromPoint() to identify the DOM element at (x, y)
    and return a stable CSS selector for the best semantic target nearby.

    Args:
        page: Active Playwright Page.
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.
        target_description: Human description of the intended UI target.
        prefer_input: Prefer text inputs and textareas.
        prefer_clickable: Prefer buttons, links, labels, and interactive elements.

    Returns:
        CSS selector string, or None if no element found.
    """
    return page.evaluate(
        _TARGET_SELECTOR_JS,
        {
            "x": x,
            "y": y,
            "targetDescription": target_description or "",
            "preferInput": prefer_input,
            "preferClickable": prefer_clickable,
        },
    )


def validate_selector(
    page: Page,
    selector: str,
    expected_x: int,
    expected_y: int,
    tolerance: int = 60,
) -> bool:
    """
    Verify that the selector resolves to an element whose center is close
    to the expected coordinates.

    Args:
        page: Active Playwright Page.
        selector: CSS selector to validate.
        expected_x: Expected center X.
        expected_y: Expected center Y.
        tolerance: Max allowed pixel distance.

    Returns:
        True if the selector is valid and close enough.
    """
    try:
        # :has-text selectors are Playwright-only; use query_selector safely
        element = page.query_selector(selector)
        if not element:
            return False

        box = element.bounding_box()
        if not box:
            return False

        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        distance = ((center_x - expected_x) ** 2 + (center_y - expected_y) ** 2) ** 0.5

        return distance <= tolerance
    except Exception:
        return False


def extract_input_selector(
    page: Page,
    x: int,
    y: int,
    target_description: str | None = None,
) -> str | None:
    """
    Find the nearest input/textarea element at or near the given coordinates.
    
    This is specifically designed for 'type' actions where we need to find
    an actual input element, not a wrapper div.

    Args:
        page: Active Playwright Page.
        x: Horizontal pixel coordinate.
        y: Vertical pixel coordinate.

    Returns:
        CSS selector for an input/textarea element, or None if not found.
    """
    return extract_selector_from_coordinates(
        page,
        x,
        y,
        target_description=target_description,
        prefer_input=True,
        prefer_clickable=True,
    )
