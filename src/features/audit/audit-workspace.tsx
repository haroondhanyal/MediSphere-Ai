"use client";

import { useEffect, useState } from "react";
import { ScrollText } from "lucide-react";

type Event = { id: number; actor_user_id: number | null; event: string; resource_type: string | null; resource_id: string | null; created_at: string; details: Record<string, unknown> };
export function AuditWorkspace() {
  const [events, setEvents] = useState<Event[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { fetch("/api/data/audit").then(async (response) => { if (!response.ok) throw new Error("Audit access is not available for this account"); setEvents(await response.json()); }).catch((reason) => setError(reason.message)); }, []);
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Recent access and workflow events</h2><p>Most recent 200 organization events, newest first.</p></div><span className="record-count">{events.length} EVENTS</span></div>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="table-wrap"><table><thead><tr><th>WHEN</th><th>ACTOR</th><th>EVENT</th><th>RESOURCE</th><th>DETAILS</th></tr></thead><tbody>
      {events.map((event) => <tr key={event.id}><td>{new Date(event.created_at).toLocaleString()}</td><td>{event.actor_user_id ? `User #${event.actor_user_id}` : "System"}</td><td className="mono">{event.event}</td><td>{event.resource_type ? `${event.resource_type}${event.resource_id ? ` #${event.resource_id}` : ""}` : "—"}</td><td>{Object.keys(event.details ?? {}).length ? JSON.stringify(event.details) : "—"}</td></tr>)}
      {!events.length && !error && <tr><td colSpan={5} className="empty-row"><ScrollText size={16} /> No audit events recorded yet.</td></tr>}
    </tbody></table></div>
  </section>;
}
