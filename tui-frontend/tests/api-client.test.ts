/**
 * Unit tests for APIClient (SSE chat streaming + HTTP helpers).
 * Run with `bun test` (or `npx tsx --test tests/*.test.ts`).
 */

import { afterEach, beforeEach, describe, it } from "node:test"
import assert from "node:assert/strict"
import { APIClient } from "../src/api/client.js"

function sseResponse(body: string): Response {
  const encoder = new TextEncoder()
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(body))
      controller.close()
    },
  })
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  })
}

const SSE_BODY =
  "data: {\"chunk\":\"Hello\"}\n" +
  "data: {\"chunk\":\" world\"}\n" +
  "data: {\"usage\":{\"prompt_tokens\":10,\"completion_tokens\":5}}\n" +
  "data: {\"chunk\":\"!\"}\n"

describe("APIClient", () => {
  let originalFetch: typeof fetch

  beforeEach(() => {
    originalFetch = globalThis.fetch
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it("streams chat via SSE and accumulates text + usage", async () => {
    globalThis.fetch = (async (_url: string | URL | Request, init?: RequestInit) => {
      assert.equal(init?.method, "POST")
      assert.equal(init?.body, JSON.stringify({ message: "hi", model: "test-model" }))
      return sseResponse(SSE_BODY)
    }) as typeof fetch

    const client = new APIClient(9) // port only used for URL construction
    const chunks: string[] = []
    const result = await client.chatStream({
      message: "hi",
      model: "test-model",
      onChunk: (full) => chunks.push(full),
    })

    assert.equal(result.full, "Hello world!")
    assert.deepEqual(result.usage, { prompt_tokens: 10, completion_tokens: 5 })
    assert.deepEqual(chunks, ["Hello", "Hello world", "Hello world!"])
  })

  it("throws on non-OK HTTP status", async () => {
    globalThis.fetch = (async () => new Response("boom", { status: 500 })) as typeof fetch
    const client = new APIClient(9)
    await assert.rejects(() => client.chatStream({ message: "hi", model: "m" }), /Server error 500: boom/)
  })

  it("centralizes API endpoints with ports/encoding", () => {
    const client = new APIClient(4242)
    assert.equal(client.baseUrl, "http://127.0.0.1:4242")
    assert.equal(client.wsUrl, "ws://127.0.0.1:4242/ws/events")
    assert.equal(
      (client as unknown as { request<T>(path: string): Promise<T> }).baseUrl,
      "http://127.0.0.1:4242",
    )
  })
})
