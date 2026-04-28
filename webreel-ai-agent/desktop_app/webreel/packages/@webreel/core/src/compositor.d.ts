import type { TimelineData } from "./timeline.js";
import { type SfxConfig } from "./media.js";
export interface ComposeOptions {
    sfx?: SfxConfig;
    crf?: number;
}
export declare function compose(cleanVideoPath: string, timelineData: TimelineData, outputPath: string, options?: ComposeOptions): Promise<void>;
//# sourceMappingURL=compositor.d.ts.map