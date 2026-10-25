/**
 * Incremental SSE (Server-Sent Events) parser.
 *
 * Pure and synchronous: feed it raw chunks from a stream and it returns the
 * complete events that fell out of those chunks. It follows the WHATWG
 * event-stream format (field names, multi-line data, comments, CRLF).
 */

export interface SSEMessage {
  data: string
  event?: string
  id?: string
}

export class SSEParser {
  private buffer = ""
  private event = ""
  private dataLines: string[] = []
  private dataId: string | undefined

  /** Feed a raw chunk; returns all complete events produced by it. */
  push(chunk: string): SSEMessage[] {
    this.buffer += chunk
    const messages: SSEMessage[] = []
    let idx: number
    while ((idx = this.buffer.indexOf("\n")) !== -1) {
      const rawLine = this.buffer.slice(0, idx)
      this.buffer = this.buffer.slice(idx + 1)
      const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine
      this.consumeLine(line, messages)
    }
    return messages
  }

  /** Dispatch a trailing event whose final line had no newline. */
  flush(): SSEMessage[] {
    const messages: SSEMessage[] = []
    if (this.buffer.length > 0) {
      this.consumeLine(this.buffer, messages)
      this.buffer = ""
    }
    this.dispatch(messages)
    return messages
  }

  private consumeLine(line: string, messages: SSEMessage[]): void {
    if (line === "") {
      this.dispatch(messages)
      return
    }
    if (line.startsWith(":")) {
      return // comment
    }
    const colon = line.indexOf(":")
    const field = colon === -1 ? line : line.slice(0, colon)
    const value = colon === -1 ? "" : line.slice(colon + 1).replace(/^ /, "")
    switch (field) {
      case "event":
        this.event = value
        break
      case "data":
        this.dataLines.push(value)
        break
      case "id":
        this.dataId = value
        break
      default:
        break
    }
  }

  private dispatch(messages: SSEMessage[]): void {
    if (this.dataLines.length > 0 || this.event !== "") {
      messages.push({
        data: this.dataLines.join("\n"),
        event: this.event || undefined,
        id: this.dataId,
      })
    }
    this.event = ""
    this.dataLines = []
    this.dataId = undefined
  }
}
