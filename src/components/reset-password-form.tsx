"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PasswordField } from "@/components/password-field";

export function ResetPasswordForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password") ?? "");
    if (password !== data.get("confirm_password")) {
      setBusy(false);
      setError("Passwords do not match.");
      return;
    }
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setBusy(false);
      setError("This reset link is missing its token. Request a new link.");
      return;
    }
    try {
      const response = await fetch("/api/auth/password/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Could not reset the password.");
      router.replace("/login?passwordReset=1");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not reset the password.");
    } finally {
      setBusy(false);
    }
  }

  return <form className="login-form" onSubmit={submit}>
    <PasswordField id="reset-password" name="password" label="New password · 12 characters minimum" autoComplete="new-password" minLength={12} />
    <PasswordField id="reset-confirm-password" name="confirm_password" label="Confirm new password" autoComplete="new-password" minLength={12} />
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="primary-button login-submit" disabled={busy}>{busy ? "Updating…" : "Update password"}</button>
    <p className="auth-links auth-links-center"><Link href="/login">Back to sign in</Link></p>
  </form>;
}
