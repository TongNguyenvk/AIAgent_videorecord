import type { CDPClient } from "./types.js";
export interface OverlayTheme {
    cursorSvg?: string;
    cursorSize?: number;
    cursorHotspot?: "top-left" | "center";
    hud?: {
        background?: string;
        color?: string;
        fontSize?: number;
        fontFamily?: string;
        borderRadius?: number;
        position?: "top" | "bottom";
    };
}
export declare function injectOverlays(client: CDPClient, theme?: OverlayTheme, initialPosition?: {
    x: number;
    y: number;
}): Promise<void>;
export declare function showKeys(client: CDPClient, labels: string[]): Promise<void>;
export declare function hideKeys(client: CDPClient): Promise<void>;
//# sourceMappingURL=overlays.d.ts.map