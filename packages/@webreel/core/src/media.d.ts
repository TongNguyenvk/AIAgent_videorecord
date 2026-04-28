import type { SoundEvent } from "./types.js";
export interface SfxConfig {
    click?: 1 | 2 | 3 | 4 | string;
    key?: 1 | 2 | 3 | 4 | string;
}
export declare function resolveSfxPath(value: 1 | 2 | 3 | 4 | string | undefined, prefix: "click" | "key"): string;
export declare function ensureSoundAssets(sfx?: SfxConfig): {
    clickPath: string;
    keyPath: string;
};
export declare function buildAudioMixArgs(videoInput: string, events: SoundEvent[], durationSec: number, sfx?: SfxConfig): {
    inputArgs: string[];
    filterComplex: string;
};
export interface FinalizeMp4Options {
    remux?: boolean;
    sfx?: SfxConfig;
}
export declare function finalizeMp4(ffmpegPath: string, tempVideo: string, outputPath: string, events: SoundEvent[], durationSec: number, options?: FinalizeMp4Options): void;
export declare function finalizeWebm(ffmpegPath: string, tempVideo: string, outputPath: string, events: SoundEvent[], durationSec: number, sfx?: SfxConfig): void;
export declare function extractThumbnail(ffmpegPath: string, videoPath: string, outputPath: string, timeSec: number): void;
export declare function finalizeGif(ffmpegPath: string, tempVideo: string, outputPath: string, width: number): void;
//# sourceMappingURL=media.d.ts.map