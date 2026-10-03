import type { DocumentInfo, Route, Source } from "./types";

async function json<T>(res: Response): Promise<T> {
  const body = await res.json();
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Request failed.");
  return body as T;
}

export const listDocuments = () => fetch("/api/documents").then((r) => json<DocumentInfo[]>(r));

export function uploadDocument(file: File) {
  const body = new FormData();
  body.append("file", file);
  return fetch("/api/documents", { method: "POST", body }).then((r) => json<DocumentInfo>(r));
}

export const deleteDocument = (name: string) =>
  fetch(`/api/documents/${encodeURIComponent(name)}`, { method: "DELETE" }).then((r) => json(r));

export interface StreamHandlers {
  onRoute: (route: Route, reason: string) => void;
  onSources: (sources: Source[], fellBack: boolean) => void;
  onToken: (token: string) => void;
}

/** POST a chat message and consume the Server-Sent Events stream. */
export async function streamChat(message: string, threadId: string, h: StreamHandlers, signal?: AbortSignal) {
  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error("The server didn't respond. Is the backend running?");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const event = block.match(/^event: (.*)$/m)?.[1];
      const data = JSON.parse(block.match(/^data: (.*)$/m)?.[1] ?? "null");
      if (event === "route") h.onRoute(data.route, data.reason);
      else if (event === "sources") h.onSources(data.sources, data.fell_back);
      else if (event === "token") h.onToken(data);
      else if (event === "error") throw new Error(data);
    }
  }
}
