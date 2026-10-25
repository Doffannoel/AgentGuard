import type { ReplayCase } from "@/lib/types";
import { DecisionBadge } from "@/components/shell/decision";

export function ReplayCaseRow({ item }: { item: ReplayCase }) {
  return (
    <div className="grid gap-4 py-4 lg:grid-cols-[150px_1.4fr_1fr_100px] lg:items-center">
      <div><div className="text-xs font-bold">{item.suite}</div><div className="mt-1 text-[11px] text-mute">{item.attack}</div></div>
      <div className="text-xs leading-6 text-mute">“{item.input}”</div>
      <div className="grid grid-cols-2 gap-3 text-xs"><div><div className="kicker">Expected</div><div className="mt-1 font-bold">{item.expectedTool}</div><div className="mt-2"><DecisionBadge decision={item.expectedDecision} /></div></div><div><div className="kicker">Actual</div><div className="mt-1 font-bold">{item.actualTool || "Not run"}</div><div className="mt-2">{item.actualDecision && <DecisionBadge decision={item.actualDecision} />}</div></div></div>
      <div className={item.passed ? "decision-allow text-xs font-bold" : "text-xs font-bold"}>{item.passed === null ? "[-] NOT RUN" : item.passed ? "[+] PASS" : "[x] FAIL"}</div>
    </div>
  );
}
