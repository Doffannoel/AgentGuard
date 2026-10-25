"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/shell/app-shell";
import { PageHeading } from "@/components/shell/page-heading";
import { DecisionBadge } from "@/components/shell/decision";
import { PolicyRuleRow } from "@/components/policy/policy-rule-row";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { StatePanel } from "@/components/ui/state-panel";
import { Textarea } from "@/components/ui/textarea";
import { createPolicy, listPolicies, simulatePolicy, publishPolicyDocument } from "@/lib/api/policies";
import { validatePolicyYaml } from "@/lib/schemas/policy";
import type { Decision } from "@/lib/types";

const defaultYaml = `- id: large-refund\n  match:\n    tool: payment.refund\n    conditions:\n      amount:\n        gt: 500000\n  effect: require_approval`;

export function PoliciesPage({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const policies = useQuery({ queryKey: ["policies", projectId], queryFn: () => listPolicies(projectId) });
  const [mode, setMode] = useState<"simple" | "yaml">("simple");
  const [tool, setTool] = useState("payment.refund");
  const [condition, setCondition] = useState("amount > 500000");
  const [effect, setEffect] = useState<Decision>("REQUIRE_APPROVAL");
  const [yaml, setYaml] = useState(defaultYaml);
  const [simulation, setSimulation] = useState('{\n  "tool": "payment.refund",\n  "arguments": { "amount": 1000000 }\n}');
  const validation = useMemo(() => validatePolicyYaml(yaml), [yaml]);
  const create = useMutation({
    mutationFn: () => createPolicy(projectId, { tool, condition: condition || undefined, effect, enabled: true, description: "Created from simple editor" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["policies", projectId] })
  });
  const simulate = useMutation({
    mutationFn: async () => {
      const value = JSON.parse(simulation) as { tool: string; arguments: Record<string, unknown> };
      return simulatePolicy(projectId, value);
    }
  });
  const publish = useMutation({
    mutationFn: () => {
      if (!validation.ok) throw new Error(validation.message);
      return publishPolicyDocument(projectId, validation.data);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["policies", projectId] })
  });

  return (
    <AppShell projectId={projectId}>
      <div className="page-wrap">
        <PageHeading eyebrow="Policy decision point" title="Policies" description="Tool actions are evaluated with deterministic project policy. Decision order is DENY > REQUIRE_APPROVAL > ALLOW; tool actions default to deny when no allow rule matches." />

        {policies.isLoading ? <StatePanel state="loading" /> : policies.error ? <StatePanel state="error" /> : (
          <section>
            {(["ALLOW", "REQUIRE_APPROVAL", "DENY"] as Decision[]).map((decision) => (
              <div key={decision} className="mb-8 border-t border-hairline pt-3">
                <div className="section-label">[{decision === "ALLOW" ? "+" : decision === "DENY" ? "x" : "!"}] {decision === "REQUIRE_APPROVAL" ? "Approval Rules" : decision === "ALLOW" ? "Allow Rules" : "Deny Rules"}</div>
                <div className="hairline-list">
                  {policies.data?.filter((rule) => rule.effect === decision).map((rule) => <PolicyRuleRow key={rule.id} rule={rule} />)}
                </div>
              </div>
            ))}
          </section>
        )}

        {(create.error || publish.error) && <p role="alert" className="text-xs decision-deny">{String(create.error || publish.error)}</p>}
        <section className="mt-14 rule-section">
          <div className="flex items-center justify-between gap-4"><div><div className="section-label">[+] Policy editor</div><p className="text-xs text-mute">Frontend validates syntax for developer feedback; the backend remains the authoritative validator.</p></div><div className="flex border-b border-hairline-strong"><button className={`px-4 py-2 text-xs ${mode === "simple" ? "border-b-2 border-ink font-bold" : "text-mute"}`} onClick={() => setMode("simple")}>Simple UI</button><button className={`px-4 py-2 text-xs ${mode === "yaml" ? "border-b-2 border-ink font-bold" : "text-mute"}`} onClick={() => setMode("yaml")}>YAML</button></div></div>
          {mode === "simple" ? (
            <div className="mt-5 grid gap-4 border border-hairline p-5 md:grid-cols-3">
              <label className="text-xs font-bold">When tool<Input className="mt-2" value={tool} onChange={(e) => setTool(e.target.value)} /></label>
              <label className="text-xs font-bold">Condition<Input className="mt-2" value={condition} onChange={(e) => setCondition(e.target.value)} /></label>
              <label className="text-xs font-bold">Then<Select className="mt-2 w-full" value={effect} onChange={(e) => setEffect(e.target.value as Decision)}><option>ALLOW</option><option>REQUIRE_APPROVAL</option><option>DENY</option></Select></label>
              <div className="md:col-span-3 flex justify-end border-t border-hairline pt-4"><Button disabled={create.isPending || !tool} onClick={() => create.mutate()}>{create.isPending ? "Publishing…" : "Publish rule"}</Button></div>
            </div>
          ) : (
            <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_320px]">
              <Textarea className="min-h-64 font-mono" value={yaml} onChange={(e) => setYaml(e.target.value)} spellCheck={false} />
              <div className="border border-hairline p-4"><div className="kicker">Validation</div>{validation.ok ? <div className="mt-3 text-sm decision-allow">[+] valid policy syntax</div> : <div className="mt-3 text-sm decision-deny">[x] policy_invalid</div>}<p className="mt-3 text-xs leading-6 text-mute">{validation.ok ? `${validation.data.length} rule parsed by YAML + Zod.` : validation.message}</p><div className="mt-5 border-t border-hairline pt-4 text-xs text-mute">backend validation is still authoritative</div></div>
            </div>
          )}
        </section>

        {mode === "yaml" && <Button className="mt-3" disabled={!validation.ok || publish.isPending} onClick={() => publish.mutate()}>Publish YAML policy</Button>}
        {publish.isSuccess && <p role="status" className="mt-2 text-xs">Policy version published.</p>}
        <section className="mt-14 rule-section">
          <div className="section-label">[+] Test Policy</div>
          <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
            <div><Textarea className="min-h-44 font-mono" value={simulation} onChange={(e) => setSimulation(e.target.value)} spellCheck={false} /><Button className="mt-3" variant="secondary" disabled={simulate.isPending} onClick={() => simulate.mutate()}>{simulate.isPending ? "Evaluating…" : "Run simulation"}</Button>{simulate.isError && <div className="mt-3 text-xs decision-deny">[x] Input must be valid JSON.</div>}</div>
            <div className="border border-hairline p-5"><div className="kicker">Decision</div>{simulate.data ? <><div className="mt-4"><DecisionBadge decision={simulate.data.decision} /></div><div className="mt-6 kicker">Matched Rule</div><div className="mt-2 font-bold">{simulate.data.matchedRule}</div><p className="mt-3 text-xs leading-6 text-mute">{simulate.data.reason}</p></> : <div className="mt-4 text-sm text-mute">Run the policy against a structured tool request before publishing.</div>}</div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
