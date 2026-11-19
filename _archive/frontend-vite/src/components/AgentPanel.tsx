import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { ChatMessage, CMARequest } from "../types";

const SUGGESTIONS = [
  "Why were these comps chosen, and which is the weakest?",
  "Walk me through how the estimate was calculated.",
  "What does the county record say about condition, and what should be inspected?",
  "Did any filter limit the search?",
];

export function AgentPanel({ req, enabled, model }: { req: CMARequest; enabled: boolean; model: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => setMessages([]), [req.subject_pin]);
  useEffect(() => endRef.current?.scrollIntoView({ block: "end" }), [messages]);

  if (!enabled) {
    return (
      <div className="panel-body">
        <p className="callout">
          The AI assistant is not configured. Add <code>ANTHROPIC_API_KEY</code> to the server's <code>.env</code> and
          restart the backend. Search, ranking, pricing and reports work without it.
        </p>
      </div>
    );
  }

  const send = async (text: string) => {
    if (!text.trim() || busy) return;
    const next: ChatMessage[] = [...messages, { role: "user", content: text.trim() }];
    setMessages(next);
    setInput("");
    setBusy(true);
    setError("");
    try {
      const r = await api.chat(req, next.map(({ role, content }) => ({ role, content })));
      setMessages([...next, { role: "assistant", content: r.reply, tool_calls: r.tool_calls }]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel-body chat">
      <p className="muted small">
        The assistant ({model}) reads the computed facts, comps and valuation through tools and explains them. It does
        not change the figures.
      </p>
      <div className="chat-log" aria-live="polite">
        {messages.length === 0 && (
          <div className="suggestions">
            {SUGGESTIONS.map((s) => (
              <button type="button" className="secondary" key={s} onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg msg-${m.role}`}>
            <div className="pre">{m.content}</div>
            {m.tool_calls && m.tool_calls.length > 0 && (
              <div className="tools small muted">Read: {m.tool_calls.map((t) => t.tool.replace(/_/g, " ")).join(", ")}</div>
            )}
          </div>
        ))}
        {busy && <div className="msg msg-assistant muted">Reading the CMA…</div>}
        <div ref={endRef} />
      </div>
      {error && <p className="warn">{error}</p>}
      <form
        className="chat-form"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <label className="sr-only" htmlFor="chat-in">Ask about this CMA</label>
        <input id="chat-in" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about this CMA…" disabled={busy} />
        <button type="submit" disabled={busy || !input.trim()}>Ask</button>
      </form>
    </div>
  );
}
