"use client";

import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

type PasswordFieldProps = {
  id: string;
  name: string;
  label: string;
  autoComplete: string;
  required?: boolean;
  minLength?: number;
};

export function PasswordField({ id, name, label, autoComplete, required = true, minLength }: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  return <label htmlFor={id}>{label}
    <span className="password-input-wrap">
      <input id={id} name={name} type={visible ? "text" : "password"} autoComplete={autoComplete} required={required} minLength={minLength} />
      <button className="password-toggle" type="button" onClick={() => setVisible((value) => !value)} aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible}>
        {visible ? <EyeOff size={17} /> : <Eye size={17} />}
      </button>
    </span>
  </label>;
}
