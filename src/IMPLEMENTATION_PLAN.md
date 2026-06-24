# Webreel Core Upgrade & Type Hang Fix Plan

This plan consolidates the architectural enhancements for Webreel core and specifies the exact fix for the "silent type hang" issue.

## User Review Required

Please review the proposed architectural changes and the bug fix implementation details below.

## Proposed Changes

### Core Enhancements & Refactoring
- Refactor the massive [runner.ts](file:///f:/==HK1-2526==/ThucTap/webreel/packages/webreel/src/lib/runner.ts) file by moving DOM selector logic into `src/lib/dom/selector.ts`.
- Update [types.ts](file:///f:/==HK1-2526==/ThucTap/webreel/packages/webreel/src/lib/types.ts) to support fallback selector arrays (e.g. `selector: string | string[]`).
- Integrate natively XPath selectors without crashing, which will natively consume `browser-use` history data.
- Add CDP stealth scripts to bypass Cloudflare/bot protections.
- Add smart auto-waiting logic to replace rigid [pause()](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#110-113) calls.

### Bug Fix: Silent Type Hang
#### [MODIFY] recorder.ts
Update the `captureLoop` method to properly handle CDP disconnection/render instabilities during heavy tasks:
1. Increase the `consecutiveErrors` threshold from `10` to `300` to survive React DOM stutters.
2. Add `await new Promise((r) => setTimeout(r, this.frameMs));` in the catch block to prevent burning CPU on immediate retries.
3. Call `this.timeline?.tick()` before breaking the loop on fatal errors. This releases the deadlock preventing [typeText](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#621-677) from waiting indefinitely for a frame that never arrives.

## Verification Plan

### Automated Tests
- Run `pnpm type-check` to ensure no typing breaking changes.

### Manual Verification
- Test video generation on a heavy React app (like the Webreel Dashboard) and trigger an intentional sequence of [click](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#320-474) followed by [type](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#621-677).
- Verify the fallback selector logic using the [browser_use_history.json](file:///f:/==HK1-2526==/ThucTap/webreel/output/test-phuctap-fix/browser_use_history.json) payload directly.
- Verify that when the recording encounters an actual rendering stall, it handles it gracefully instead of locking up the main thread indefinitely.
