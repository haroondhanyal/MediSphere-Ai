"use client";

import { useEffect, useState } from "react";
import { Settings2 } from "lucide-react";

type Organization = { id: number; name: string; slug: string; status: string; settings: { timezone: string; default_locale: string }; subscription: { plan_code: string; status: string } };
export function SettingsWorkspace() {
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { fetch("/api/data/organizations/current").then(async (response) => { if (!response.ok) throw new Error("Organization settings are not available for this account"); setOrganization(await response.json()); }).catch((reason) => setError(reason.message)); }, []);
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Organization profile</h2><p>Workspace configuration available to your account.</p></div><span className="record-count">READ ONLY</span></div>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    {organization ? <div className="settings-grid">{[
      ["Organization", organization.name], ["Workspace slug", organization.slug], ["Workspace status", organization.status],
      ["Timezone", organization.settings.timezone], ["Default language", organization.settings.default_locale],
      ["Plan", organization.subscription.plan_code], ["Subscription status", organization.subscription.status],
    ].map(([label, value]) => <div className="settings-item" key={label}><small>{label}</small><strong>{value}</strong></div>)}</div> : !error && <div className="empty-row"><Settings2 size={16} /> Loading organization settings…</div>}
  </section>;
}
