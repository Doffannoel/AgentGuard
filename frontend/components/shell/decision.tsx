import type { Decision } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

export function DecisionBadge({ decision }: { decision: Decision }) {
  const tone = decision === "ALLOW" ? "allow" : decision === "DENY" ? "deny" : "approval";
  return <Badge tone={tone}>{decision.replace("REQUIRE_", "")}</Badge>;
}
