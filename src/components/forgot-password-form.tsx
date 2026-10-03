"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";

export function ForgotPasswordForm() {
  const [message, setMessage] = useState("");
  const [resetUrl, setResetUrl] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    setResetUrl("");
    try {
      const data = new FormData(event.currentTarget);
      const response = await fetch("/api/auth/password/forgot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: data.get("email") }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Could not request a password reset.");
      setMessage(result.message);
      setResetUrl(result.development_reset_url ?? "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not request a password reset.");
    } finally {
      setBusy(false);
    }
  }

  return <form className="login-form" onSubmit={submit}>
    <label htmlFor="forgot-email">Email address<input id="forgot-email" name="email" type="email" autoComplete="email" required /></label>
    {error && <p className="form-error" role="alert">{error}</p>}
    {message && <p className="success-hint" role="status">{message}</p>}
    {resetUrl && <a className="development-reset-link" href={resetUrl}>Open local password reset link</a>}
    <button className="primary-button login-submit" disabled={busy}>{busy ? "Sending…" : "Send reset link"}</button>
    <p className="auth-links auth-links-center"><Link href="/login">Back to sign in</Link></p>
  </form>;
}
