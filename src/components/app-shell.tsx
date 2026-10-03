"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { Bell, ChevronDown, LogOut, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { modules } from "@/lib/modules";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<{ user: { full_name: string }; organization: string; role: string } | null>(null);
  useEffect(() => {
    fetch("/api/auth/me").then(async (response) => {
      if (!response.ok) { await fetch("/api/auth/logout", { method: "POST" }); router.replace("/login"); return; }
      setSession(await response.json());
    }).catch(() => router.replace("/login"));
  }, [router]);
  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }
  return <div className="app-shell">
    <aside className="sidebar">
      <Link className="brand" href="/dashboard"><span className="brand-mark"><Image src="/medisphere-mark.svg" width={36} height={36} alt="" /></span><span><strong>MediSphere AI</strong><small>HEALTHCARE</small></span></Link>
      <div className="org-switch"><span className="org-avatar">MS</span><span className="org-copy"><strong>{session?.organization ?? "MediSphere AI Medical"}</strong><small>Care network</small></span><ChevronDown size={15} /></div>
      <div className="nav-label">WORKSPACE</div>
      <nav className="nav-list" aria-label="Main navigation">{modules.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href + "/"));
        return <Link key={item.href} href={item.href} className={"nav-link" + (active ? " active" : "")}><Icon size={17} strokeWidth={1.8} /><span>{item.label}</span></Link>;
      })}</nav>
      <div className="sidebar-bottom"><span className="online-dot" /> All systems operational</div>
    </aside>
    <div className="main-column">
      <header className="topbar"><Link className="top-brand" href="/dashboard" aria-label="MediSphere AI home"><Image src="/medisphere-logo.svg" width={220} height={48} alt="MediSphere AI" priority /></Link><div className="top-actions">
        <div className="search-button" aria-label="Search"><Search size={16} /><span>Search anything...</span><kbd>⌘ K</kbd></div>
        <span className="icon-button" aria-label="Notifications"><Bell size={18} /><i /></span>
        <div className="user-chip"><span className="user-avatar">{session?.user.full_name.split(" ").map((part) => part[0]).join("").slice(0, 2) ?? "NC"}</span><span><strong>{session?.user.full_name ?? "Loading account"}</strong><small>{session?.role.replaceAll("_", " ") ?? "Workspace user"}</small></span><button className="signout-button" onClick={signOut} aria-label="Sign out" title="Sign out"><LogOut size={15} /></button></div>
      </div></header>
      <main className="page-content">{children}</main>
      <footer className="footer">MediSphere AI <span>·</span> Unified healthcare workspace</footer>
    </div>
  </div>;
}
