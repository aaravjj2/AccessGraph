import { useEffect, useRef, useState } from "react";
import { Bot, ChevronRight, FileText, Send, Sparkles, X } from "lucide-react";
import type { CaseAssistantResponse } from "../lib/contracts";

type Message = {
  id: string;
  role: "agent" | "user";
  text: string;
  citations?: string[];
  disclaimer?: string;
};

const starterQuestions = [
  "What is blocking this case?",
  "What does the cost estimate mean?",
  "Which sources support the findings?",
];

const makeMessage = (role: Message["role"], text: string, response?: CaseAssistantResponse): Message => ({
  id: crypto.randomUUID(),
  role,
  text,
  citations: response?.citations,
  disclaimer: response?.disclaimer,
});

export function CaseSideAgent({
  open,
  onClose,
  onAsk,
}: {
  open: boolean;
  onClose: () => void;
  onAsk: (question: string) => Promise<CaseAssistantResponse>;
}) {
  const [messages, setMessages] = useState<Message[]>([makeMessage("agent", "I’m the AccessGraph Case Guide. Ask about the current case, evidence, cost estimate, or the next best action.")]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  async function send(question: string) {
    const value = question.trim();
    if (!value || sending) return;
    setMessages(current => [...current, makeMessage("user", value)]);
    setDraft("");
    setSending(true);
    try {
      const response = await onAsk(value);
      setMessages(current => [...current, makeMessage("agent", response.answer, response)]);
    } catch {
      setMessages(current => [...current, makeMessage("agent", "I couldn’t reach the case guide. Check the Orchestrator connection and try again.")]);
    } finally {
      setSending(false);
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }

  if (!open) return null;
  return <>
    <button className="assistant-scrim" aria-label="Close Case Guide" onClick={onClose} />
    <aside className="case-side-agent" role="dialog" aria-modal="true" aria-label="AccessGraph Case Guide">
      <header className="assistant-header">
        <div className="assistant-avatar"><Bot size={20} /></div>
        <div><span className="eyebrow">SIDE AGENT</span><h2>Case Guide</h2><p>Grounded in this case’s available findings.</p></div>
        <button className="icon-button" aria-label="Close Case Guide" onClick={onClose}><X size={20} /></button>
      </header>
      <div className="assistant-context"><Sparkles size={15} /><span>Case-aware guidance, with no approval promises.</span></div>
      <div className="assistant-messages" aria-live="polite">
        {messages.map(message => <div className={`assistant-message ${message.role}`} key={message.id}>
          {message.role === "agent" ? <Bot size={15} /> : null}
          <div><p>{message.text}</p>{message.citations?.length ? <div className="assistant-citations"><FileText size={13} /><span>{message.citations.join(" · ")}</span></div> : null}{message.disclaimer ? <p className="assistant-disclaimer">{message.disclaimer}</p> : null}</div>
        </div>)}
        {sending ? <div className="assistant-message agent"><Bot size={15} /><div className="assistant-typing"><i /><i /><i /></div></div> : null}
      </div>
      <div className="assistant-suggestions"><span>Try asking</span><div>{starterQuestions.map(question => <button key={question} disabled={sending} onClick={() => void send(question)}>{question}<ChevronRight size={14} /></button>)}</div></div>
      <form className="assistant-composer" onSubmit={event => { event.preventDefault(); void send(draft); }}>
        <label className="sr-only" htmlFor="case-guide-question">Ask the Case Guide</label>
        <input id="case-guide-question" ref={inputRef} value={draft} maxLength={1200} disabled={sending} onChange={event => setDraft(event.target.value)} placeholder="Ask about this case…" />
        <button type="submit" className="assistant-send" disabled={!draft.trim() || sending} aria-label="Send question"><Send size={17} /></button>
      </form>
      <p className="assistant-footnote">Synthetic case guidance only. Keep clinical judgment and payer review at the center.</p>
    </aside>
  </>;
}
