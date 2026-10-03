"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { CreditCard, FileCheck2, Plus, ShieldCheck, WalletCards } from "lucide-react";

type Patient = { id: number; given_name: string; family_name: string };
type Row = { id: number; patient_id: number; status: string; [key: string]: string | number };
type Kind = "insurance" | "claims" | "authorizations" | "billing";
const endpoints = { insurance: "insurance/policies", claims: "claims", authorizations: "authorizations", billing: "billing/invoices" };
const titles = { insurance: "Insurance coverage", claims: "Insurance claims", authorizations: "Prior authorization requests", billing: "Invoices and payments" };

function Workspace({ kind }: { kind: Kind }) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    const [p, r] = await Promise.all([fetch("/api/data/patients"), fetch("/api/data/" + endpoints[kind])]);
    if (!p.ok || !r.ok) throw new Error("Could not load records");
    setPatients(await p.json()); setRows(await r.json());
  }, [kind]);
  // Initial server data is applied after fetch resolves.
  useEffect(() => { load().catch((reason) => setError(reason.message)); }, [load]);
  const patientName = (id: number) => {
    const patient = patients.find((item) => item.id === id);
    return patient ? patient.given_name + " " + patient.family_name : "Patient";
  };
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setBusy(true);
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form);
    if (kind === "claims" || kind === "billing") {
      payload.patient_id = String(Number(form.get("patient_id")));
      payload.amount_cents = String(Math.round(Number(form.get("amount")) * 100));
      delete payload.amount;
    }
    const response = await fetch("/api/data/" + endpoints[kind], { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not save record"); return; }
    event.currentTarget.reset(); await load();
  }
  async function update(path: string, status: string) {
    const response = await fetch("/api/data/" + path, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not update status"); return; }
    await load();
  }
  async function payment(row: Row) {
    const raw = window.prompt("Manual payment amount in dollars");
    if (!raw) return;
    const amount_cents = Math.round(Number(raw) * 100);
    if (!Number.isFinite(amount_cents) || amount_cents <= 0) { setError("Enter a positive amount"); return; }
    const response = await fetch("/api/data/billing/invoices/" + row.id + "/payments", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ amount_cents, method: "manual" }) });
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not record payment"); return; }
    await load();
  }
  const icon = kind === "insurance" ? <ShieldCheck size={15} /> : kind === "claims" ? <FileCheck2 size={15} /> : kind === "authorizations" ? <Plus size={15} /> : <WalletCards size={15} />;
  const claimNext: Record<string, string> = { draft: "submitted", submitted: "in_review", in_review: "approved", approved: "paid" };
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>{titles[kind]}</h2><p>Manage organization coverage and revenue-cycle records.</p></div><span className="record-count">{rows.length} RECORDS</span></div>
    {kind === "billing" && <div className="notice"><span className="notice-mark">i</span><span><strong>Manual payment ledger</strong><small>Payment processor is not connected; entries record offline payments only.</small></span></div>}
    <form className="record-form" onSubmit={create}>
      <label>Patient<select name="patient_id" required defaultValue=""><option value="" disabled>Select patient</option>{patients.map((item) => <option key={item.id} value={item.id}>{item.given_name} {item.family_name}</option>)}</select></label>
      {kind === "insurance" && <><label>Payer<input name="payer_name" required /></label><label>Member ID<input name="member_id" required /></label><label>Plan name<input name="plan_name" /></label></>}
      {kind === "claims" && <><label>Payer<input name="payer_name" required /></label><label>Amount ($)<input name="amount" type="number" min="0.01" step="0.01" required /></label></>}
      {kind === "authorizations" && <><label>Payer<input name="payer_name" required /></label><label>Service<input name="service_name" required /></label></>}
      {kind === "billing" && <><label>Description<input name="description" required /></label><label>Amount ($)<input name="amount" type="number" min="0.01" step="0.01" required /></label></>}
      <button className="primary-button" disabled={busy || !patients.length}>{icon} {busy ? "Saving…" : kind === "insurance" ? "Add coverage" : kind === "claims" ? "Create claim" : kind === "authorizations" ? "Request authorization" : "Create invoice"}</button>
    </form>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="table-wrap"><table>
      <thead>{kind === "insurance" ? <tr><th>Patient</th><th>Payer</th><th>Plan</th><th>Member ID</th><th>Status</th></tr> : kind === "claims" ? <tr><th>Claim</th><th>Patient</th><th>Payer</th><th>Amount</th><th>Status</th><th>Action</th></tr> : kind === "authorizations" ? <tr><th>Patient</th><th>Payer</th><th>Service</th><th>Status</th><th>Action</th></tr> : <tr><th>Invoice</th><th>Patient</th><th>Description</th><th>Amount</th><th>Paid</th><th>Status</th><th>Action</th></tr>}</thead>
      <tbody>{rows.map((row) => <tr key={row.id}>
        <td>{kind === "claims" ? <span className="mono">{String(row.claim_number)}</span> : kind === "billing" ? <span className="mono">{String(row.invoice_number)}</span> : patientName(row.patient_id)}</td>
        {kind === "insurance" && <><td>{String(row.payer_name)}</td><td>{String(row.plan_name || "—")}</td><td className="mono">{String(row.member_id)}</td><td>{row.status}</td></>}
        {kind === "claims" && <><td>{patientName(row.patient_id)}</td><td>{String(row.payer_name)}</td><td>{"$" + (Number(row.amount_cents) / 100).toFixed(2)}</td><td>{row.status}</td><td>{claimNext[row.status] ? <button className="text-action" onClick={() => update("claims/" + row.id + "/status", claimNext[row.status])}>Move to {claimNext[row.status]}</button> : "—"}</td></>}
        {kind === "authorizations" && <><td>{String(row.payer_name)}</td><td>{String(row.service_name)}</td><td>{row.status}</td><td>{row.status === "requested" ? <button className="text-action" onClick={() => update("authorizations/" + row.id + "/status", "submitted")}>Submit</button> : row.status === "submitted" ? <><button className="text-action" onClick={() => update("authorizations/" + row.id + "/status", "approved")}>Approve</button><button className="text-action" onClick={() => update("authorizations/" + row.id + "/status", "denied")}>Deny</button></> : "—"}</td></>}
        {kind === "billing" && <><td>{patientName(row.patient_id)}</td><td>{String(row.description)}</td><td>{"$" + (Number(row.amount_cents) / 100).toFixed(2)}</td><td>{"$" + (Number(row.paid_cents) / 100).toFixed(2)}</td><td>{row.status}</td><td>{row.status !== "paid" ? <button className="text-action" onClick={() => payment(row)}><CreditCard size={12} /> Record payment</button> : "—"}</td></>}
      </tr>)}{!rows.length && <tr><td colSpan={7} className="empty-row">No records yet.</td></tr>}</tbody>
    </table></div>
  </section>;
}

export function InsuranceWorkspace() { return <Workspace kind="insurance" />; }
export function ClaimsWorkspace() { return <Workspace kind="claims" />; }
export function AuthorizationsWorkspace() { return <Workspace kind="authorizations" />; }
export function BillingWorkspace() { return <Workspace kind="billing" />; }
