import type { AuthorizationResult, Explanation } from "./contracts";

const criterionLabels: Record<string, string> = {
  MRI_CONFIRMED: "MRI confirmation",
  PT_WEEKS: "Conservative treatment",
  PT_DURATION: "Conservative treatment duration",
  PERSISTENT_SYMPTOMS: "Persistent symptoms",
  FAILED_CONSERVATIVE_TREATMENT: "Failed conservative treatment",
  DIAGNOSIS_CODING: "Diagnosis coding",
  PERSISTENT_INSTABILITY: "Functional instability",
  RECENT_PHYSICAL_EXAM: "Recent physical exam",
};
export function humanize(value: string) {
  const label = value.replaceAll("_", " ").toLowerCase();
  return label.charAt(0).toUpperCase() + label.slice(1);
}
export const criterionLabel = (id: string) =>
  criterionLabels[id] ?? humanize(id);
export function statusLabel(status: string) {
  return (
    (
      {
        NEEDS_MORE_EVIDENCE: "Needs more evidence",
        BLOCKED: "Blocked",
        READY: "Ready for review",
        READY_FOR_SUBMISSION: "Ready for submission",
        PARTIAL_ANALYSIS: "Partial analysis",
        NO_POLICY: "No policy available",
        NO_POLICY_AVAILABLE: "No policy available",
        NO_CLINICAL_EVIDENCE: "No clinical evidence",
        NO_EVIDENCE: "No clinical evidence",
      } as Record<string, string>
    )[status] ?? humanize(status)
  );
}
// Optional textual citations preserve the canonical schema. Absent references
// remain absent: live responses never borrow citations from the demo fixture.
export function narrative(value: string) {
  const match = value.match(/\[Source:\s*([^\]]+)\]/);
  return {
    text: value.replace(/\s*\[Source:\s*[^\]]+\]/g, "").trim(),
    source: match?.[1] ?? null,
  };
}
export function criteriaFor(result: AuthorizationResult): Explanation[] {
  const items = [...result.explanations];
  for (const missing of result.missing_requirements) {
    if (!items.some((item) => item.criterion_id === missing.criterion_id)) {
      items.push({
        criterion_id: missing.criterion_id,
        patient_evidence: missing.description,
        payer_requirement: "Policy detail was not included in this analysis.",
        result: "MISSING",
      });
    }
  }
  return items;
}
export function analysisNotice(
  result: AuthorizationResult,
): { title: string; detail: string } | null {
  if (["NO_POLICY", "NO_POLICY_AVAILABLE"].includes(result.status))
    return {
      title: "No policy available",
      detail:
        "Confirm the selected plan and procedure. A matching payer policy is needed before readiness can be assessed.",
    };
  if (["NO_CLINICAL_EVIDENCE", "NO_EVIDENCE"].includes(result.status))
    return {
      title: "No clinical evidence found",
      detail:
        "Add records to the registered case through your clinical workflow, then analyze again.",
    };
  if (
    result.status.includes("PARTIAL") ||
    result.requirements_total === 0 ||
    criteriaFor(result).length < result.requirements_total
  )
    return {
      title: "Some analysis details are unavailable",
      detail:
        "Review the available findings below. Missing details are not evidence that a requirement was satisfied.",
    };
  return null;
}
export const hasNoAssessment = (result: AuthorizationResult) =>
  result.requirements_total === 0 ||
  [
    "NO_POLICY",
    "NO_POLICY_AVAILABLE",
    "NO_CLINICAL_EVIDENCE",
    "NO_EVIDENCE",
  ].includes(result.status);
