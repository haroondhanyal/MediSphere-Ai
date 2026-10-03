"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { BellPlus, Send, Video } from "lucide-react";

type Member = { id: number; full_name: string; email: string };
type Message = { id: number; sender_user_id: number; body: string; sent_at: string };
type Notice = { id: number; title: string; body: string; category: string; read_at: string | null; created_at: string };
type Appointment = { id: number; starts_at: string; status: string };
type Session = { id: number; appointment_id: number; room_code: string; status: string };

export function MessagesWorkspace() {
  const [members, setMembers] = useState<Member[]>([]);
  const [selected, setSelected] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentUser, setCurrentUser] = useState(0);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const loadMessages = useCallback(async () => {
    if (!selected) return;
    const response = await fetch("/api/data/messages?with_user_id=" + selected);
    if (!response.ok) throw new Error("Could not load messages");
    setMessages(await response.json());
  }, [selected]);
  useEffect(() => {
    Promise.all([fetch("/api/data/directory"), fetch("/api/auth/me")]).then(async ([a, b]) => {
      if (!a.ok || !b.ok) throw new Error("Could not load organization members");
      setMembers(await a.json());
      const session = await b.json();
      setCurrentUser(session.user.id);
    }).catch((reason) => setError(reason.message));
  }, []);
  useEffect(() => {
    // Refresh server-owned messages on selection and on the polling timer.
    loadMessages().catch((reason) => setError(reason.message));
    const timer = window.setInterval(() => loadMessages().catch((reason) => setError(reason.message)), 5000);
    return () => window.clearInterval(timer);
  }, [loadMessages]);
  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const response = await fetch("/api/data/messages", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ recipient_user_id: Number(selected), body: text }) });
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not send message"); return; }
    setText(""); await loadMessages();
  }
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Secure messages</h2><p>Private messages between members of this organization.</p></div><span className="record-count">POLLING · 5 SEC</span></div>
    <label className="member-select">Conversation with<select value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">Choose a team member</option>{members.map((member) => <option key={member.id} value={member.id}>{member.full_name} · {member.email}</option>)}</select></label>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="message-list">{messages.map((message) => <article key={message.id} className={"message-bubble" + (message.sender_user_id === currentUser ? " mine" : "")}><p>{message.body}</p><small>{new Date(message.sent_at).toLocaleString()}</small></article>)}{selected && !messages.length && <p className="empty-row">No messages in this conversation yet.</p>}</div>
    <form className="message-form" onSubmit={send}><input value={text} onChange={(event) => setText(event.target.value)} maxLength={4000} placeholder="Write a secure message…" required disabled={!selected} /><button className="primary-button" disabled={!selected || !text.trim()}><Send size={15} /> Send</button></form>
  </section>;
}

export function NotificationsWorkspace() {
  const [rows, setRows] = useState<Notice[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    const response = await fetch("/api/data/notifications");
    if (!response.ok) throw new Error("Could not load notifications");
    setRows(await response.json());
  }, []);
  // Initial server data is applied after fetch resolves.
  useEffect(() => { load().catch((reason) => setError(reason.message)); }, [load]);
  async function addReminder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const response = await fetch("/api/data/notifications", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    if (!response.ok) { setError("Could not create reminder"); return; }
    event.currentTarget.reset(); await load();
  }
  async function markRead(id: number) {
    const response = await fetch("/api/data/notifications/" + id + "/read", { method: "POST" });
    if (!response.ok) { setError("Could not update notification"); return; }
    await load();
  }
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Notification center</h2><p>Organization events and secure message alerts.</p></div><span className="record-count">{rows.filter((item) => !item.read_at).length} UNREAD</span></div>
    <form className="record-form reminder-form" onSubmit={addReminder}><label>Reminder title<input name="title" required maxLength={180} /></label><label>Details<input name="body" maxLength={1000} /></label><button className="primary-button"><BellPlus size={15} /> Add reminder</button></form>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="notification-list">{rows.map((item) => <article key={item.id} className={"notification-item" + (item.read_at ? "" : " unread")}><span className="notification-mark"><BellPlus size={16} /></span><div><strong>{item.title}</strong><p>{item.body}</p><small>{item.category} · {new Date(item.created_at).toLocaleString()}</small></div>{!item.read_at && <button className="text-action" onClick={() => markRead(item.id)}>Mark read</button>}</article>)}{!rows.length && <p className="empty-row">No notifications yet.</p>}</div>
  </section>;
}

export function TelehealthWorkspace() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    const [a, s] = await Promise.all([fetch("/api/data/appointments"), fetch("/api/data/telehealth/sessions")]);
    if (!a.ok || !s.ok) throw new Error("Could not load virtual visit sessions");
    setAppointments(await a.json()); setSessions(await s.json());
  }, []);
  // Initial server data is applied after fetch resolves.
  useEffect(() => { load().catch((reason) => setError(reason.message)); }, [load]);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const response = await fetch("/api/data/telehealth/sessions?appointment_id=" + selected, { method: "POST" });
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not create session"); return; }
    setSelected(""); await load();
  }
  async function change(id: number, action: "start" | "end") {
    const response = await fetch("/api/data/telehealth/sessions/" + id + "/" + action, { method: "POST" });
    if (!response.ok) { const result = await response.json(); setError(result.detail ?? "Could not update session"); return; }
    await load();
  }
  const eligible = appointments.filter((item) => item.status === "scheduled" && !sessions.some((session) => session.appointment_id === item.id));
  return <section className="workspace-panel">
    <div className="panel-title"><div><h2>Virtual visit sessions</h2><p>Coordinate a telehealth session from a scheduled appointment.</p></div><span className="record-count">SESSION CONTROL</span></div>
    <div className="notice"><span className="notice-mark">i</span><span><strong>Session coordination only</strong><small>A video provider and protected media connection must be configured before calls can run.</small></span></div>
    <form className="record-form session-form" onSubmit={create}><label>Appointment<select required value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">Select appointment</option>{eligible.map((item) => <option key={item.id} value={item.id}>Appointment #{item.id} · {new Date(item.starts_at).toLocaleString()}</option>)}</select></label><button className="primary-button" disabled={!selected}><Video size={15} /> Create session</button></form>
    {error && <p className="form-error panel-error" role="alert">{error}</p>}
    <div className="notification-list">{sessions.map((item) => <article className="notification-item" key={item.id}><span className="notification-mark"><Video size={16} /></span><div><strong>Appointment #{item.appointment_id}</strong><p>Session reference: {item.room_code}</p><small>Status: {item.status}</small></div>{item.status === "scheduled" && <button className="text-action" onClick={() => change(item.id, "start")}>Start</button>}{item.status === "in_progress" && <button className="text-action" onClick={() => change(item.id, "end")}>End</button>}</article>)}{!sessions.length && <p className="empty-row">No virtual sessions scheduled.</p>}</div>
  </section>;
}
