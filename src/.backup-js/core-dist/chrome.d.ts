import { type ChildProcess } from "node:child_process";
export declare const CHROME_CACHE_DIR: string;
export declare const HEADLESS_SHELL_CACHE_DIR: string;
export declare function cftPlatform(): string;
export declare function ensureChrome(): Promise<string>;
export declare function ensureHeadlessShell(): Promise<string>;
export interface ChromeInstance {
    process: ChildProcess;
    port: number;
    kill: () => void;
}
export interface LaunchChromeOptions {
    headless?: boolean;
    profile?: string;
    cdpUrl?: string;
}
export declare function launchChrome(options?: LaunchChromeOptions): Promise<ChromeInstance>;
//# sourceMappingURL=chrome.d.ts.map