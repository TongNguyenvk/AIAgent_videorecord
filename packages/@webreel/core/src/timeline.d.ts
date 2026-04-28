import type { Point, SoundEvent } from "./types.js";
interface CursorState {
    x: number;
    y: number;
    scale: number;
}
interface HudState {
    labels: string[];
}
interface FrameData {
    cursor: CursorState;
    hud: HudState | null;
}
export interface TimelineData {
    fps: number;
    width: number;
    height: number;
    zoom: number;
    theme: {
        cursorSvg: string;
        cursorSize: number;
        cursorHotspot: "top-left" | "center";
        hud: {
            background: string;
            color: string;
            fontSize: number;
            fontFamily: string;
            borderRadius: number;
            position: "top" | "bottom";
        };
    };
    frames: FrameData[];
    events: SoundEvent[];
}
export declare class InteractionTimeline {
    private cursorPath;
    private pathIndex;
    private currentCursor;
    private currentHud;
    private frames;
    private events;
    private frameCount;
    private tickResolvers;
    private width;
    private height;
    private zoom;
    private fps;
    private cursorSvg;
    private cursorSize;
    private cursorHotspot;
    private hudConfig;
    constructor(width?: number, height?: number, options?: {
        zoom?: number;
        fps?: number;
        initialCursor?: {
            x: number;
            y: number;
        };
        cursorSvg?: string;
        cursorSize?: number;
        cursorHotspot?: "top-left" | "center";
        hud?: Partial<TimelineData["theme"]["hud"]>;
        loadedFrames?: FrameData[];
        loadedEvents?: SoundEvent[];
    });
    setCursorPath(positions: Point[]): void;
    setCursorScale(scale: number): void;
    showHud(labels: string[]): void;
    hideHud(): void;
    addEvent(type: "click" | "key"): void;
    waitForNextTick(): Promise<void>;
    tick(): void;
    tickDuplicate(): void;
    private pushCurrentState;
    getEvents(): SoundEvent[];
    getFrameCount(): number;
    toJSON(): TimelineData;
    save(path: string): void;
    static load(json: TimelineData): InteractionTimeline;
}
export {};
//# sourceMappingURL=timeline.d.ts.map