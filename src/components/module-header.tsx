import { modules } from "@/lib/modules";

export function ModuleHeader({ href }: { href: (typeof modules)[number]["href"] }) {
  const selectedModule = modules.find((item) => item.href === href);
  const Icon = selectedModule?.icon;
  return <div className="module-title"><span className="module-icon large">{Icon && <Icon size={22} />}</span><div><div className="eyebrow">WORKSPACE MODULE</div><h1>{selectedModule?.label}</h1><p className="muted">{selectedModule?.description}</p></div></div>;
}
