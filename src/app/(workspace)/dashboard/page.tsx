import Link from "next/link";
import { ArrowUpRight, CalendarDays, Clock3, Users } from "lucide-react";
import { modules } from "@/lib/modules";

export default function DashboardPage() {
  const cards = modules.filter((item) => item.href !== "/dashboard");
  return <>
    <div className="welcome-row"><div><div className="eyebrow">SAMPLE WORKSPACE DATA</div><h1>Good morning, Sofia <span>✦</span></h1><p className="muted">Here’s your care network at a glance.</p></div><Link className="primary-button" href="/appointments"><CalendarDays size={16} /> View schedule</Link></div>
    <section className="metric-grid">
      <article className="metric-card"><div className="metric-heading"><span>Patients</span><Users size={17} /></div><strong>1,284</strong><small><b className="positive">+8.2%</b> this month</small><div className="metric-spark teal" /></article>
      <article className="metric-card"><div className="metric-heading"><span>Appointments today</span><CalendarDays size={17} /></div><strong>36</strong><small><b className="positive">12 completed</b> · 24 upcoming</small><div className="metric-spark blue" /></article>
      <article className="metric-card"><div className="metric-heading"><span>Average wait time</span><Clock3 size={17} /></div><strong>14 <em>min</em></strong><small><b className="positive">−3 min</b> from last week</small><div className="metric-spark purple" /></article>
      <article className="metric-card"><div className="metric-heading"><span>Open claims</span><ArrowUpRight size={17} /></div><strong>82</strong><small><b className="neutral">In review</b> across 3 payers</small><div className="metric-spark orange" /></article>
    </section>
    <div className="section-heading"><div><h2>Workspace modules</h2><p>Open a module to work with that team’s workflow.</p></div><span className="module-count">{cards.length} MODULES</span></div>
    <section className="module-grid">{cards.map((item) => { const Icon = item.icon; return <Link className="module-card" href={item.href} key={item.href}><span className="module-icon"><Icon size={19} /></span><span className="module-text"><strong>{item.label}</strong><small>{item.description}</small></span><ArrowUpRight className="module-arrow" size={16} /></Link>; })}</section>
    <div className="notice"><span className="notice-mark">i</span><span><strong>Phases 1–10 local workflows are ready</strong><small>Care, revenue, interoperability, monitoring alerts, automated checks, and deployment tooling are in place.</small></span></div>
  </>;
}
