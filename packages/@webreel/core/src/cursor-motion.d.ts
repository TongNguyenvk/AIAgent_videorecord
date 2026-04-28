import type { CDPClient, Point } from "./types.js";
import type { RecordingContext } from "./actions.js";
/**
 * Animate cursor from one position to another. Pre-computes the full
 * bezier path with easing and jitter, then registers a frame-based
 * tick function (window.__tickCursor) that the recorder calls before
 * every captureScreenshot. Each tick advances exactly one step through
 * the path, so every captured frame shows a smooth intermediate
 * position regardless of actual capture latency.
 */
export declare function animateMoveTo(ctx: RecordingContext, client: CDPClient, fromX: number, fromY: number, toX: number, toY: number): Promise<void>;
export declare function computeEasedPath(fromX: number, fromY: number, toX: number, toY: number, steps: number): Point[];
export declare function computeDragTiming(distance: number): {
    steps: number;
    delayMs: number;
};
//# sourceMappingURL=cursor-motion.d.ts.map