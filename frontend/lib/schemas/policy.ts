import { z } from "zod";
import YAML from "yaml";

const effectSchema = z.enum(["allow", "deny", "require_approval"]);
const ruleSchema = z.object({
  id: z.string().min(2),
  match: z.object({
    tool: z.string().min(2),
    conditions: z.record(z.unknown()).optional()
  }),
  effect: effectSchema
});

export const policyYamlSchema = z.array(ruleSchema).min(1);

export function validatePolicyYaml(value: string) {
  try {
    const parsed = YAML.parse(value);
    const result = policyYamlSchema.safeParse(parsed);
    if (!result.success) return { ok: false as const, message: result.error.issues.map((issue) => `${issue.path.join(".") || "policy"}: ${issue.message}`).join("; ") };
    return { ok: true as const, data: result.data };
  } catch (error) {
    return { ok: false as const, message: error instanceof Error ? error.message : "Invalid YAML" };
  }
}
