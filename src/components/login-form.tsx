"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: data.get("email"),
          password: data.get("password"),
          organization_slug: data.get("organization"),
        }),
      });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail ?? "Sign in failed");
      }
      router.replace("/dashboard");
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sign in failed");
    } finally {
      setBusy(false);
    }
  }

  return <form className="login-form" onSubmit={submit}>
    <label>Email address<input name="email" type="email" autoComplete="username" defaultValue="admin@medisphere.local" required /></label>
    <label>Password<input name="password" type="password" autoComplete="current-password" defaultValue="MediSphere-Demo-2026!" required /></label>
    <label>Organization<input name="organization" defaultValue="medisphere-health" required /></label>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="primary-button login-submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
  </form>;
}
