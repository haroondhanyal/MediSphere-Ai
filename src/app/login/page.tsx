import { LoginForm } from "@/components/login-form";
import Image from "next/image";

export default function LoginPage() {
  return <main className="login-page">
    <section className="login-card">
      <div className="brand login-brand"><span className="brand-mark"><Image src="/medisphere-mark.svg" width={36} height={36} alt="" /></span><span><strong>MediSphere AI</strong><small>HEALTHCARE</small></span></div>
      <div className="eyebrow">SECURE WORKSPACE</div>
      <h1>Welcome back</h1>
      <p className="muted">Sign in to your healthcare workspace.</p>
      <LoginForm />
      <p className="login-foot">Local demo: admin@medisphere.local · MediSphere-Demo-2026!</p>
    </section>
  </main>;
}
