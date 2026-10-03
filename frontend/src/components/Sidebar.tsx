import { useState, type DragEvent } from "react";
import { deleteDocument, uploadDocument } from "../api";
import type { DocumentInfo } from "../types";

interface Props {
  docs: DocumentInfo[];
  onChange: () => void;
  onNewChat: () => void;
}

const ACCEPT = [".pdf", ".docx", ".txt", ".md"];

const extension = (name: string) => name.slice(name.lastIndexOf(".")).toLowerCase();

export default function Sidebar({ docs, onChange, onNewChat }: Props) {
  const [status, setStatus] = useState<{ text: string; error?: boolean } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true);
    for (const file of Array.from(files)) {
      if (!ACCEPT.includes(extension(file.name))) {
        setStatus({ text: `${file.name} isn't supported. Use PDF, Word, text, or Markdown.`, error: true });
        continue;
      }
      setStatus({ text: `Indexing ${file.name}…` });
      try {
        const res = await uploadDocument(file);
        setStatus({ text: `Indexed ${res.filename} (${res.chunks} chunks).` });
      } catch (err) {
        setStatus({ text: (err as Error).message, error: true });
        break;
      }
    }
    setUploading(false);
    onChange();
  }

  async function remove(name: string) {
    setConfirming(null);
    try {
      await deleteDocument(name);
      setStatus({ text: `Removed ${name}.` });
    } catch (err) {
      setStatus({ text: `Couldn't remove ${name}: ${(err as Error).message}`, error: true });
    }
    onChange();
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    upload(e.dataTransfer.files);
  }

  return (
    <aside className="sidebar">
      <div className="brand">
        <h1>Knowledge Assistant</h1>
        <button className="ghost" onClick={onNewChat}>New chat</button>
      </div>

      <label
        className={`drop${dragging ? " dragging" : ""}${uploading ? " busy" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          type="file"
          multiple
          accept={ACCEPT.join(",")}
          disabled={uploading}
          onChange={(e) => {
            upload(e.target.files);
            e.target.value = "";
          }}
        />
        <span className="drop-icon" aria-hidden="true">↑</span>
        {uploading ? "Indexing…" : dragging ? "Drop to upload" : "Upload documents"}
        <small>Click or drag files here · PDF, Word, text, Markdown</small>
      </label>
      {status && <p className={status.error ? "status error" : "status"} role="status">{status.text}</p>}

      <h3>
        Knowledge base <span className="count">{docs.length}</span>
      </h3>
      {docs.length === 0 ? (
        <p className="muted">No documents yet. Upload a policy, manual, or report to start.</p>
      ) : (
        <ul className="docs">
          {docs.map((d) => {
            const ext = extension(d.filename).slice(1);
            return (
              <li key={d.filename}>
                <span className={`filetype filetype-${ext}`}>{ext}</span>
                <span className="doc-name" title={d.filename}>
                  {d.filename}
                  <small>
                    {d.pages} page{d.pages === 1 ? "" : "s"} · {d.chunks} chunk{d.chunks === 1 ? "" : "s"}
                  </small>
                </span>
                {confirming === d.filename ? (
                  <span className="confirm">
                    <button className="danger" onClick={() => remove(d.filename)}>Remove</button>
                    <button onClick={() => setConfirming(null)}>Cancel</button>
                  </span>
                ) : (
                  <button onClick={() => setConfirming(d.filename)} aria-label={`Remove ${d.filename}`}>
                    Remove
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </aside>
  );
}
