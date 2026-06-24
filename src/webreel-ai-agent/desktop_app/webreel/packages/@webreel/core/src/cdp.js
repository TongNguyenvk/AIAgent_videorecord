import CDP from "chrome-remote-interface";
export async function connectCDP(port) {
    return (await CDP({ port }));
}
export async function connectCDPUrl(url) {
    try {
        const parsed = new URL(url);
        const host = parsed.hostname || "localhost";
        const port = parsed.port ? parseInt(parsed.port, 10) : 9222;
        return (await CDP({ host, port }));
    }
    catch (e) {
        // If invalid URL, assume it's just a port or host:port
        const parts = url.split(":");
        const host = parts.length > 1 ? parts[0] : "localhost";
        const port = parts.length > 1 ? parseInt(parts[1], 10) : parseInt(parts[0], 10);
        return (await CDP({ host, port: isNaN(port) ? 9222 : port }));
    }
}
//# sourceMappingURL=cdp.js.map