# Webreel Core: Analysis of the "Silent Type Hang" Bug

This document analyzes the root cause of the silent hanging issue that occurs sporadically during the [type](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#621-677) action (e.g., at `[step 8] type "teacher@example.com"`) and proposes a concrete fix for the `@webreel/core` package.

## 1. The Symptoms
- The video recording process stops progressing exactly when a [type](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#621-677) action is initiated.
- No error is thrown to the console. The process runs indefinitely.
- The issue is intermittent ("có cái được cái không"). It happens more frequently on heavy pages or immediately after complex [click](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#320-474) interactions.

## 2. Technical Root Cause (The Deadlock)

The hang is caused by a silent deadlock between two separate asynchronous systems within `@webreel/core`:

### A. The Typer ([actions.ts](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts) -> [typeText](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#621-677))
Webreel simulates human typing by introducing delays between characters. To ensure the recorded video matches the typing animation, [typeText](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#621-677) syncs with the video timeline.
```typescript
// packages/@webreel/core/src/actions.ts (inside typeText)
if (ctx.isRecording) {
  const waitStart = Date.now();
  await getTimeline(ctx).waitForNextTick(); // <--- WAITING HERE FOR THE CAMERA
  // ... calculates human delay ...
}
```
The [type](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#621-677) command completely halts execution, waiting for the timeline to announce that it has processed a new video frame.

### B. The Camera ([recorder.ts](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/recorder.ts) -> [captureLoop](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/recorder.ts#161-230))
The camera loop continuously asks headless Chrome for screenshots.
```typescript
// packages/@webreel/core/src/recorder.ts
while (this.running) {
  try {
    if (this.timeline) this.timeline.tick(); // <--- RELEASES WAITING TYPER
    const screenshotResult = await this.raceStop(client.Page.captureScreenshot({...}));
    // ... writes frame ...
    consecutiveErrors = 0;
  } catch (err) {
    if (!this.running) break;
    consecutiveErrors++;
    if (consecutiveErrors >= 10) {
      console.error(`Recording aborted...`);
      break; // <--- CAMERA DIES SILENTLY
    }
  }
}
```

### C. The Collision Scenario
1. Webreel executes a [click](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#320-474) on an input field.
2. The React DOM reacts to the focus event, causing layout shifts or heavy render cycles.
3. Simultaneously, [captureLoop](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/recorder.ts#161-230) asks Chrome [captureScreenshot()](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#837-845).
4. Chrome, busy with the DOM changes, throws internal CDP timeouts or rendering errors.
5. [captureLoop](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/recorder.ts#161-230) fails rapidly. In just a few milliseconds, `consecutiveErrors` hits `10`.
6. The `while` loop hits `break;` and exits. The camera is dead.
7. Next step in the pipeline: [typeText](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#621-677). It immediately calls `await getTimeline(ctx).waitForNextTick()`.
8. Because the camera loop exited, `this.timeline.tick()` is **never called again**.
9. **Result: Deadlock.** The [typeText](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#621-677) function waits forever for a frame that will never arrive, while the main process hangs silently without crashing.

## 3. The Solution

To fix this, we must ensure the camera loop survives temporary React DOM instability, and if it must die, it must not leave waiters hanging.

**Modification to [packages/@webreel/core/src/recorder.ts](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/recorder.ts)**:

```typescript
      } catch (err) {
        if (!this.running) break;
        consecutiveErrors++;
        
        // FIX 1: Increase tolerance and add frame delay to survive navigation/React renders
        // Previously: if (consecutiveErrors >= 10) { ... break; }
        if (consecutiveErrors >= 300) {
          console.error(
            `Recording aborted after ${consecutiveErrors} consecutive capture failures:`,
            err,
          );
          
          // FIX 2: Release the deadlock before breaking!
          // Force a tick so functions awaiting waitForNextTick() (like typeText) can resume or fail gracefully.
          if (this.timeline) {
            this.timeline.tick(); 
          }
          break;
        }
        
        // Delay before retrying to prevent burning CPU and hitting 300 errors instantly
        await new Promise((r) => setTimeout(r, this.frameMs));
      }
```

By applying these two fixes and recompiling `@webreel/core`, the pipeline will either gracefully survive the DOM stutter (and resume typing) or crash visibly, preventing the silent perpetual hang.
