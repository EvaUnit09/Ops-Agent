import { useEffect, useRef, useState } from "react";
import { postChat } from "./api";
import { ChatComposer } from "./components/ChatComposer";
import { MessageList, type ChatMessage } from "./components/MessageList";
import { getThreadId } from "./thread";

export default function App() {
  const [threadId] = useState(() => getThreadId());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);

  async function send() {
    const message = draft.trim();
    if (!message || loading) return;
    setMessages((v) => [...v, {id: crypto.randomUUID(), role: "user", text: message}]);
    setDraft(""); setError(null); setLoading(true);
    const controller = new AbortController(); active.current = controller;
    try {
      const result = await postChat({message, thread_id: threadId}, controller.signal);
      setMessages((v) => [...v, {
        id: crypto.randomUUID(), role: "assistant", text: result.answer,
        softLimitReached: result.soft_limit_reached,
      }]);
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") return;
      setError(caught instanceof Error ? caught.message : "An unexpected error occurred.");
    } finally {
      if (active.current === controller) {
        active.current = null; setLoading(false);
      }
    }
  }

  return <main className="shell"><section className="card" aria-labelledby="title">
    <header><div><p className="eyebrow">Read-only asset assistant</p>
      <h1 id="title">Ops Agent</h1></div></header>
    <div className="transcript"><MessageList messages={messages} loading={loading} /></div>
    {error && <div className="error" role="alert">
      <strong>Message not completed.</strong><span>{error}</span>
    </div>}
    <ChatComposer value={draft} loading={loading} onChange={setDraft} onSubmit={send} />
  </section></main>;
}
