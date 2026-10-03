"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Pill } from "lucide-react";

type Prescription = { id: number; patient_id: number; medication_name: string; dosage: string; frequency: string; duration: string; instructions: string; status: string; created_at: string };

export function PharmacyWorkspace() {
  const [orders, setOrders] = useState<Prescription[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    const response = await fetch("/api/data/prescriptions");
    if (!response.ok) throw new Error("Could not load prescriptions for this organization");
    setOrders(await response.json());
  }, []);
  useEffect(() => { load().catch((reason) => setError(reason.message)); }, [load]);
  async function update(id: number, status: string) {
    setError("");
    const response = await fetch(`/api/data/pharmacy/prescriptions/${id}/status`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not update dispensing status"); return; }
    await load();
  }
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Dispensing queue</h2><p>Review organization prescriptions and record pharmacy handoff.</p></div><span className="record-count">{orders.filter((item) => !["dispensed", "cancelled"].includes(item.status)).length} OPEN</span></div>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="table-wrap"><table><thead><tr><th>ORDER</th><th>PATIENT ID</th><th>MEDICATION</th><th>INSTRUCTIONS</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>
      {orders.map((order) => <tr key={order.id}><td className="mono">RX-{order.id}</td><td>#{order.patient_id}</td><td><strong>{order.medication_name}</strong><br /><small>{order.dosage} · {order.frequency}{order.duration ? ` · ${order.duration}` : ""}</small></td><td>{order.instructions || "—"}</td><td><span className="table-dot" />{order.status.replaceAll("_", " ")}</td><td>{order.status === "active" ? <button className="text-action" onClick={() => update(order.id, "dispensing")}>Prepare</button> : order.status === "dispensing" ? <button className="text-action" onClick={() => update(order.id, "dispensed")}><Check size={13} /> Dispensed</button> : "—"}</td></tr>)}
      {!orders.length && <tr><td colSpan={6} className="empty-row"><Pill size={16} /> No prescriptions in the queue.</td></tr>}
    </tbody></table></div>
  </section>;
}
