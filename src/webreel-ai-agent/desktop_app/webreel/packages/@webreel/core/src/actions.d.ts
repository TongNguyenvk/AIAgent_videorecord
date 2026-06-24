import type { CDPClient, BoundingBox } from "./types.js";
import type { InteractionTimeline } from "./timeline.js";
export declare class RecordingContext {
    private _mode;
    private _timeline;
    private _recorder;
    private _cursorX;
    private _cursorY;
    private _clickDwell;
    get mode(): "record" | "preview";
    setMode(mode: "record" | "preview"): void;
    get timeline(): InteractionTimeline | null;
    setTimeline(timeline: InteractionTimeline | null): void;
    setRecorder(recorder: {
        addEvent: (type: "click" | "key") => void;
    } | null): void;
    get cursorX(): number;
    get cursorY(): number;
    setCursorPosition(x: number, y: number): void;
    get isRecording(): boolean;
    resetCursorPosition(cssWidth?: number, cssHeight?: number): void;
    setClickDwell(ms: number | undefined): void;
    getClickDwellMs(): number;
    getCursorPosition(): {
        x: number;
        y: number;
    };
    markEvent(type: "click" | "key"): void;
}
export declare function modKey(): string;
export declare function pause(ms?: number): Promise<void>;
export declare function buildElementExpression(selector: string, within?: string): string;
export declare function navigate(client: CDPClient, url: string): Promise<void>;
export declare function waitForSelector(client: CDPClient, selector: string | string[], timeoutMs?: number, within?: string): Promise<void>;
export declare function waitForText(client: CDPClient, text: string, within?: string, timeoutMs?: number): Promise<void>;
export declare function waitForInteractive(client: CDPClient, box: BoundingBox, timeoutMs?: number): Promise<void>;
export declare function findElementByText(client: CDPClient, text: string, within?: string): Promise<BoundingBox | null>;
export declare function findElementBySelector(client: CDPClient, selector: string, within?: string): Promise<BoundingBox | null>;
export declare function moveCursorTo(ctx: RecordingContext, client: CDPClient, x: number, y: number): Promise<void>;
export declare function resolveMod(mod: string): string;
export declare function modifierFlag(mod: string): number;
export declare function modifiersToFlag(mods?: string[]): number;
export declare function modLabel(mod: string): string;
interface ModKeyInfo {
    key: string;
    code: string;
    keyCode: number;
    location: number;
}
export declare function modKeyInfo(mod: string): ModKeyInfo | null;
export declare function clickAt(ctx: RecordingContext, client: CDPClient, x: number, y: number, modifiers?: string[]): Promise<void>;
export declare const KEY_CODES: Record<string, {
    code: string;
    keyCode: number;
}>;
export declare const SHORTCUT_COMMANDS: Record<string, string[]>;
export declare function resolveCommands(modifiers: string[], mainKey: string): string[] | undefined;
export declare function pressKey(ctx: RecordingContext, client: CDPClient, key: string, label?: string): Promise<void>;
export declare const CHAR_CODES: Record<string, {
    code: string;
    keyCode: number;
}>;
export declare function typeText(ctx: RecordingContext, client: CDPClient, text: string, delayMs?: number): Promise<void>;
export declare function dragFromTo(ctx: RecordingContext, client: CDPClient, fromBox: BoundingBox, toBox: BoundingBox): Promise<void>;
export declare function captureScreenshot(client: CDPClient, outputPath: string): Promise<void>;
export {};
//# sourceMappingURL=actions.d.ts.map