"use strict";
/**
 * Thin HTTP/SSE client for the APEX backend (`apex serve`).
 *
 * Uses the global `fetch` API only; no Node-specific modules. The class is
 * deliberately independent of the `vscode` API so it can be unit-tested
 * with a mocked global fetch.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ApexClient = void 0;
const sse_1 = require("./sse");
class ApexClient {
    baseUrl;
    apiKey;
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
    }
    headers(extra) {
        const headers = { "Content-Type": "application/json", ...extra };
        if (this.apiKey) {
            headers["Authorization"] = `Bearer ${this.apiKey}`;
        }
        return headers;
    }
    url(path) {
        return `${this.baseUrl.replace(/\/+$/, "")}${path}`;
    }
    async health() {
        try {
            const resp = await fetch(this.url("/health"), { headers: this.headers() });
            return { ok: resp.ok, status: resp.status };
        }
        catch {
            return { ok: false, status: 0 };
        }
    }
    async models() {
        const resp = await fetch(this.url("/api/v1/models"), { headers: this.headers() });
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        const data = (await resp.json());
        return data.models ?? data.data ?? [];
    }
    async createSession() {
        const resp = await fetch(this.url("/api/v1/sessions"), {
            method: "POST",
            headers: this.headers(),
            body: "{}",
        });
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        const data = (await resp.json());
        return data.session_id ?? data.id ?? "current";
    }
    async diff(sessionId) {
        const resp = await fetch(this.url(`/api/v1/session/${encodeURIComponent(sessionId)}/diff`), {
            headers: this.headers(),
        });
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        return (await resp.json());
    }
    async chatStream(options) {
        const parser = new sse_1.SSEParser();
        let resp;
        try {
            resp = await fetch(this.url("/chat/stream"), {
                method: "POST",
                headers: this.headers(),
                body: JSON.stringify({ message: options.message, model: options.model }),
                signal: options.signal,
            });
        }
        catch (error) {
            options.onError?.(error instanceof Error ? error : new Error(String(error)));
            return;
        }
        if (!resp.ok || !resp.body) {
            options.onError?.(new Error(`HTTP ${resp.status}`));
            return;
        }
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        try {
            for (;;) {
                const { done, value } = await reader.read();
                if (done) {
                    break;
                }
                const messages = parser.push(decoder.decode(value, { stream: true }));
                for (const message of messages) {
                    this.handleSSE(message, options);
                }
            }
            const trailing = parser.flush();
            for (const message of trailing) {
                this.handleSSE(message, options);
            }
            options.onDone?.();
        }
        catch (error) {
            options.onError?.(error instanceof Error ? error : new Error(String(error)));
        }
    }
    handleSSE(message, options) {
        let payload;
        try {
            payload = JSON.parse(message.data);
        }
        catch {
            options.onDelta?.(message.data);
            return;
        }
        if (typeof payload === "object" && payload !== null) {
            const record = payload;
            if (typeof record.chunk === "string") {
                options.onDelta?.(record.chunk);
                return;
            }
            if (record.usage !== undefined) {
                options.onUsage?.(record.usage);
                return;
            }
            if (record.error !== undefined) {
                options.onError?.(new Error(String(record.error)));
                return;
            }
        }
        options.onDelta?.(message.data);
    }
}
exports.ApexClient = ApexClient;
//# sourceMappingURL=client.js.map