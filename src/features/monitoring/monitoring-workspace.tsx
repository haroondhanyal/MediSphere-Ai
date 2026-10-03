"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Activity, Watch } from "lucide-react";

type Patient = { id: number; given_name: string; family_name: string };
type Device = { id: number; patient_id: number; display_name: string; device_type: string; serial_number: string };
type Reading = { id: number; metric: string; value: number; unit: string; recorded_at: string };

export function MonitoringWorkspace() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [readings, setReadings] = useState<Reading[]>([]);
  const [selectedDevice, setSelectedDevice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    const [p, d] = await Promise.all([fetch("/api/data/patients"), fetch("/api/data/remote-monitoring/devices")]);
    if (!p.ok || !d.ok) throw new Error("Could not load devices");
    setPatients(await p.json()); setDevices(await d.json());
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
    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/data/remote-monitoring/devices", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ patient_id: Number(form.get("patient_id")), display_name: form.get("display_name"), device_type: form.get("device_type"), serial_number: form.get("serial_number") }) });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not register device"); return; }
    event.currentTarget.reset(); await load();
  }
  async function addReading(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/data/remote-monitoring/devices/" + selectedDevice + "/readings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ metric: form.get("metric"), value: Number(form.get("value")), unit: form.get("unit"), recorded_at: new Date().toISOString() }) });
    setBusy(false);
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not save reading"); return; }
    event.currentTarget.reset(); await loadReadings();
  }
  const patientName = (id: number) => {
    const patient = patients.find((person) => person.id === id);
    return patient ? patient.given_name + " " + patient.family_name : "Patient";
  };
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Remote patient monitoring</h2><p>Register devices and record timestamped measurements.</p></div><span className="record-count">{devices.length} DEVICES</span></div>
    <div className="notice"><span className="notice-mark">i</span><span><strong>Manual data entry</strong><small>Wearable integrations, clinical thresholds, and risk alerts are not connected.</small></span></div>
    <form className="record-form" onSubmit={createDevice}><label>Patient<select name="patient_id" required defaultValue=""><option value="" disabled>Select patient</option>{patients.map((p) => <option key={p.id} value={p.id}>{p.given_name} {p.family_name}</option>)}</select></label><label>Device name<input name="display_name" required placeholder="Home blood pressure monitor" /></label><label>Type<input name="device_type" required placeholder="Blood pressure" /></label><label>Serial number<input name="serial_number" /></label><button className="primary-button" disabled={busy || !patients.length}><Watch size={15} /> Register device</button></form>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="table-wrap"><table><thead><tr><th>Device</th><th>Patient</th><th>Type</th><th>Serial number</th></tr></thead><tbody>{devices.map((device) => <tr key={device.id}><td>{device.display_name}</td><td>{patientName(device.patient_id)}</td><td>{device.device_type}</td><td>{device.serial_number || "—"}</td></tr>)}{!devices.length && <tr><td colSpan={4} className="empty-row">No monitoring devices yet.</td></tr>}</tbody></table></div>
    <form className="record-form reading-form" onSubmit={addReading}><label>Device<select value={selectedDevice} onChange={(event) => setSelectedDevice(event.target.value)} required><option value="">Select device</option>{devices.map((device) => <option key={device.id} value={device.id}>{device.display_name} · {patientName(device.patient_id)}</option>)}</select></label><label>Metric<input name="metric" required placeholder="Systolic pressure" /></label><label>Value<input name="value" type="number" step="any" required /></label><label>Unit<input name="unit" required placeholder="mmHg" /></label><button className="primary-button" disabled={busy || !selectedDevice}><Activity size={15} /> Record reading</button></form>
    <div className="table-wrap"><table><thead><tr><th>Metric</th><th>Value</th><th>Recorded at</th></tr></thead><tbody>{readings.map((reading) => <tr key={reading.id}><td>{reading.metric}</td><td>{reading.value} {reading.unit}</td><td>{new Date(reading.recorded_at).toLocaleString()}</td></tr>)}{selectedDevice && !readings.length && <tr><td colSpan={3} className="empty-row">No readings for this device yet.</td></tr>}</tbody></table></div>
  </section>;
}
