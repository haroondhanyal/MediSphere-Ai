"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { PasswordField } from "@/components/password-field";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).has("passwordReset")) setNotice("Password updated. Sign in with your new password.");
  }, []);

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
          organization_slug: String(data.get("organization") ?? "").trim() || null,
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
    <label htmlFor="login-email">Email address<input id="login-email" name="email" type="email" autoComplete="username" required /></label>
    <PasswordField id="login-password" name="password" label="Password" autoComplete="current-password" />
    <label htmlFor="login-organization">Organization<input id="login-organization" name="organization" autoComplete="organization" /></label>
    <small className="optional-label">Leave blank if your account has only one workspace.</small>
    {error && <p className="form-error" role="alert">{error}</p>}
    {notice && <p className="success-hint" role="status">{notice}</p>}
    <button className="primary-button login-submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
    <div className="auth-links"><Link href="/forgot-password">Forgot password?</Link><span>New here? <Link href="/signup">Create an account</Link></span></div>
  </form>;
}
