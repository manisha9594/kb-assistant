import { useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

interface Props {
  busy: boolean;
  onSend: (t: string) => void;
  onStop: () => void;
}

export default function Composer({ busy, onSend, onStop }: Props) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  // Grow with the content up to the CSS max-height.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [text]);

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    onSend(value);
    setText("");
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) submit(e);
  }

  return (
    <form className="composer" onSubmit={submit}>
      <div className="composer-box">
        <textarea
          ref={ref}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          placeholder="Ask a question about your documents"
          aria-label="Your question"
        />
        {busy ? (
          <button type="button" className="primary stop" onClick={onStop}>
            Stop
          </button>
        ) : (
          <button className="primary" disabled={!text.trim()}>
            Send
          </button>
        )}
      </div>
      <p className="composer-hint">Enter to send · Shift+Enter for a new line</p>
    </form>
  );
}
