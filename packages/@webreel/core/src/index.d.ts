export type { CDPClient, BoundingBox, Point, SoundEvent } from "./types.js";
export { TARGET_FPS, FRAME_MS, DEFAULT_VIEWPORT_SIZE, OFFSCREEN_MARGIN, CAPTURE_CYCLE_MS, DEFAULT_CURSOR_SVG, DEFAULT_CURSOR_SIZE, DEFAULT_HUD_THEME, } from "./types.js";
export { connectCDP, connectCDPUrl } from "./cdp.js";
export { launchChrome, ensureChrome, ensureHeadlessShell, CHROME_CACHE_DIR, HEADLESS_SHELL_CACHE_DIR, type ChromeInstance, type LaunchChromeOptions, } from "./chrome.js";
export { injectOverlays, showKeys, hideKeys, type OverlayTheme } from "./overlays.js";
export { RecordingContext, modKey, pause, navigate, waitForSelector, waitForText, waitForInteractive, findElementByText, findElementBySelector, moveCursorTo, clickAt, pressKey, typeText, dragFromTo, captureScreenshot, buildElementExpression, } from "./actions.js";
export { Recorder } from "./recorder.js";
export { InteractionTimeline, type TimelineData } from "./timeline.js";
export { compose, type ComposeOptions } from "./compositor.js";
export { ensureFfmpeg, FFMPEG_CACHE_DIR } from "./ffmpeg.js";
export { extractThumbnail, type SfxConfig } from "./media.js";
export { moveFileSync } from "./fs.js";
//# sourceMappingURL=index.d.ts.map