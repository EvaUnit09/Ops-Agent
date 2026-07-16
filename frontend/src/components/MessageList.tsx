import { useEffect, useRef } from "react";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  softLimitReached?: boolean;
}
export function MessageList({messages, loading}: {
  messages: ChatMessage[]; loading: boolean;
}) {
  const end = useRef<HTMLLIElement>(null);
  useEffect(() => end.current?.scrollIntoView({block: "nearest"}), [messages, loading]);
  if (!messages.length) return <div className="empty">
    <p>Ask about assets, stale inventory, users, or checkout history.</p>
    <p>Try “Find LT-100” or “What is checked out to Maya?”</p>
  </div>;
  return <ol className="messages" aria-label="Conversation" aria-live="polite"
    aria-relevant="additions" aria-busy={loading}>
    {messages.map((m) => <li className={`message ${m.role}`} key={m.id}>
      <span className="label">{m.role === "user" ? "You" : "Ops Agent"}</span>
      <p>{m.text}</p>
      {m.softLimitReached && <p className="note">
        The agent reached its tool-use limit and returned its best available answer.
      </p>}
    </li>)}
    {loading && <li className="thinking" role="status">
      <span aria-hidden="true" />Ops Agent is working…
    </li>}
    <li ref={end} aria-hidden="true" />
  </ol>;
}
