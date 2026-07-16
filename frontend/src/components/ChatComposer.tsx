import { useRef, type FormEvent, type KeyboardEvent } from "react";

export function ChatComposer({value, loading, onChange, onSubmit}: {
  value: string; loading: boolean;
  onChange: (value: string) => void; onSubmit: () => void;
}) {
  const form = useRef<HTMLFormElement>(null);
  const composing = useRef(false);
  function submit(e: FormEvent) {
    e.preventDefault();
    if (!loading && value.trim()) onSubmit();
  }
  function keyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !composing.current &&
        !e.nativeEvent.isComposing && !loading) {
      e.preventDefault();
      form.current?.requestSubmit();
    }
  }
  return <form className="composer" ref={form} onSubmit={submit}>
    <label htmlFor="chat-message">Message</label>
    <div className="controls">
      <textarea id="chat-message" value={value} rows={3} maxLength={4000}
        placeholder="Ask a read-only operations question…" disabled={loading}
        aria-describedby="composer-help"
        onChange={(e) => onChange(e.target.value)} onKeyDown={keyDown}
        onCompositionStart={() => { composing.current = true; }}
        onCompositionEnd={() => { composing.current = false; }} />
      <button type="submit" disabled={loading || !value.trim()}>
        {loading ? "Sending…" : "Send"}
      </button>
    </div>
    <p id="composer-help" className="help">Enter sends. Shift+Enter adds a new line.</p>
  </form>;
}
