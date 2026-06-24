import { writeFileSync } from "node:fs";
import { TARGET_FPS, DEFAULT_CURSOR_SVG, DEFAULT_VIEWPORT_SIZE, OFFSCREEN_MARGIN, DEFAULT_CURSOR_SIZE, DEFAULT_HUD_THEME, } from "./types.js";
export class InteractionTimeline {
    cursorPath = null;
    pathIndex = 0;
    currentCursor = {
        x: -OFFSCREEN_MARGIN,
        y: -OFFSCREEN_MARGIN,
        scale: 1,
    };
    currentHud = null;
    frames = [];
    events = [];
    frameCount = 0;
    tickResolvers = [];
    width;
    height;
    zoom;
    fps;
    cursorSvg;
    cursorSize;
    cursorHotspot;
    hudConfig;
    constructor(width = DEFAULT_VIEWPORT_SIZE, height = DEFAULT_VIEWPORT_SIZE, options) {
        this.width = width;
        this.height = height;
        this.zoom = options?.zoom ?? 1;
        this.fps = options?.fps ?? TARGET_FPS;
        if (options?.initialCursor) {
            this.currentCursor = {
                x: options.initialCursor.x,
                y: options.initialCursor.y,
                scale: 1,
            };
        }
        this.cursorSvg = options?.cursorSvg ?? DEFAULT_CURSOR_SVG;
        this.cursorSize = options?.cursorSize ?? DEFAULT_CURSOR_SIZE;
        this.cursorHotspot = options?.cursorHotspot ?? "top-left";
        this.hudConfig = {
            background: options?.hud?.background ?? DEFAULT_HUD_THEME.background,
            color: options?.hud?.color ?? DEFAULT_HUD_THEME.color,
            fontSize: options?.hud?.fontSize ?? DEFAULT_HUD_THEME.fontSize,
            fontFamily: options?.hud?.fontFamily ?? DEFAULT_HUD_THEME.fontFamily,
            borderRadius: options?.hud?.borderRadius ?? DEFAULT_HUD_THEME.borderRadius,
            position: options?.hud?.position ?? DEFAULT_HUD_THEME.position,
        };
        if (options?.loadedFrames) {
            this.frames = options.loadedFrames;
            this.frameCount = options.loadedFrames.length;
        }
        if (options?.loadedEvents) {
            this.events = options.loadedEvents;
        }
    }
    setCursorPath(positions) {
        this.cursorPath = positions;
        this.pathIndex = 0;
    }
    setCursorScale(scale) {
        this.currentCursor.scale = scale;
    }
    showHud(labels) {
        this.currentHud = { labels };
    }
    hideHud() {
        this.currentHud = null;
    }
    addEvent(type) {
        const timeMs = (this.frameCount / this.fps) * 1000;
        this.events.push({ type, timeMs });
    }
    waitForNextTick() {
        return new Promise((resolve) => {
            this.tickResolvers.push(resolve);
            // Safety valve: prevent deadlocks if the recorder hangs
            setTimeout(() => {
                const idx = this.tickResolvers.indexOf(resolve);
                if (idx !== -1) {
                    this.tickResolvers.splice(idx, 1);
                    resolve(); // Resolve anyway to unblock the runner
                }
            }, 1000);
        });
    }
    tick() {
        if (this.cursorPath && this.pathIndex < this.cursorPath.length) {
            const p = this.cursorPath[this.pathIndex++];
            this.currentCursor.x = p.x;
            this.currentCursor.y = p.y;
            if (this.pathIndex >= this.cursorPath.length) {
                this.cursorPath = null;
            }
        }
        this.pushCurrentState();
        const resolvers = this.tickResolvers;
        this.tickResolvers = [];
        for (const resolve of resolvers)
            resolve();
    }
    tickDuplicate() {
        this.pushCurrentState();
    }
    pushCurrentState() {
        this.frames.push({
            cursor: { ...this.currentCursor },
            hud: this.currentHud ? { labels: [...this.currentHud.labels] } : null,
        });
        this.frameCount++;
    }
    getEvents() {
        return this.events;
    }
    getFrameCount() {
        return this.frameCount;
    }
    toJSON() {
        return {
            fps: this.fps,
            width: this.width,
            height: this.height,
            zoom: this.zoom,
            theme: {
                cursorSvg: this.cursorSvg,
                cursorSize: this.cursorSize,
                cursorHotspot: this.cursorHotspot,
                hud: this.hudConfig,
            },
            frames: this.frames,
            events: this.events,
        };
    }
    save(path) {
        writeFileSync(path, JSON.stringify(this.toJSON()));
    }
    static load(json) {
        return new InteractionTimeline(json.width, json.height, {
            zoom: json.zoom,
            fps: json.fps,
            cursorSvg: json.theme.cursorSvg,
            cursorSize: json.theme.cursorSize,
            cursorHotspot: json.theme.cursorHotspot,
            hud: json.theme.hud,
            loadedFrames: json.frames,
            loadedEvents: json.events,
        });
    }
}
//# sourceMappingURL=timeline.js.map