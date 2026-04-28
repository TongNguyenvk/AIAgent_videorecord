import { spawn } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { resolve, extname } from "node:path";
import { TARGET_FPS, DEFAULT_VIEWPORT_SIZE } from "./types.js";
import { ensureFfmpeg } from "./ffmpeg.js";
import { finalizeMp4, finalizeWebm, finalizeGif } from "./media.js";
export class Recorder {
    outputPath = "";
    frameCount = 0;
    running = false;
    capturePromise = null;
    events = [];
    outputWidth;
    outputHeight;
    sfx;
    fps;
    frameMs;
    crf;
    ffmpegPath = "ffmpeg";
    ffmpegProcess = null;
    tempVideo = "";
    drainResolve = null;
    droppedFrames = 0;
    timeline = null;
    ctx = null;
    framesDir = null;
    stopResolve = null;
    stoppedPromise = null;
    constructor(outputWidth = DEFAULT_VIEWPORT_SIZE, outputHeight = DEFAULT_VIEWPORT_SIZE, options) {
        this.outputWidth = outputWidth;
        this.outputHeight = outputHeight;
        this.sfx = options?.sfx;
        this.fps = options?.fps ?? TARGET_FPS;
        this.frameMs = 1000 / this.fps;
        this.crf = options?.crf ?? 18;
        if (options?.framesDir) {
            this.framesDir = options.framesDir;
            mkdirSync(this.framesDir, { recursive: true });
        }
    }
    setTimeline(timeline) {
        this.timeline = timeline;
    }
    getTimeline() {
        return this.timeline;
    }
    getTimelineData() {
        return this.timeline?.toJSON() ?? null;
    }
    addEvent(type) {
        if (this.running) {
            const timeMs = (this.frameCount / this.fps) * 1000;
            this.events.push({ type, timeMs });
        }
    }
    async start(client, outputPath, ctx) {
        this.ffmpegPath = await ensureFfmpeg();
        this.outputPath = outputPath;
        this.frameCount = 0;
        this.droppedFrames = 0;
        this.running = true;
        this.events = [];
        this.ctx = ctx ?? null;
        if (this.ctx)
            this.ctx.setRecorder(this);
        const workDir = resolve(homedir(), ".webreel");
        mkdirSync(workDir, { recursive: true });
        this.tempVideo = resolve(workDir, `_rec_${Date.now()}.mp4`);
        this.ffmpegProcess = spawn(this.ffmpegPath, [
            "-y",
            "-f",
            "image2pipe",
            "-framerate",
            String(this.fps),
            "-c:v",
            "mjpeg",
            "-i",
            "pipe:0",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            String(this.crf),
            "-pix_fmt",
            "yuv420p",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-movflags",
            "+faststart",
            "-r",
            String(this.fps),
            "-vsync",
            "cfr",
            this.tempVideo,
        ], { stdio: ["pipe", "pipe", "pipe"] });
        const resolveDrain = () => {
            const resolve = this.drainResolve;
            if (resolve) {
                this.drainResolve = null;
                resolve();
            }
        };
        const stdin = this.ffmpegProcess.stdin;
        if (!stdin)
            throw new Error("ffmpeg process has no stdin pipe");
        stdin.on("drain", resolveDrain);
        this.ffmpegProcess.on("close", resolveDrain);
        this.stoppedPromise = new Promise((resolve) => {
            this.stopResolve = resolve;
        });
        this.capturePromise = this.captureLoop(client);
    }
    async writeFrame(buffer) {
        if (!this.running)
            return;
        const stdin = this.ffmpegProcess?.stdin;
        if (!stdin?.writable) {
            this.droppedFrames++;
            return;
        }
        const ok = stdin.write(buffer);
        if (!ok) {
            await new Promise((res) => {
                this.drainResolve = res;
            });
        }
    }
    async raceStop(promise) {
        const stopped = this.stoppedPromise.then(() => null);
        const result = await Promise.race([promise, stopped]);
        return result;
    }
    async captureLoop(client) {
        let lastFrameTime = Date.now();
        let consecutiveErrors = 0;
        while (this.running) {
            try {
                if (this.timeline) {
                    this.timeline.tick();
                }
                else {
                    const evalResult = await this.raceStop(client.Runtime.evaluate({
                        expression: "window.__tickCursor&&window.__tickCursor()",
                    }));
                    if (!evalResult)
                        break;
                }
                const screenshotResult = await this.raceStop(Promise.race([
                    client.Page.captureScreenshot({
                        format: "jpeg",
                        quality: 60,
                        optimizeForSpeed: true,
                    }),
                    new Promise((_, reject) => setTimeout(() => reject(new Error("captureScreenshot timeout")), 2000))
                ]));
                if (!screenshotResult)
                    break;
                const buffer = Buffer.from(screenshotResult.data, "base64");
                const now = Date.now();
                const elapsed = now - lastFrameTime;
                const frameSlots = Math.min(600, Math.max(1, Math.round(elapsed / this.frameMs)));
                if (frameSlots > 1) {
                    for (let i = 0; i < frameSlots - 1; i++) {
                        if (this.timeline)
                            this.timeline.tickDuplicate();
                        await this.writeFrame(buffer);
                        this.frameCount++;
                    }
                }
                await this.writeFrame(buffer);
                this.frameCount++;
                if (this.framesDir) {
                    const padded = String(this.frameCount).padStart(5, "0");
                    writeFileSync(resolve(this.framesDir, `frame-${padded}.jpg`), buffer);
                }
                lastFrameTime = now;
                consecutiveErrors = 0;
            }
            catch (err) {
                if (!this.running)
                    break;
                consecutiveErrors++;
                // During page navigations, captureScreenshot can throw rapidly.
                // Wait a frame before retrying, and increase tolerance to 300 (~10s at 30fps).
                // This prevents the silent type hang from deadlock when React DOM shifts.
                if (consecutiveErrors >= 300) {
                    console.error(`Recording aborted after ${consecutiveErrors} consecutive capture failures:`, err);
                    // Release any pending waitForNextTick promises so the runner doesn't hang
                    if (this.timeline) {
                        this.timeline.tick();
                    }
                    break;
                }
                await new Promise((r) => setTimeout(r, this.frameMs));
            }
        }
    }
    getTempVideoPath() {
        return this.tempVideo;
    }
    async stop() {
        this.running = false;
        if (this.ctx)
            this.ctx.setRecorder(null);
        if (this.drainResolve) {
            this.drainResolve();
            this.drainResolve = null;
        }
        if (this.stopResolve) {
            this.stopResolve();
            this.stopResolve = null;
        }
        await this.capturePromise;
        if (this.droppedFrames > 0) {
            console.warn(`Warning: ${this.droppedFrames} frame(s) dropped during recording`);
        }
        if (this.ffmpegProcess) {
            const proc = this.ffmpegProcess;
            const FFMPEG_CLOSE_TIMEOUT_MS = 10_000;
            const killTimer = setTimeout(() => {
                try {
                    proc.kill("SIGKILL");
                }
                catch {
                    // Process may have already exited
                }
            }, FFMPEG_CLOSE_TIMEOUT_MS);
            await new Promise((res) => {
                if (proc.exitCode !== null) {
                    res();
                    return;
                }
                proc.once("close", () => res());
                try {
                    proc.stdin?.end();
                }
                catch (err) {
                    console.warn("Failed to close ffmpeg stdin:", err);
                    res();
                }
            });
            clearTimeout(killTimer);
            this.ffmpegProcess = null;
        }
        if (this.frameCount === 0) {
            rmSync(this.tempVideo, { force: true });
            return;
        }
        // When a timeline is set, the caller is responsible for the temp video
        // (e.g. renaming it for later compositing). Don't delete or finalize it.
        if (this.timeline) {
            return;
        }
        try {
            const durationSec = this.frameCount / this.fps;
            const ext = extname(this.outputPath).toLowerCase();
            if (ext === ".webm") {
                finalizeWebm(this.ffmpegPath, this.tempVideo, this.outputPath, this.events, durationSec, this.sfx);
            }
            else if (ext === ".gif") {
                finalizeGif(this.ffmpegPath, this.tempVideo, this.outputPath, this.outputWidth);
            }
            else {
                finalizeMp4(this.ffmpegPath, this.tempVideo, this.outputPath, this.events, durationSec, { sfx: this.sfx });
            }
        }
        finally {
            rmSync(this.tempVideo, { force: true });
        }
    }
}
//# sourceMappingURL=recorder.js.map