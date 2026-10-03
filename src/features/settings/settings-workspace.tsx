"use client";

import { FormEvent, useEffect, useState } from "react";
import { Save, Settings2 } from "lucide-react";

type Organization = { id: number; name: string; slug: string; status: string; logo_url: string | null; contact_phone: string | null; settings: { timezone: string; default_locale: string }; subscription: { plan_code: string; status: string } };
export function SettingsWorkspace() {
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [name, setName] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { fetch("/api/data/organizations/current").then(async (response) => { if (!response.ok) throw new Error("Organization settings are not available for this account"); const data: Organization = await response.json(); setOrganization(data); setName(data.name); setLogoUrl(data.logo_url ?? ""); setPhone(data.contact_phone ?? ""); }).catch((reason) => setError(reason.message)); }, []);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch("/api/data/organizations/current", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, logo_url: logoUrl || null, contact_phone: phone || null }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not save organization profile");
      setOrganization(result); setNotice("Organization profile saved.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save organization profile"); }
    finally { setBusy(false); }
  }
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Organization profile</h2><p>Manage the name, logo, and contact number shown for your workspace.</p></div><span className="record-count">SETTINGS</span></div>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    {organization ? <>
      <form className="record-form settings-form" onSubmit={save}>
        <label>Organization name<input required maxLength={180} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label>Logo URL<input type="url" placeholder="https://example.com/logo.png" value={logoUrl} onChange={(e) => setLogoUrl(e.target.value)} /></label>
        <label>Contact number<input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
        {logoUrl && <div className="logo-preview"><small>Logo preview</small><img src={logoUrl} alt="Organization logo preview" onError={(e) => { e.currentTarget.style.visibility = "hidden"; }} /></div>}
        <button className="primary-button" disabled={busy}><Save size={15} /> {busy ? "Saving…" : "Save profile"}</button>
      </form>
      {notice && <p className="success-hint" role="status">{notice}</p>}
      <div className="settings-grid organization-details">{[["Workspace slug", organization.slug], ["Workspace status", organization.status], ["Timezone", organization.settings.timezone], ["Default language", organization.settings.default_locale], ["Plan", organization.subscription.plan_code], ["Subscription status", organization.subscription.status]].map(([label, value]) => <div className="settings-item" key={label}><small>{label}</small><strong>{value}</strong></div>)}</div>
    </> : !error && <div className="empty-row"><Settings2 size={16} /> Loading organization settings…</div>}
  </section>;
}
