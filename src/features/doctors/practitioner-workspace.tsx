"use client";

import { FormEvent, useEffect, useState } from "react";
import { Stethoscope, UserPlus } from "lucide-react";

type Practitioner = { id: number; given_name: string; family_name: string; specialty: string; email: string; status: string };

export function PractitionerWorkspace() {
  const [rows, setRows] = useState<Practitioner[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() {
    const response = await fetch("/api/data/practitioners");
    if (!response.ok) throw new Error("Could not load care team");
    setRows(await response.json());
  }
  // Initial server data is applied after fetch resolves.
  useEffect(() => { load().catch((reason) => setError(reason.message)); }, []);
  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const response = await fetch("/api/data/practitioners", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not add practitioner"); return; }
    event.currentTarget.reset(); await load();
  }
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Practitioner directory</h2><p>Care team members for your organization.</p></div><span className="record-count">{rows.length} MEMBERS</span></div>
    <form className="record-form" onSubmit={add}>
      <label>First name<input name="given_name" required /></label><label>Last name<input name="family_name" required /></label>
      <label>Specialty<input name="specialty" placeholder="Family medicine" required /></label><label>Work email<input name="email" type="email" required /></label>
      <button className="primary-button" disabled={busy}><UserPlus size={15} /> {busy ? "Saving…" : "Add practitioner"}</button>
    </form>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="table-wrap"><table><thead><tr><th>Care team member</th><th>Specialty</th><th>Email</th><th>Status</th></tr></thead><tbody>
      {rows.map((doctor) => <tr key={doctor.id}><td className="patient-cell"><span><Stethoscope size={14} /></span><strong>{doctor.given_name} {doctor.family_name}</strong></td><td>{doctor.specialty}</td><td>{doctor.email}</td><td><i className="table-dot" /> Active</td></tr>)}
      {!rows.length && <tr><td colSpan={4} className="empty-row">No practitioners yet. Add a care team member above.</td></tr>}
    </tbody></table></div>
  </section>;
}
