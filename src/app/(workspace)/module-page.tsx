import { ArrowLeft, Construction } from "lucide-react";
import Link from "next/link";
import { modules } from "@/lib/modules";

export function ModulePage({ href }: { href: (typeof modules)[number]["href"] }) {
  const item = modules.find((module) => module.href === href);
  if (!item) return null;
  const Icon = item.icon;
  const featureFolder = href.slice(1);
  return <>
    <Link href="/dashboard" className="back-link"><ArrowLeft size={15} /> All modules</Link>
    <div className="module-title"><span className="module-icon large"><Icon size={22} /></span><div><div className="eyebrow">WORKSPACE MODULE</div><h1>{item.label}</h1><p className="muted">{item.description}</p></div></div>
    <section className="empty-state"><span className="empty-icon"><Construction size={22} /></span><h2>{item.label} workspace</h2><p>This screen is ready for the {item.label.toLowerCase()} team’s workflow. Keep its feature components in <code>src/features/{featureFolder}/</code> and connect them when the module API is available.</p><span className="status-pill"><i /> Screen scaffolded</span></section>
  </>;
}
