"use client";

import { FormEvent, useEffect, useState } from "react";
import { Plus, Stethoscope, Trash2, UserPlus } from "lucide-react";

type Practitioner = { id: number; given_name: string; family_name: string; specialty: string; email: string; phone: string | null; role: string; status: string };
type MemberDraft = { given_name: string; family_name: string; role: string; specialty: string; email: string; phone: string };
const emptyMember = (): MemberDraft => ({ given_name: "", family_name: "", role: "Practitioner", specialty: "", email: "", phone: "" });

export function PractitionerWorkspace() {
  const [rows, setRows] = useState<Practitioner[]>([]);
  const [drafts, setDrafts] = useState<MemberDraft[]>([emptyMember()]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() {
    const response = await fetch("/api/data/practitioners");
    if (!response.ok) throw new Error("Could not load care team");
    setRows(await response.json());
  }
  useEffect(() => { load().catch((reason) => setError(reason.message)); }, []);
  function update(index: number, key: keyof MemberDraft, value: string) {
    setDrafts((current) => current.map((draft, i) => i === index ? { ...draft, [key]: value } : draft));
  }
  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const response = await fetch("/api/data/practitioners/bulk", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ practitioners: drafts.map((draft) => ({ ...draft, phone: draft.phone || null })) }) });
      if (!response.ok) { const result = await response.json(); throw new Error(result.detail ?? "Could not add care team members"); }
      setDrafts([emptyMember()]); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not add care team members"); await load().catch(() => undefined); }
    finally { setBusy(false); }
  }
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Practitioner directory</h2><p>Add one or several care team profiles at once.</p></div><span className="record-count">{rows.length} MEMBERS</span></div>
    <form className="record-form member-form" onSubmit={add}>
      {drafts.map((draft, index) => <div className="member-draft" key={index}>
        <div className="member-draft-heading"><strong>Person {index + 1}</strong>{drafts.length > 1 && <button type="button" className="quiet-button remove-member" onClick={() => setDrafts((items) => items.filter((_, i) => i !== index))} aria-label={`Remove person ${index + 1}`}><Trash2 size={14} /></button>}</div>
        <label>First name<input required value={draft.given_name} onChange={(e) => update(index, "given_name", e.target.value)} /></label>
        <label>Last name<input required value={draft.family_name} onChange={(e) => update(index, "family_name", e.target.value)} /></label>
        <label>Role<select value={draft.role} onChange={(e) => update(index, "role", e.target.value)}><option>Practitioner</option><option>Physician</option><option>Nurse</option><option>Medical assistant</option><option>Administrator</option><option>Other</option></select></label>
        <label>Specialty<input placeholder="Family medicine" required value={draft.specialty} onChange={(e) => update(index, "specialty", e.target.value)} /></label>
        <label>Work email<input type="email" required value={draft.email} onChange={(e) => update(index, "email", e.target.value)} /></label>
        <label>Contact number<input type="tel" value={draft.phone} onChange={(e) => update(index, "phone", e.target.value)} /></label>
      </div>)}
      <div className="member-form-actions"><button type="button" className="secondary-button" onClick={() => setDrafts((items) => [...items, emptyMember()])}><Plus size={14} /> Add another person</button><button className="primary-button" disabled={busy}><UserPlus size={15} /> {busy ? "Saving…" : `Save ${drafts.length > 1 ? "people" : "person"}`}</button></div>
    </form>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="table-wrap"><table><thead><tr><th>Care team member</th><th>Role</th><th>Specialty</th><th>Email</th><th>Contact</th><th>Status</th></tr></thead><tbody>
      {rows.map((doctor) => <tr key={doctor.id}><td className="patient-cell"><span><Stethoscope size={14} /></span><strong>{doctor.given_name} {doctor.family_name}</strong></td><td>{doctor.role}</td><td>{doctor.specialty}</td><td>{doctor.email}</td><td>{doctor.phone || "—"}</td><td><i className="table-dot" /> Active</td></tr>)}
      {!rows.length && <tr><td colSpan={6} className="empty-row">No practitioners yet. Add a care team member above.</td></tr>}
    </tbody></table></div>
  </section>;
}
