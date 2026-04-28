# Webreel Core Upgrade Plan

This document outlines the roadmap for upgrading the core Webreel engine (`packages/webreel`) to support more robust automation, better AI integration, and anti-bot bypassing.

## Phase 1: Selector Engine Enhancement (Priority 1)
**Goal:** Improve element targeting reliability beyond basic `document.querySelector`. Webreel currently fails on complex React apps because it lacks native XPath support.

### 1. Native XPath Support (`document.evaluate`)
Webreel relies heavily on `packages/webreel/src/lib/runner.ts`. We need to intercept the selector logic in functions like `waitForSelector`, `resolveTarget`, and `findElementBySelector`.

**Implementation details (Target: `runner.ts`):**
```javascript
// Example modification for findElementBySelector
export async function findElementBySelector(client: CDPClient, selector: string, within?: string): Promise<BoundingBox | null> {
  const isXPath = selector.startsWith("xpath=");
  const expression = isXPath 
    ? `(() => {
        const xpath = ${JSON.stringify(selector.replace('xpath=', ''))};
        const scope = ${within ? `document.querySelector(${JSON.stringify(within)})` : "document"};
        if (!scope) return null;
        const el = document.evaluate(xpath, scope, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: r.x, y: r.y, width: r.width, height: r.height };
      })()`
    : `(() => {
        // ... (existing querySelector logic) ...
      })()`;

  const { result } = await client.Runtime.evaluate({ expression, returnByValue: true });
  return (result.value as BoundingBox) ?? null;
}
```
*Note: Any time `client.Runtime.evaluate({ expression: \`document.querySelector...`) is used (e.g., in `scroll`, `key`, `type`), it MUST be abstracted to handle the `xpath=` format.*

### 2. Robust Selector Fallback Mechanism
**Implementation details:**
- Update `Step` types in `types.ts` to allow `selector: string | string[]`.
- Modify `resolveTarget` to iterate through the array:
```javascript
// Pseudo-logic for resolveTarget
const selectors = Array.isArray(opts.selector) ? opts.selector : [opts.selector];
for (const sel of selectors) {
    const box = await findElementBySelector(client, sel, opts.within);
    if (box) return box; // Success!
}
throw new Error("Element not found after exhausting all selectors");
```

## Phase 2: Timing & User Experience
**Goal:** Prevent hanging and make interactions look more human.

1. **Smart Polling (Auto-wait)**:
   - Replace static `pause` with Playwright-style auto-waiting.
   - Continuously poll the DOM until an element becomes visible and interactive before attempting a `click` or `type`.
2. **Human-like Typing Simulation**:
   - Introduce randomness to the typing speed to simulate human behavior.
   - Example: Randomize `charDelay` between `30ms` and `120ms` per keystroke instead of a fixed delay.

## Phase 3: Anti-Bot Stealth (Bypassing Google/Cloudflare)
**Goal:** Prevent the headless Chrome instance from being blocked by modern WAFs and bot protection.

1. **Stealth Plugin Integration**:
   - Inject `puppeteer-extra-plugin-stealth` script techniques when launching Chrome.
   - Override `navigator.webdriver`, mock plugins, and mask the `window.chrome` object.
2. **Fingerprint Masking**:
   - Randomize WebGL and Canvas fingerprints.
3. **Profile Persistence**:
   - Support loading persistent Chrome profiles (`--user-data-dir`) to retain cookies, sessions, and trust scores, bypassing CAPTCHAs on familiar sites.

## Phase 4: Smart Error Recovery
**Goal:** Automatically recover from selector failures during recording.

1. **Real-time AI Healing**:
   - When a step fails (e.g., element not found), capture the current DOM tree.
   - Send the DOM back to the GenAI model (Gemini) to dynamically identify the new selector for the intended action.
   - Resume execution with the newly discovered selector without failing the entire recording session.
