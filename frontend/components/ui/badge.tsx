import { cn } from "@/lib/utils";

export function Badge({ children, tone = "neutral", className }: { children: React.ReactNode; tone?: "neutral" | "allow" | "deny" | "approval" | "info"; className?: string }) {
  const toneClass = tone === "allow" ? "decision-allow" : tone === "deny" ? "decision-deny" : tone === "approval" ? "decision-approval" : tone === "info" ? "text-accent" : "text-mute";
  return <span className={cn("inline-flex items-center rounded-sm border border-current px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide", toneClass, className)}>{children}</span>;
}
