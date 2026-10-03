"use client";

import { FormEvent, useEffect, useState } from "react";
import { Search, UserPlus } from "lucide-react";

type Patient = { id: number; mrn: string; given_name: string; family_name: string; birth_date: string | null; gender: string; status: string };

export function PatientWorkspace() {
  const [rows, setRows] = useState<Patient[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const response = await fetch("/api/data/patients");
    if (!response.ok) throw new Error("Could not load patient records");
    setRows(await response.json());
  }

  // Initial server data is applied after fetch resolves.
  useEffect(() => { load().catch((reason) => setError(reason.message)); }, []);

  async function addPatient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    const payload = {
      given_name: String(data.get("given_name")),
      family_name: String(data.get("family_name")),
      gender: String(data.get("gender")),
      birth_date: String(data.get("birth_date") ?? "") || null,
      email: String(data.get("email") ?? "") || null,
      phone: String(data.get("phone") ?? "") || null,
    };
    const response = await fetch("/api/data/patients", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not create patient"); return; }
    event.currentTarget.reset();
    await load();
  }

  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Patient directory</h2><p>Patient records for your organization.</p></div><span className="record-count">{rows.length} RECORDS</span></div>
    <form className="record-form" onSubmit={addPatient}>
      <label>First name<input name="given_name" required maxLength={100} /></label><label>Last name<input name="family_name" required maxLength={100} /></label>
      <label>Date of birth<input name="birth_date" type="date" /></label><label>Gender<select name="gender"><option value="unknown">Not specified</option><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option></select></label>
      <label>Email<input name="email" type="email" /></label><label>Phone<input name="phone" type="tel" /></label>
      <button className="primary-button" disabled={busy}><UserPlus size={15} /> {busy ? "Saving…" : "Add patient"}</button>
    </form>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="table-tools"><span><Search size={15} /> Patient records</span></div>
    <div className="table-wrap"><table><thead><tr><th>MRN</th><th>Patient</th><th>Date of birth</th><th>Gender</th><th>Status</th></tr></thead><tbody>
      {rows.map((patient) => <tr key={patient.id}><td className="mono">{patient.mrn}</td><td className="patient-cell"><span>{patient.given_name[0]}{patient.family_name[0]}</span><strong>{patient.given_name} {patient.family_name}</strong></td><td>{patient.birth_date ?? "—"}</td><td>{patient.gender}</td><td><i className="table-dot" /> Active</td></tr>)}
      {!rows.length && <tr><td colSpan={5} className="empty-row">No patient records yet. Add a patient above to begin.</td></tr>}
    </tbody></table></div>
  </section>;
}
