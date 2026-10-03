"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { FlaskConical, Pill, ScanLine } from "lucide-react";

type Person = { id: number; given_name: string; family_name: string };
type Order = { id: number; patient_id: number; practitioner_id: number; status: string; [key: string]: string | number };
type Kind = "prescription" | "lab" | "radiology";

function useOrderData(endpoint: string) {
  const [patients, setPatients] = useState<Person[]>([]);
  const [practitioners, setPractitioners] = useState<Person[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    const [p, d, o] = await Promise.all([fetch("/api/data/patients"), fetch("/api/data/practitioners"), fetch("/api/data/" + endpoint)]);
    if (!p.ok || !d.ok || !o.ok) throw new Error("Could not load clinical orders");
    setPatients(await p.json()); setPractitioners(await d.json()); setOrders(await o.json());
  }, [endpoint]);
  // Initial server data is applied after fetch resolves.
  useEffect(() => { load().catch((reason) => setError(reason.message)); }, [load]);
  return { patients, practitioners, orders, error, setError, load };
}

function PersonFields({ patients, practitioners }: { patients: Person[]; practitioners: Person[] }) {
  return <>
    <label>Patient<select name="patient_id" required defaultValue=""><option value="" disabled>Select patient</option>{patients.map((item) => <option key={item.id} value={item.id}>{item.given_name} {item.family_name}</option>)}</select></label>
    <label>Practitioner<select name="practitioner_id" required defaultValue=""><option value="" disabled>Select practitioner</option>{practitioners.map((item) => <option key={item.id} value={item.id}>{item.given_name} {item.family_name}</option>)}</select></label>
  </>;
}

function ClinicalOrderWorkspace({ kind }: { kind: Kind }) {
  const endpoint = kind === "prescription" ? "prescriptions" : kind === "lab" ? "lab-orders" : "radiology-orders";
  const data = useOrderData(endpoint);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState("");
  const [summary, setSummary] = useState("");
  const labels = kind === "prescription"
    ? { title: "Prescriptions", subtitle: "Medication orders for organization patients.", action: "Issue prescription", icon: Pill }
    : kind === "lab"
      ? { title: "Lab orders", subtitle: "Order tests and record completed results.", action: "Place lab order", icon: FlaskConical }
      : { title: "Imaging orders", subtitle: "Request imaging and record radiology reports.", action: "Place imaging order", icon: ScanLine };
  const Icon = labels.icon;
  const patientName = (id: number) => data.patients.find((person) => person.id === id);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); data.setError("");
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form);
    if (kind === "prescription") payload.dosage = String(form.get("dosage"));
    const response = await fetch("/api/data/" + endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); data.setError(result.detail ?? "Could not save order"); return; }
    event.currentTarget.reset(); await data.load();
  }
  async function recordResult(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); data.setError("");
    const path = kind === "lab" ? "lab-orders/" + selected + "/result" : "radiology-orders/" + selected + "/report";
    const response = await fetch("/api/data/" + path, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ summary }) });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); data.setError(result.detail ?? "Could not save report"); return; }
    setSelected(""); setSummary(""); await data.load();
  }
  const canReport = kind !== "prescription";
  const fields = kind === "prescription"
    ? <><label>Medication<input name="medication_name" required /></label><label>Dosage<input name="dosage" required /></label><label>Frequency<input name="frequency" placeholder="Twice daily" required /></label><label>Duration<input name="duration" placeholder="7 days" /></label><label className="wide-field">Instructions<input name="instructions" /></label></>
    : kind === "lab"
      ? <><label>Test name<input name="test_name" required placeholder="Complete blood count" /></label><label>Priority<select name="priority"><option value="routine">Routine</option><option value="urgent">Urgent</option><option value="stat">STAT</option></select></label></>
      : <><label>Modality<select name="modality"><option>X-Ray</option><option>CT</option><option>MRI</option><option>Ultrasound</option></select></label><label>Body region<input name="body_region" required placeholder="Chest" /></label></>;

  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>{labels.title}</h2><p>{labels.subtitle}</p></div><span className="record-count">{data.orders.length} ORDERS</span></div>
    <form className="record-form" onSubmit={create}><PersonFields patients={data.patients} practitioners={data.practitioners} />{fields}<button className="primary-button" disabled={busy || !data.patients.length || !data.practitioners.length}><Icon size={15} /> {busy ? "Saving…" : labels.action}</button></form>
    {!data.patients.length || !data.practitioners.length ? <p className="muted form-hint">Add a patient and care team member before placing orders.</p> : null}
    {canReport && <form className="record-form report-form" onSubmit={recordResult}>
      <label>Order<select value={selected} onChange={(event) => setSelected(event.target.value)} required><option value="" disabled>Select an open order</option>{data.orders.filter((order) => order.status === "ordered").map((order) => <option key={order.id} value={order.id}>#{order.id} · {patientName(order.patient_id)?.given_name ?? "Patient"} · {String(order.test_name ?? order.body_region)}</option>)}</select></label>
      <label className="wide-field">{kind === "lab" ? "Result summary" : "Report summary"}<textarea rows={2} value={summary} onChange={(event) => setSummary(event.target.value)} required maxLength={4000} /></label>
      <button className="primary-button" disabled={busy || !selected}>Record {kind === "lab" ? "result" : "report"}</button>
    </form>}
    {data.error && <p className="form-error panel-error" role="alert">{data.error}</p>}
    <div className="table-wrap"><table><thead><tr><th>Patient</th><th>{kind === "prescription" ? "Medication" : kind === "lab" ? "Test" : "Modality"}</th><th>Details</th>{canReport && <th>Result / report</th>}<th>Status</th></tr></thead><tbody>
      {data.orders.map((order) => <tr key={order.id}><td>{patientName(order.patient_id)?.given_name ?? "Patient"} {patientName(order.patient_id)?.family_name ?? ""}</td>
        <td>{String(order.medication_name ?? order.test_name ?? order.modality)}</td>
        <td>{kind === "prescription" ? String(order.dosage) + " · " + String(order.frequency) : kind === "lab" ? String(order.priority) : String(order.body_region)}</td>
        {canReport && <td>{String(order.result_summary ?? order.report_summary ?? "—")}</td>}
        <td><span className="status-pill"><i /> {order.status}</span></td></tr>)}
      {!data.orders.length && <tr><td colSpan={canReport ? 5 : 4} className="empty-row">No orders yet.</td></tr>}
    </tbody></table></div>
  </section>;
}

export function PrescriptionWorkspace() { return <ClinicalOrderWorkspace kind="prescription" />; }
export function LabWorkspace() { return <ClinicalOrderWorkspace kind="lab" />; }
export function RadiologyWorkspace() { return <ClinicalOrderWorkspace kind="radiology" />; }
