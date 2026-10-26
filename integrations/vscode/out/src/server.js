"use strict";
/**
 * Backend server resolution and lifecycle.
 *
 * Pure URL helpers are separated from the child-process management so they
 * can be unit-tested without spawning anything.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.BackendServer = void 0;
exports.normalizeServerUrl = normalizeServerUrl;
exports.portOf = portOf;
const node_child_process_1 = require("node:child_process");
function normalizeServerUrl(raw) {
    const trimmed = raw.trim();
    if (!trimmed) {
        throw new Error("server URL is empty");
    }
    if (!/^https?:\/\//i.test(trimmed)) {
        throw new Error(`invalid server URL: ${raw} (expected http(s)://host:port)`);
    }
    return trimmed.replace(/\/+$/, "");
}
function portOf(url) {
    try {
        const port = Number(new URL(url).port);
        return Number.isFinite(port) && port > 0 ? port : 8765;
    }
    catch {
        return 8765;
    }
}
class BackendServer {
    child = null;
    get running() {
        return this.child !== null;
    }
    /** True when this extension started the process (so it owns the lifecycle). */
    startedByUs() {
        return this.child !== null;
    }
    async ensureStarted(cwd, url, options) {
        if (this.child) {
            return;
        }
        const port = portOf(url);
        const binary = options?.binary ?? process.env.APEX_BIN ?? "apex";
        this.child = (0, node_child_process_1.spawn)(binary, ["serve", "--cwd", cwd, "--port", String(port)], {
            cwd,
            stdio: "ignore",
        });
        this.child.on("exit", () => {
            this.child = null;
        });
        this.child.on("error", () => {
            this.child = null;
        });
    }
    async stop() {
        const child = this.child;
        this.child = null;
        if (!child) {
            return;
        }
        await new Promise((resolve) => {
            const timer = setTimeout(() => {
                child.kill("SIGKILL");
                resolve();
            }, 5000);
            child.once("exit", () => {
                clearTimeout(timer);
                resolve();
            });
            child.kill("SIGTERM");
        });
    }
}
exports.BackendServer = BackendServer;
//# sourceMappingURL=server.js.map