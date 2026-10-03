"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Activity, Watch } from "lucide-react";

type Patient = { id: number; given_name: string; family_name: string };
type Device = { id: number; patient_id: number; display_name: string; device_type: string; serial_number: string };
type Reading = { id: number; metric: string; value: number; unit: string; recorded_at: string };
type Rule = { id: number; metric: string; unit: string; minimum: number | null; maximum: number | null; enabled: boolean };
type Alert = { id: number; device_name: string; patient_name: string; metric: string; value: number; unit: string; message: string; status: string; created_at: string };
type DeviceCredential = { device_id: number; token: string };

export function MonitoringWorkspace() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [readings, setReadings] = useState<Reading[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [deviceCredential, setDeviceCredential] = useState<DeviceCredential | null>(null);
  const [selectedDevice, setSelectedDevice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    const [p, d, r, a] = await Promise.all([fetch("/api/data/patients"), fetch("/api/data/remote-monitoring/devices"), fetch("/api/data/remote-monitoring/rules"), fetch("/api/data/remote-monitoring/alerts")]);
    if (!p.ok || !d.ok || !r.ok || !a.ok) throw new Error("Could not load monitoring workspace");
    setPatients(await p.json()); setDevices(await d.json()); setRules(await r.json()); setAlerts(await a.json());
  }, []);
  const loadReadings = useCallback(async () => {
    if (!selectedDevice) { setReadings([]); return; }
    const response = await fetch("/api/data/remote-monitoring/devices/" + selectedDevice + "/readings");
    if (!response.ok) throw new Error("Could not load device readings");
    setReadings(await response.json());
  }, [selectedDevice]);
  // Initial server data is applied after fetch resolves.
  useEffect(() => { load().catch((reason) => setError(reason.message)); }, [load]);
  // Refresh readings when the selected device changes.
  useEffect(() => { loadReadings().catch((reason) => setError(reason.message)); }, [loadReadings]);
  async function createDevice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const formElement = event.currentTarget; const form = new FormData(formElement);
    const response = await fetch("/api/data/remote-monitoring/devices", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ patient_id: Number(form.get("patient_id")), display_name: form.get("display_name"), device_type: form.get("device_type"), serial_number: form.get("serial_number") }) });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not register device"); return; }
    const created = await response.json();
    setDeviceCredential({ device_id: created.id, token: created.ingest_token });
    setSelectedDevice(String(created.id));
    formElement.reset(); await load();
  }
  async function addReading(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/data/remote-monitoring/devices/" + selectedDevice + "/readings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ metric: form.get("metric"), value: Number(form.get("value")), unit: form.get("unit"), recorded_at: new Date().toISOString() }) });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not save reading"); return; }
    event.currentTarget.reset(); await loadReadings();
    await load();
  }
  async function saveRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    const min = String(form.get("minimum") ?? "").trim(); const max = String(form.get("maximum") ?? "").trim();
    const response = await fetch("/api/data/remote-monitoring/rules", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ metric: form.get("metric"), unit: form.get("unit"), minimum: min ? Number(min) : null, maximum: max ? Number(max) : null }) });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not save threshold"); return; }
    event.currentTarget.reset(); await load();
  }
  async function acknowledge(alertId: number) {
    const response = await fetch("/api/data/remote-monitoring/alerts/" + alertId + "/acknowledge", { method: "POST" });
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not acknowledge alert"); return; }
    await load();
  }
  async function rotateCredential(deviceId: number) {
    const response = await fetch("/api/data/remote-monitoring/devices/" + deviceId + "/ingest-token", { method: "POST" });
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not rotate device token"); return; }
    const result = await response.json(); setDeviceCredential({ device_id: deviceId, token: result.ingest_token });
  }
  const patientName = (id: number) => {
    const patient = patients.find((person) => person.id === id);
    return patient ? patient.given_name + " " + patient.family_name : "Patient";
  };
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Remote patient monitoring</h2><p>Register devices and record timestamped measurements.</p></div><span className="record-count">{devices.length} DEVICES</span></div>
    <div className="notice"><span className="notice-mark">i</span><span><strong>Clinician-configured monitoring thresholds</strong><small>Alerts follow thresholds your care team configures. Review measurements in clinical context; alerts are not a diagnosis.</small></span></div>
    <form className="record-form" onSubmit={createDevice}><label>Patient<select name="patient_id" required defaultValue=""><option value="" disabled>Select patient</option>{patients.map((p) => <option key={p.id} value={p.id}>{p.given_name} {p.family_name}</option>)}</select></label><label>Device name<input name="display_name" required placeholder="Home blood pressure monitor" /></label><label>Type<input name="device_type" required placeholder="Blood pressure" /></label><label>Serial number<input name="serial_number" /></label><button className="primary-button" disabled={busy || !patients.length}><Watch size={15} /> Register device</button></form>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    {deviceCredential && <div className="notice" role="status"><span className="notice-mark">!</span><span><strong>Copy this device token now</strong><small>It is only shown once. Send readings to /api/v1/remote-monitoring/ingest/{deviceCredential.device_id}/readings with an Authorization: Bearer header.</small><code className="device-token">{deviceCredential.token}</code></span></div>}
    <div className="table-wrap"><table><thead><tr><th>Device</th><th>Patient</th><th>Type</th><th>Serial number</th><th>Integration</th></tr></thead><tbody>{devices.map((device) => <tr key={device.id}><td>{device.display_name}</td><td>{patientName(device.patient_id)}</td><td>{device.device_type}</td><td>{device.serial_number || "—"}</td><td><button className="text-action" onClick={() => rotateCredential(device.id)}>Rotate ingest token</button></td></tr>)}{!devices.length && <tr><td colSpan={5} className="empty-row">No monitoring devices yet.</td></tr>}</tbody></table></div>
    <form className="record-form reading-form" onSubmit={addReading}><label>Device<select value={selectedDevice} onChange={(event) => setSelectedDevice(event.target.value)} required><option value="">Select device</option>{devices.map((device) => <option key={device.id} value={device.id}>{device.display_name} · {patientName(device.patient_id)}</option>)}</select></label><label>Metric<input name="metric" required placeholder="Systolic pressure" /></label><label>Value<input name="value" type="number" step="any" required /></label><label>Unit<input name="unit" required placeholder="mmHg" /></label><button className="primary-button" disabled={busy || !selectedDevice}><Activity size={15} /> Record reading</button></form>
    <div className="table-wrap"><table><thead><tr><th>Metric</th><th>Value</th><th>Recorded at</th></tr></thead><tbody>{readings.map((reading) => <tr key={reading.id}><td>{reading.metric}</td><td>{reading.value} {reading.unit}</td><td>{new Date(reading.recorded_at).toLocaleString()}</td></tr>)}{selectedDevice && !readings.length && <tr><td colSpan={3} className="empty-row">No readings for this device yet.</td></tr>}</tbody></table></div>
    <div className="panel-title monitoring-section-title"><div><h2>Alert thresholds</h2><p>Set a minimum, maximum, or both for each metric and unit.</p></div><span className="record-count">{rules.length} RULES</span></div>
    <form className="record-form" onSubmit={saveRule}><label>Metric<input name="metric" required placeholder="Systolic pressure" /></label><label>Unit<input name="unit" required placeholder="mmHg" /></label><label>Minimum<input name="minimum" type="number" step="any" /></label><label>Maximum<input name="maximum" type="number" step="any" /></label><button className="primary-button" disabled={busy}><Activity size={15} /> Save threshold</button></form>
    <div className="table-wrap"><table><thead><tr><th>Metric</th><th>Unit</th><th>Minimum</th><th>Maximum</th></tr></thead><tbody>{rules.map((rule) => <tr key={rule.id}><td>{rule.metric}</td><td>{rule.unit}</td><td>{rule.minimum ?? "—"}</td><td>{rule.maximum ?? "—"}</td></tr>)}{!rules.length && <tr><td colSpan={4} className="empty-row">No thresholds configured.</td></tr>}</tbody></table></div>
    <div className="panel-title monitoring-section-title"><div><h2>Threshold alerts</h2><p>Review and acknowledge readings outside configured limits.</p></div><span className="record-count">{alerts.filter((alert) => alert.status === "open").length} OPEN</span></div>
    <div className="table-wrap"><table><thead><tr><th>Patient</th><th>Device</th><th>Reading</th><th>Alert</th><th>Time</th><th>Status</th><th /></tr></thead><tbody>{alerts.map((alert) => <tr key={alert.id}><td>{alert.patient_name}</td><td>{alert.device_name}</td><td>{alert.value} {alert.unit}</td><td>{alert.message}</td><td>{new Date(alert.created_at).toLocaleString()}</td><td>{alert.status}</td><td>{alert.status === "open" && <button className="text-action" onClick={() => acknowledge(alert.id)}>Acknowledge</button>}</td></tr>)}{!alerts.length && <tr><td colSpan={7} className="empty-row">No alerts. Alerts appear when readings cross a configured threshold.</td></tr>}</tbody></table></div>
  </section>;
}
