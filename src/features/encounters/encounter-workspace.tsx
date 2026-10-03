"use client";

import { FormEvent, useEffect, useState } from "react";
import { ClipboardPlus } from "lucide-react";

type Person = { id: number; given_name: string; family_name: string };
type Encounter = { id: number; patient_id: number; practitioner_id: number; status: string; diagnosis_summary: string; note: string };

export function EncounterWorkspace() {
  const [patients, setPatients] = useState<Person[]>([]);
  const [practitioners, setPractitioners] = useState<Person[]>([]);
  const [rows, setRows] = useState<Encounter[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() {
    const [a, b, c] = await Promise.all([fetch("/api/data/patients"), fetch("/api/data/practitioners"), fetch("/api/data/encounters")]);
    if (!a.ok || !b.ok || !c.ok) throw new Error("Could not load encounter records");
    setPatients(await a.json()); setPractitioners(await b.json()); setRows(await c.json());
  }
  // Initial server data is applied after fetch resolves.
  useEffect(() => { load().catch((reason) => setError(reason.message)); }, []);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const response = await fetch("/api/data/encounters", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not save encounter"); return; }
    event.currentTarget.reset(); await load();
  }
  const name = (id: number, list: Person[]) => list.find((item) => item.id === id);
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Clinical encounters</h2><p>Start a documented encounter for a patient and practitioner.</p></div><span className="record-count">{rows.length} ENCOUNTERS</span></div>
    <form className="record-form encounter-form" onSubmit={create}>
      <label>Patient<select name="patient_id" required defaultValue=""><option value="" disabled>Select patient</option>{patients.map((item) => <option key={item.id} value={item.id}>{item.given_name} {item.family_name}</option>)}</select></label>
      <label>Practitioner<select name="practitioner_id" required defaultValue=""><option value="" disabled>Select practitioner</option>{practitioners.map((item) => <option key={item.id} value={item.id}>{item.given_name} {item.family_name}</option>)}</select></label>
      <label className="wide-field">Diagnosis summary<input name="diagnosis_summary" maxLength={1000} /></label>
      <label className="wide-field">Clinical note<textarea name="note" rows={4} maxLength={10000} placeholder="Document the encounter…" /></label>
      <button className="primary-button" disabled={busy || !patients.length || !practitioners.length}><ClipboardPlus size={15} /> {busy ? "Saving…" : "Start encounter"}</button>
    </form>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="table-wrap"><table><thead><tr><th>Patient</th><th>Practitioner</th><th>Diagnosis summary</th><th>Status</th></tr></thead><tbody>
      {rows.map((item) => <tr key={item.id}><td>{name(item.patient_id, patients)?.given_name ?? "Patient"} {name(item.patient_id, patients)?.family_name ?? ""}</td><td>{name(item.practitioner_id, practitioners)?.given_name ?? "Practitioner"} {name(item.practitioner_id, practitioners)?.family_name ?? ""}</td><td>{item.diagnosis_summary || "—"}</td><td><span className="status-pill"><i /> {item.status}</span></td></tr>)}
      {!rows.length && <tr><td colSpan={4} className="empty-row">No encounter records yet.</td></tr>}
    </tbody></table></div>
  </section>;
}
