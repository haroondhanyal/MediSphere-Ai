import Image from "next/image";
import { SignupForm } from "@/components/signup-form";

export default function SignupPage() {
  return <main className="login-page auth-page">
    <section className="login-card signup-card">
      <Image className="login-logo" src="/medisphere-logo.svg" width={440} height={96} alt="MediSphere AI" priority />
      <div className="eyebrow">GET STARTED</div>
      <h1>Create your workspace</h1>
      <p className="muted">Set up your organization and care team account.</p>
      <SignupForm />
    </section>
  </main>;
}
