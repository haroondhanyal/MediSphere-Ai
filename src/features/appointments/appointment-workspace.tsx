"use client";

import { FormEvent, useEffect, useState } from "react";
import { CalendarPlus } from "lucide-react";

type Person = { id: number; given_name: string; family_name: string };
type Appointment = { id: number; patient_id: number; practitioner_id: number; starts_at: string; ends_at: string; status: string; reason: string };

export function AppointmentWorkspace() {
  const [patients, setPatients] = useState<Person[]>([]);
  const [practitioners, setPractitioners] = useState<Person[]>([]);
  const [rows, setRows] = useState<Appointment[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const [patientResponse, practitionerResponse, appointmentResponse] = await Promise.all([
      fetch("/api/data/patients"), fetch("/api/data/practitioners"), fetch("/api/data/appointments"),
    ]);
    if (!patientResponse.ok || !practitionerResponse.ok || !appointmentResponse.ok) throw new Error("Could not load scheduling data");
    setPatients(await patientResponse.json()); setPractitioners(await practitionerResponse.json()); setRows(await appointmentResponse.json());
  }
  // Initial server data is applied after fetch resolves.
  useEffect(() => { load().catch((reason) => setError(reason.message)); }, []);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    const start = new Date(String(data.get("starts_at")));
    const end = new Date(String(data.get("ends_at")));
    const response = await fetch("/api/data/appointments", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_id: Number(data.get("patient_id")), practitioner_id: Number(data.get("practitioner_id")), starts_at: start.toISOString(), ends_at: end.toISOString(), reason: data.get("reason") }),
    });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not create appointment"); return; }
    event.currentTarget.reset(); await load();
  }
  const patientName = (id: number) => patients.find((item) => item.id === id);
  const practitionerName = (id: number) => practitioners.find((item) => item.id === id);

  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Appointment schedule</h2><p>Book visits with organization patients and practitioners.</p></div><span className="record-count">{rows.length} VISITS</span></div>
    <form className="record-form appointment-form" onSubmit={create}>
      <label>Patient<select name="patient_id" required defaultValue=""><option value="" disabled>Select patient</option>{patients.map((item) => <option key={item.id} value={item.id}>{item.given_name} {item.family_name}</option>)}</select></label>
      <label>Practitioner<select name="practitioner_id" required defaultValue=""><option value="" disabled>Select practitioner</option>{practitioners.map((item) => <option key={item.id} value={item.id}>{item.given_name} {item.family_name}</option>)}</select></label>
      <label>Starts<input name="starts_at" type="datetime-local" required /></label><label>Ends<input name="ends_at" type="datetime-local" required /></label>
      <label className="wide-field">Visit reason<input name="reason" maxLength={500} placeholder="Reason for visit" /></label>
      <button className="primary-button" disabled={busy || !patients.length || !practitioners.length}><CalendarPlus size={15} /> {busy ? "Booking…" : "Book appointment"}</button>
    </form>
    {(!patients.length || !practitioners.length) && <p className="muted form-hint">Add at least one patient and practitioner before booking.</p>}
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="table-wrap"><table><thead><tr><th>Patient</th><th>Practitioner</th><th>Start time</th><th>Reason</th><th>Status</th></tr></thead><tbody>
      {rows.map((visit) => <tr key={visit.id}><td>{patientName(visit.patient_id)?.given_name ?? "Patient"} {patientName(visit.patient_id)?.family_name ?? ""}</td><td>{practitionerName(visit.practitioner_id)?.given_name ?? "Practitioner"} {practitionerName(visit.practitioner_id)?.family_name ?? ""}</td><td>{new Date(visit.starts_at).toLocaleString()}</td><td>{visit.reason || "—"}</td><td><span className="status-pill"><i /> {visit.status}</span></td></tr>)}
      {!rows.length && <tr><td colSpan={5} className="empty-row">No appointments scheduled.</td></tr>}
    </tbody></table></div>
  </section>;
}
