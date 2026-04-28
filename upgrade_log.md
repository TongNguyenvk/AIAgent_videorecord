# Webreel Core Upgrade Log

## Phase 1: Selector Engine Enhancement
### Step 1.1: Update type definitions
- **Goal**: Modify `selector` property in `types.ts` to accept `string | string[]` to support an array of fallbacks.
- **Location**: `packages/webreel/src/lib/types.ts`
- **Result**: [Done] Replaced all `selector?: string` with `selector?: string | string[]`.

### Step 1.2: Implement Array Fallback in Runner
- **Goal**: Modify `resolveTarget` in `runner.ts` to iterate through the array of selectors.
- **Location**: `packages/webreel/src/lib/runner.ts`
- **Result**: [Done] `resolveTarget` safely loops over `selector` arrays and returns the first match.

### Step 1.3: Abstract Selector Logic and XPath Support in Core Actions
- **Goal**: Add `buildElementExpression` and support `xpath=` in `@webreel/core/src/actions.ts` and refactor `findElementBySelector` and `waitForSelector`.
- **Location**: `packages/@webreel/core/src/actions.ts`
- **Result**: [Done] Abstracted evaluating into `buildElementExpression` and exported it. Built `core` successfully with `tsc`.

## Phase 3: Fix Silent Type Hang Deadlock
### Step 3.1: Increase Error Tolerance and Add Release Tick
- **Goal**: Update `recorder.ts` `captureLoop` catch block to prevent deadlock on React rendering.
- **Location**: `packages/@webreel/core/src/recorder.ts`
- **Result**: [Done] Applied 300 tick tolerance and `this.timeline.tick()` release.

## Phase 2: Timing & User Experience
### Step 2.1: Human-like Typing Simulation
- **Goal**: Implement dynamic delay between 30ms-150ms in `typeText`.
- **Location**: `packages/@webreel/core/src/actions.ts`
- **Result**: [Done] Random distribution added. Gaussian-curve with `Math.random` across 6 calls for non-uniform natural spread.

### Step 2.2: Smart Polling in Runner
- **Goal**: Implement auto-waiting instead of static pause before interaction.
- **Location**: `packages/webreel/src/lib/runner.ts`, `packages/@webreel/core/src/actions.ts`
- **Result**: [Done] Implemented `waitForInteractive` which evaluates `window.getComputedStyle(el)` recursively every 100ms. Injected into `type` and `click` commands array iteration. 

## Phase 4: Anti-Bot Stealth
### Step 4.1: Integrate CDP Stealth Scripts
- **Goal**: Add stealth evasion scripts on document creation.
- **Location**: `packages/webreel/src/lib/runner.ts`
- **Result**: [Done] Injected stealth script via `Page.addScriptToEvaluateOnNewDocument` before navigating.

### Step 4.2: Add Persistent Chrome Profiles
- **Goal**: Allow saving browser state across sessions via user-defined profile.
- **Location**: `packages/@webreel/core/src/chrome.ts`, `runner.ts`
- **Result**: [Done] Refactored `launchChrome` options to take `profile?: string`. Removed temp dir wiping if persistent profile.
