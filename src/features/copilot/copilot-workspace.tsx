"use client";

import { FormEvent, useState } from "react";
import { Search, Sparkles } from "lucide-react";

type Source = Record<string, string | number>;
type Turn = { question: string; answer: string; category: string; sources: Source[] };
const prompts = ["Find patient records for", "Show recent appointments", "List recent prescriptions", "Show recent claims", "Give organization summary"];

export function CopilotWorkspace() {
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = query.trim();
    if (!question || busy) return;
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/data/ai/copilot", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: question }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not search workspace records");
      setTurns((previous) => [{ question, ...result }, ...previous]);
      setQuery("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not search workspace records"); }
    finally { setBusy(false); }
  }
  return <section className="workspace-panel copilot-panel">
    <div className="notice copilot-notice"><span className="notice-mark"><Sparkles size={13} /></span><span><strong>Private, permission-aware retrieval</strong><small>Searches records inside your organization and only returns data allowed by your role. It does not generate clinical advice.</small></span></div>
    <div className="copilot-prompts">{prompts.map((prompt) => <button type="button" key={prompt} onClick={() => setQuery(prompt)}>{prompt}</button>)}</div>
    <form className="copilot-form" onSubmit={ask}><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} maxLength={500} placeholder="Ask about patients, appointments, prescriptions, claims…" aria-label="Search MediSphere records" /><button className="primary-button" disabled={busy || query.trim().length < 2}><Sparkles size={15} /> {busy ? "Searching…" : "Search"}</button></form>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="copilot-results">{turns.map((turn, index) => <article className="copilot-result" key={`${turn.category}-${index}`}><div className="copilot-question">{turn.question}</div><div className="copilot-answer"><strong>{turn.answer}</strong><span className="record-count">{turn.category.toUpperCase()}</span></div>{turn.sources.length > 0 && <div className="table-wrap"><table><thead><tr>{Object.keys(turn.sources[0]).map((key) => <th key={key}>{key.replaceAll("_", " ").toUpperCase()}</th>)}</tr></thead><tbody>{turn.sources.map((row, rowIndex) => <tr key={rowIndex}>{Object.values(row).map((value, cellIndex) => <td key={cellIndex}>{String(value)}</td>)}</tr>)}</tbody></table></div>}</article>)}{!turns.length && <div className="copilot-empty"><span className="empty-icon"><Sparkles size={20} /></span><h2>What would you like to find?</h2><p>Ask for records and summaries available to your account.</p></div>}</div>
  </section>;
}
