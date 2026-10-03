import { Fragment, useState, type ReactNode } from "react";
import type { Message, Route, Source } from "../types";

const ROUTE_LABEL: Record<Route, string> = {
  retrieve: "Searched your documents",
  web_search: "Searched the web",
  clarify: "Needs more detail",
};

/** Turn "[1]" markers into clickable highlighter marks, plus **bold** and `code`. */
function inline(text: string, onCite: (id: number) => void): ReactNode[] {
  return text.split(/(\[\d+\]|\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) => {
    const cite = part.match(/^\[(\d+)\]$/);
    if (cite) {
      return (
        <button key={i} className="cite" onClick={() => onCite(Number(cite[1]))} aria-label={`Show source ${cite[1]}`}>
          {cite[1]}
        </button>
      );
    }
    if (/^\*\*[^*]+\*\*$/.test(part)) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (/^`[^`]+`$/.test(part)) return <code key={i}>{part.slice(1, -1)}</code>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}

const BULLET = /^\s*[-*]\s+/;
const NUMBERED = /^\s*\d+[.)]\s+/;
const HEADING = /^#{1,6}\s+/;

/** Minimal markdown: headings, paragraphs, bulleted and numbered lists. */
function Answer({ text, onCite }: { text: string; onCite: (id: number) => void }) {
  const blocks = text.split(/\n{2,}/).filter((b) => b.trim());
  return (
    <>
      {blocks.map((block, i) => {
        const lines = block.split("\n").filter((l) => l.trim());
        if (lines.length === 1 && HEADING.test(lines[0])) {
          return <h4 key={i}>{inline(lines[0].replace(HEADING, ""), onCite)}</h4>;
        }
        for (const [re, List] of [[BULLET, "ul"], [NUMBERED, "ol"]] as const) {
          if (lines.every((l) => re.test(l))) {
            return (
              <List key={i}>
                {lines.map((l, j) => <li key={j}>{inline(l.replace(re, ""), onCite)}</li>)}
              </List>
            );
          }
        }
        return <p key={i}>{inline(block, onCite)}</p>;
      })}
    </>
  );
}

function SourceItem({ s, lit }: { s: Source; lit: boolean }) {
  return (
    <li id={`src-${s.id}`} className={lit ? "source lit" : "source"}>
      <div className="source-head">
        <b>
          [{s.id}]{" "}
          {s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.source}</a> : s.source}
          {s.kind !== "web" && s.page && <span className="muted">, page {s.page}</span>}
        </b>
        {s.score != null && <span className="score" title="Relevance">{Math.round(s.score * 100)}% match</span>}
      </div>
      <p>{s.snippet}…</p>
    </li>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked; nothing useful to do */
    }
  }
  return (
    <button className="ghost small" onClick={copy}>
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export default function ChatMessage({ message: m }: { message: Message }) {
  const [open, setOpen] = useState(false);
  const [lit, setLit] = useState<number | null>(null);

  if (m.role === "user") return <div className="msg user">{m.content}</div>;

  const sources = m.sources ?? [];
  const cite = (id: number) => {
    setOpen(true);
    setLit(id);
    requestAnimationFrame(() =>
      document.getElementById(`src-${id}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" }),
    );
  };

  return (
    <div className={m.error ? "msg assistant error" : "msg assistant"}>
      {m.route && (
        <div className={`route route-${m.route}`} title={m.routeReason}>
          {m.fellBack ? "No match in your documents, searched the web" : ROUTE_LABEL[m.route]}
        </div>
      )}
      <div className="answer" aria-live={m.pending ? "polite" : undefined}>
        {m.content ? (
          <Answer text={m.content} onCite={cite} />
        ) : (
          m.pending && (
            <p className="typing" aria-label="Thinking">
              <span /><span /><span />
            </p>
          )
        )}
        {m.stopped && <p className="muted stopped">Stopped.</p>}
      </div>
      {!m.pending && (sources.length > 0 || m.content) && !m.error && (
        <div className="actions">
          {sources.length > 0 && (
            <button className="ghost small" onClick={() => setOpen(!open)} aria-expanded={open}>
              {open ? "Hide" : "Show"} {sources.length} source{sources.length > 1 ? "s" : ""}
            </button>
          )}
          {m.content && <CopyButton text={m.content} />}
        </div>
      )}
      {open && sources.length > 0 && (
        <ol className="sources">{sources.map((s) => <SourceItem key={s.id} s={s} lit={lit === s.id} />)}</ol>
      )}
    </div>
  );
}
