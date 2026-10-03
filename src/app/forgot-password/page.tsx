import Image from "next/image";
import { ForgotPasswordForm } from "@/components/forgot-password-form";

export default function ForgotPasswordPage() {
  return <main className="login-page auth-page">
    <section className="login-card">
      <Image className="login-logo" src="/medisphere-logo.svg" width={440} height={96} alt="MediSphere AI" priority />
      <div className="eyebrow">ACCOUNT RECOVERY</div>
      <h1>Reset your password</h1>
      <p className="muted">Enter your account email and we’ll send a secure reset link.</p>
      <ForgotPasswordForm />
    </section>
  </main>;
}
