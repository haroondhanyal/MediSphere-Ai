import Image from "next/image";
import { ResetPasswordForm } from "@/components/reset-password-form";

export default function ResetPasswordPage() {
  return <main className="login-page auth-page">
    <section className="login-card">
      <Image className="login-logo" src="/medisphere-logo.svg" width={440} height={96} alt="MediSphere AI" priority />
      <div className="eyebrow">ACCOUNT RECOVERY</div>
      <h1>Choose a new password</h1>
      <p className="muted">Use at least 12 characters to protect your account.</p>
      <ResetPasswordForm />
    </section>
  </main>;
}
