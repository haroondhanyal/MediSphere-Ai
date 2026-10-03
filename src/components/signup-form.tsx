"use client";

import { ChangeEvent, FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Building2, Check, ClipboardList, HeartPulse, ImagePlus, Stethoscope } from "lucide-react";
import { PasswordField } from "@/components/password-field";

const countries = [
  { code: "PK", label: "🇵🇰 Pakistan", dial: "+92", regions: ["Azad Jammu and Kashmir", "Balochistan", "Islamabad Capital Territory", "Gilgit-Baltistan", "Khyber Pakhtunkhwa", "Punjab", "Sindh"] },
  { code: "US", label: "🇺🇸 United States", dial: "+1", regions: ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"] },
  { code: "GB", label: "🇬🇧 United Kingdom", dial: "+44", regions: ["England", "Northern Ireland", "Scotland", "Wales"] },
  { code: "IN", label: "🇮🇳 India", dial: "+91", regions: ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"] },
] as const;

const roles = [
  { id: "hospital_admin", title: "Administrator", detail: "Manage a care workspace", icon: Building2 },
  { id: "doctor", title: "Doctor", detail: "Coordinate clinical care", icon: Stethoscope },
  { id: "nurse", title: "Nurse", detail: "Support care delivery", icon: HeartPulse },
  { id: "receptionist", title: "Front desk", detail: "Coordinate visits", icon: ClipboardList },
] as const;

function errorMessage(value: unknown) {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map((item) => item?.msg ?? "Invalid form input").join(" · ");
  return "Could not create your account";
}

export function SignupForm() {
  const router = useRouter();
  const [countryCode, setCountryCode] = useState<(typeof countries)[number]["code"]>("PK");
  const [region, setRegion] = useState("Punjab");
  const [role, setRole] = useState<(typeof roles)[number]["id"]>("hospital_admin");
  const [phone, setPhone] = useState("");
  const [imageData, setImageData] = useState("");
  const [imagePreview, setImagePreview] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const country = countries.find((item) => item.code === countryCode) ?? countries[0];
  const maxPhoneDigits = 15 - country.dial.slice(1).length;

  async function chooseImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    setError("");
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 8 * 1024 * 1024) {
      setError("Choose a PNG, JPEG, or WebP image under 8 MB.");
      event.target.value = "";
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    try {
      const source = new Image();
      source.src = objectUrl;
      await source.decode();
      let output = "";
      for (const size of [320, 240, 160]) {
        const scale = Math.min(1, size / Math.max(source.width, source.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(source.width * scale));
        canvas.height = Math.max(1, Math.round(source.height * scale));
        const context = canvas.getContext("2d");
        if (!context) throw new Error("Your browser could not prepare this image.");
        context.drawImage(source, 0, 0, canvas.width, canvas.height);
        output = canvas.toDataURL("image/webp", 0.78);
        if (output.length <= 340_000) break;
      }
      if (output.length > 340_000) throw new Error("This image could not be compressed enough. Try another image.");
      setImageData(output);
      setImagePreview(output);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load this image.");
      event.target.value = "";
    } finally {
      URL.revokeObjectURL(objectUrl);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password") ?? "");
    if (password !== data.get("confirm_password")) {
      setBusy(false);
      setError("Passwords do not match.");
      return;
    }
    try {
      const response = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: data.get("full_name"),
          email: data.get("email"),
          password,
          organization_name: data.get("organization_name"),
          role_code: role,
          phone_e164: country.dial + phone.replace(/^0+/, ""),
          country_code: country.code,
          region,
          profile_image_data: imageData || null,
        }),
      });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(errorMessage(result.detail));
      }
      router.replace("/dashboard");
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create your account");
    } finally {
      setBusy(false);
    }
  }

  return <form className="auth-form signup-form" onSubmit={submit}>
    <div className="profile-image-picker">
      <label className="profile-image-button" htmlFor="profile-image" aria-label="Choose a profile image">
        {imagePreview ? <img src={imagePreview} alt="Profile preview" /> : <ImagePlus size={21} />}
        <span className="profile-image-badge"><Check size={11} /></span>
      </label>
      <div><strong>Profile photo</strong><small>Optional · PNG, JPEG, or WebP</small></div>
      <input id="profile-image" type="file" accept="image/png,image/jpeg,image/webp" onChange={chooseImage} />
    </div>

    <div className="signup-fields">
      <label htmlFor="signup-name">Full name<input id="signup-name" name="full_name" autoComplete="name" maxLength={180} required /></label>
      <label htmlFor="signup-email">Work email<input id="signup-email" name="email" type="email" autoComplete="email" maxLength={320} required /></label>
      <label htmlFor="signup-organization">Organization name<input id="signup-organization" name="organization_name" autoComplete="organization" maxLength={180} required /></label>
      <label htmlFor="signup-country">Country<select id="signup-country" value={countryCode} onChange={(event) => {
        const next = countries.find((item) => item.code === event.target.value) ?? countries[0];
        setCountryCode(next.code);
        setRegion(next.regions[0]);
        setPhone("");
      }}>{countries.map((item) => <option key={item.code} value={item.code}>{item.label} ({item.dial})</option>)}</select></label>
      <label htmlFor="signup-region">State / province<select id="signup-region" value={region} onChange={(event) => setRegion(event.target.value)}>{country.regions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
      <label htmlFor="signup-phone">Phone number<span className="phone-input-wrap"><span>{country.dial}</span><input id="signup-phone" type="tel" autoComplete="tel-national" inputMode="tel" value={phone} onChange={(event) => setPhone(event.target.value.replace(/[^0-9]/g, "").slice(0, maxPhoneDigits))} placeholder="Mobile number" required /></span></label>
    </div>

    <fieldset className="role-picker"><legend>Your role</legend><div className="role-options">{roles.map((item) => {
      const Icon = item.icon;
      return <button className={`role-option${role === item.id ? " selected" : ""}`} type="button" key={item.id} aria-pressed={role === item.id} onClick={() => setRole(item.id)}>
        <Icon size={17} /><span><strong>{item.title}</strong><small>{item.detail}</small></span>{role === item.id && <Check className="role-check" size={14} />}
      </button>;
    })}</div></fieldset>

    <div className="signup-fields password-pair">
      <PasswordField id="signup-password" name="password" label="Password · 12 characters minimum" autoComplete="new-password" minLength={12} />
      <PasswordField id="signup-confirm-password" name="confirm_password" label="Confirm password" autoComplete="new-password" minLength={12} />
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="primary-button login-submit" disabled={busy}>{busy ? "Creating account…" : "Create account"}</button>
    <p className="auth-links auth-links-center">Already have an account? <Link href="/login">Sign in</Link></p>
  </form>;
}
