import type { CDPClient } from "./types.js";
import type { RecordingContext } from "./actions.js";
import { type SfxConfig } from "./media.js";
import type { InteractionTimeline, TimelineData } from "./timeline.js";
export declare class Recorder {
    private outputPath;
    private frameCount;
    private running;
    private capturePromise;
    private events;
    private outputWidth;
    private outputHeight;
    private sfx;
    private fps;
    private frameMs;
    private crf;
    private ffmpegPath;
    private ffmpegProcess;
    private tempVideo;
    private drainResolve;
    private droppedFrames;
    private timeline;
    private ctx;
    private framesDir;
    private stopResolve;
    private stoppedPromise;
    constructor(outputWidth?: number, outputHeight?: number, options?: {
        sfx?: SfxConfig;
        fps?: number;
        crf?: number;
        framesDir?: string;
    });
    setTimeline(timeline: InteractionTimeline): void;
    getTimeline(): InteractionTimeline | null;
    getTimelineData(): TimelineData | null;
    addEvent(type: "click" | "key"): void;
    start(client: CDPClient, outputPath: string, ctx?: RecordingContext): Promise<void>;
    private writeFrame;
    private raceStop;
    private captureLoop;
    getTempVideoPath(): string;
    stop(): Promise<void>;
}
//# sourceMappingURL=recorder.d.ts.map