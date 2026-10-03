"use client";

import { useEffect, useState } from "react";
import { Activity, ClipboardList, FileCheck2, Pill, ReceiptText, Users } from "lucide-react";

type Summary = { patients: number; appointments: number; encounters: number; open_claims: number; unpaid_invoices: number; prescriptions: number };
const cards = [
  ["Active patients", "patients", Users], ["Appointments", "appointments", Activity], ["Encounters", "encounters", ClipboardList],
  ["Open claims", "open_claims", FileCheck2], ["Unpaid invoices", "unpaid_invoices", ReceiptText], ["Prescriptions", "prescriptions", Pill],
] as const;

export function AnalyticsWorkspace() {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { fetch("/api/data/analytics/summary").then(async (response) => { if (!response.ok) throw new Error("Reports access is required to view this summary"); setData(await response.json()); }).catch((reason) => setError(reason.message)); }, []);
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Care network snapshot</h2><p>Live totals from this organization’s operational records.</p></div><span className="record-count">CURRENT TOTALS</span></div>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="summary-grid">{cards.map(([label, key, Icon]) => <article className="summary-card" key={key}><span className="module-icon"><Icon size={17} /></span><small>{label}</small><strong>{data ? data[key] : "—"}</strong></article>)}</div>
    <p className="form-hint muted">Totals include records currently stored in the workspace. This view does not estimate trends or clinical outcomes.</p>
  </section>;
}
