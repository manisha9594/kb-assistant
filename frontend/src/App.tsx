import { useCallback, useEffect, useRef, useState } from "react";
import { listDocuments, streamChat } from "./api";
import Sidebar from "./components/Sidebar";
import ChatMessage from "./components/ChatMessage";
import Composer from "./components/Composer";
import type { DocumentInfo, Message } from "./types";

/** Questions that match the bundled sample documents, keyed by filename. */
const SAMPLE_QUESTIONS: Record<string, string> = {
  "employee_handbook.pdf": "How many PTO days can I carry over?",
  "it_security_policy.docx": "Can I use SMS codes for MFA?",
  "expense_policy.md": "What's the hotel limit in New York?",
};

function suggestionsFor(docs: DocumentInfo[]): string[] {
  return docs.slice(0, 3).map((d) => SAMPLE_QUESTIONS[d.filename] ?? `Summarize ${d.filename}`);
}

const newId = () => crypto.randomUUID();
const STORAGE_KEY = "kb-assistant:chat";

/** Restore the last conversation; storage can be unavailable, so fail quietly. */
function loadChat(): { threadId: string; messages: Message[] } {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
    if (saved?.threadId && Array.isArray(saved.messages)) {
      return { threadId: saved.threadId, messages: saved.messages.map((m: Message) => ({ ...m, pending: false })) };
    }
  } catch {
    /* ignore */
  }
  return { threadId: newId(), messages: [] };
}

export default function App() {
  const [initial] = useState(loadChat);
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [messages, setMessages] = useState<Message[]>(initial.messages);
  const [threadId, setThreadId] = useState(initial.threadId);
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const refreshDocs = useCallback(() => {
    listDocuments().then(setDocs).catch(() => setDocs([]));
  }, []);
  useEffect(refreshDocs, [refreshDocs]);
  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [messages]);
  useEffect(() => {
    if (busy) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ threadId, messages }));
    } catch {
      /* ignore */
    }
  }, [busy, threadId, messages]);

  const patch = (id: string, update: Partial<Message> | ((m: Message) => Partial<Message>)) =>
    setMessages((all) =>
      all.map((m) => (m.id === id ? { ...m, ...(typeof update === "function" ? update(m) : update) } : m)),
    );

  async function send(text: string) {
    const replyId = newId();
    setMessages((all) => [
      ...all,
      { id: newId(), role: "user", content: text },
      { id: replyId, role: "assistant", content: "", pending: true },
    ]);
    setBusy(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamChat(
        text,
        threadId,
        {
          onRoute: (route, routeReason) => patch(replyId, { route, routeReason }),
          onSources: (sources, fellBack) => patch(replyId, { sources, fellBack }),
          onToken: (t) => patch(replyId, (m) => ({ content: m.content + t })),
        },
        controller.signal,
      );
    } catch (err) {
      if (controller.signal.aborted) patch(replyId, { stopped: true });
      else patch(replyId, { content: (err as Error).message, error: true });
    } finally {
      patch(replyId, { pending: false });
      abortRef.current = null;
      setBusy(false);
    }
  }

  function newChat() {
    abortRef.current?.abort();
    setMessages([]);
    setThreadId(newId());
  }

  return (
    <div className="layout">
      <Sidebar docs={docs} onChange={refreshDocs} onNewChat={newChat} />
      <main className="chat">
        <div className="thread">
          {messages.length === 0 ? (
            <div className="empty">
              <h2>Ask anything about your documents</h2>
              <p>
                Answers cite the file and page they came from. If your documents don't cover it, the
                assistant searches the web or asks you to clarify.
              </p>
              {docs.length > 0 ? (
                <div className="suggestions">
                  {suggestionsFor(docs).map((s) => (
                    <button key={s} onClick={() => send(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="hint">Start by uploading a PDF, Word, text, or Markdown file in the sidebar.</p>
              )}
            </div>
          ) : (
            messages.map((m) => <ChatMessage key={m.id} message={m} />)
          )}
          <div ref={endRef} />
        </div>
        <Composer busy={busy} onSend={send} onStop={() => abortRef.current?.abort()} />
      </main>
    </div>
  );
}
