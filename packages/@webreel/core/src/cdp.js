import CDP from "chrome-remote-interface";
export async function connectCDP(port) {
    return (await CDP({ port }));
}
export async function connectCDPUrl(url) {
    let host = "localhost";
    let port = 9222;
    try {
        const parsed = new URL(url);
        host = parsed.hostname || "localhost";
        port = parsed.port ? parseInt(parsed.port, 10) : 9222;
    }
    catch (e) {
        // If invalid URL, assume it's just a port or host:port
        const parts = url.split(":");
        host = parts.length > 1 ? parts[0] : "localhost";
        port = parts.length > 1 ? parseInt(parts[1], 10) : parseInt(parts[0], 10);
        if (isNaN(port))
            port = 9222;
    }
    // Create a brand new tab for Webreel to ensure clean state
    const newTarget = await CDP.New({ host, port, url: "about:blank" });
    return (await CDP({ host, port, target: newTarget }));
}
//# sourceMappingURL=cdp.js.map