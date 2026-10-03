import { LoginForm } from "@/components/login-form";
import Image from "next/image";

export default function LoginPage() {
  return <main className="login-page">
    <section className="login-card">
      <Image className="login-logo" src="/medisphere-logo.svg" width={440} height={96} alt="MediSphere AI" priority />
      <div className="eyebrow">SECURE WORKSPACE</div>
      <h1>Welcome back</h1>
      <p className="muted">Sign in to your healthcare workspace.</p>
      <LoginForm />
      {process.env.NODE_ENV !== "production" && <p className="login-foot">Local demo: admin@medisphere.local · MediSphere-Demo-2026!</p>}
    </section>
  </main>;
}
