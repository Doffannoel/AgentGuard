import type { PolicyRule } from "@/lib/types";
import { DecisionBadge } from "@/components/shell/decision";

export function PolicyRuleRow({ rule }: { rule: PolicyRule }) {
  return (
    <div className="grid gap-3 py-4 md:grid-cols-[190px_1fr_1fr_auto] md:items-center">
      <DecisionBadge decision={rule.effect} />
      <div><div className="font-bold">{rule.tool}</div><div className="mt-1 text-xs text-mute">{rule.id}</div></div>
      <div className="text-xs leading-6 text-mute">{rule.condition ?? rule.description}</div>
      <div className="text-xs text-mute">{rule.enabled ? "[+] enabled" : "[-] disabled"}</div>
    </div>
  );
}
