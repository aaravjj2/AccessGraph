import { z } from "zod";

const text = z.string().trim().min(1);
export const analyzeCaseRequestSchema = z.object({
  patient_id: text,
  procedure: text,
  insurer: text,
});

export const authorizationResultSchema = z
  .object({
    patient_id: text,
    procedure: text,
    status: text,
    authorization_readiness: z.number().finite().min(0).max(1),
    requirements_met: z.number().int().nonnegative(),
    requirements_total: z.number().int().nonnegative(),
    missing_requirements: z.array(
      z.object({
        criterion_id: text,
        description: text,
        recommended_action: text,
      }),
    ),
    estimated_patient_cost: z
      .object({
        low: z.number().finite().nonnegative(),
        high: z.number().finite().nonnegative(),
        currency: text.regex(/^[A-Z]{3}$/),
        basis: text,
      })
      .refine((cost) => cost.low <= cost.high, "Cost range must be ordered"),
    identity_status: z.object({
      provider_agent_verified: z.boolean(),
      insurer_agent_verified: z.boolean(),
    }),
    explanations: z.array(
      z.object({
        criterion_id: text,
        patient_evidence: text,
        payer_requirement: text,
        result: text,
      }),
    ),
  })
  .superRefine((result, ctx) => {
    const criterionIds = new Set([
      ...result.explanations.map((item) => item.criterion_id),
      ...result.missing_requirements.map((item) => item.criterion_id),
    ]);
    if (
      criterionIds.size > result.requirements_total ||
      result.explanations.filter((item) => item.result === "SATISFIED").length >
        result.requirements_met
    ) {
      ctx.addIssue({
        code: "custom",
        message: "Explanations conflict with requirement counts",
      });
    }
    if (result.requirements_met > result.requirements_total) {
      ctx.addIssue({
        code: "custom",
        message: "Met requirements exceed total",
      });
    }
    if (
      result.missing_requirements.length >
      result.requirements_total - result.requirements_met
    ) {
      ctx.addIssue({
        code: "custom",
        message: "Missing requirements conflict with counts",
      });
    }
    for (const entries of [result.explanations, result.missing_requirements]) {
      if (
        new Set(entries.map((item) => item.criterion_id)).size !==
        entries.length
      ) {
        ctx.addIssue({ code: "custom", message: "Duplicate criterion IDs" });
      }
    }
    if (
      result.explanations.some(
        (item) =>
          item.result === "SATISFIED" &&
          result.missing_requirements.some(
            (missing) => missing.criterion_id === item.criterion_id,
          ),
      )
    ) {
      ctx.addIssue({
        code: "custom",
        message: "Satisfied criterion is also missing",
      });
    }
  });

export type AnalyzeCaseRequest = z.infer<typeof analyzeCaseRequestSchema>;
export type AuthorizationResult = z.infer<typeof authorizationResultSchema>;
export type Explanation = AuthorizationResult["explanations"][number];
export type MissingRequirement =
  AuthorizationResult["missing_requirements"][number];
