import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: { default: "MediSphere AI", template: "%s · MediSphere AI" },
  description: "MediSphere AI unified healthcare workspace",
  applicationName: "MediSphere AI",
  icons: { icon: "/medisphere-mark.svg", shortcut: "/medisphere-mark.svg", apple: "/medisphere-mark.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
