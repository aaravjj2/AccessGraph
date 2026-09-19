import fixture from "../mocks/authorizationResult.json";
import {
  analyzeCaseRequestSchema,
  authorizationResultSchema,
  caseAssistantRequestSchema,
  caseAssistantResponseSchema,
  type AnalyzeCaseRequest,
  type AuthorizationResult,
  type CaseAssistantResponse,
} from "./contracts";

export type AnalysisErrorCode =
  | "UNAVAILABLE"
  | "MALFORMED_RESPONSE"
  | "NO_POLICY"
  | "NO_CLINICAL_EVIDENCE"
  | "TIMEOUT";
export class AnalysisError extends Error {
  constructor(public readonly code: AnalysisErrorCode) {
    super(code);
    this.name = "AnalysisError";
  }
}

export const errorMessages: Record<AnalysisErrorCode, { title: string; detail: string }> = {
  UNAVAILABLE: { title: "We couldn’t reach the analysis service", detail: "Your case selections are saved here. Check the connection and try again." },
  MALFORMED_RESPONSE: { title: "The analysis could not be safely displayed", detail: "The service returned incomplete or inconsistent data. Try again or ask your team to check the analysis service." },
  NO_POLICY: { title: "No policy is available for this case", detail: "Confirm the procedure and insurance plan, then ask your team to make the matching payer policy available." },
  NO_CLINICAL_EVIDENCE: { title: "No clinical evidence was found", detail: "Ask your team to add clinical records to this patient’s registered case, then run the analysis again." },
  TIMEOUT: { title: "The analysis is taking longer than expected", detail: "The request timed out. Your case selections are still here; please try again." },
};

const configuredUrl = import.meta.env.VITE_ORCHESTRATOR_URL?.trim() ?? "";
export const isMockMode = !configuredUrl;
type MockStage = "initial" | "confirmed" | "verified" | "ready";
let mockStage: MockStage = "initial";

export function resetDemoState() {
  mockStage = "initial";
}

function mockResult(request: AnalyzeCaseRequest): AuthorizationResult {
  const result = structuredClone(fixture) as AuthorizationResult;
  const instability = result.explanations.find((item) => item.criterion_id === "FUNCTIONAL_INSTABILITY")!;
  const pt = result.explanations.find((item) => item.criterion_id === "PT_DURATION")!;
  if (mockStage !== "initial") {
    instability.result = "SATISFIED";
    instability.patient_evidence = "Clinician confirmed positive Lachman finding as functional instability. [Source: Orthopedic Note, page 1]";
    result.requirements_met = 6;
    result.authorization_readiness = 0.8571;
    result.missing_requirements = result.missing_requirements.filter((item) => item.criterion_id !== "FUNCTIONAL_INSTABILITY");
  }
  if (mockStage === "verified" || mockStage === "ready") result.identity_status.provider_agent_verified = true;
  if (mockStage === "ready") {
    pt.result = "SATISFIED";
    pt.patient_evidence = "49 documented days of conservative therapy after verified PT evidence. [Source: PT Agent Record, synthetic]";
    result.requirements_met = 7;
    result.authorization_readiness = 1;
    result.status = "READY_FOR_REVIEW";
    result.missing_requirements = [];
  }
  return parseAuthorizationResult(result, request);
}

function mockCaseAssistant(request: AnalyzeCaseRequest, question: string): CaseAssistantResponse {
  const result = mockResult(request);
  const normalized = question.toLowerCase();
  const disclaimer = "Case guidance is based on the available synthetic evidence and policy criteria. It does not determine coverage or insurer authorization.";
  const suggestions = ["What is blocking this case?", "What does the cost estimate mean?", "Which sources support the findings?"];
  const citationsFor = (ids: string[]) => result.explanations
    .filter(item => ids.includes(item.criterion_id))
    .flatMap(item => [item.patient_evidence, item.payer_requirement])
    .map(value => value.match(/\[Source:\s*([^\]]+)\]/)?.[1])
    .filter((value): value is string => Boolean(value))
    .filter((value, index, values) => values.indexOf(value) === index);

  if (/cost|price|out of pocket|deductible|pay/.test(normalized)) {
    const cost = result.estimated_patient_cost;
    return { answer: `The current synthetic estimate is $${cost.low.toLocaleString()}–$${cost.high.toLocaleString()} ${cost.currency}. It is based on ${cost.basis.toLowerCase()}; actual patient responsibility can change with benefits, billing, and coverage.`, citations: [], suggested_questions: suggestions, disclaimer };
  }
  if (/agent|identity|verify|trusted/.test(normalized)) {
    return { answer: `The synthetic provider/PT agent is ${result.identity_status.provider_agent_verified ? "verified" : "not yet verified"}; the synthetic insurer agent is ${result.identity_status.insurer_agent_verified ? "verified" : "not yet verified"}. Verification controls whether external PT evidence can enter this demo case.`, citations: [], suggested_questions: suggestions, disclaimer };
  }
  if (/source|document|policy|evidence|support/.test(normalized)) {
    return { answer: "The findings are backed by the source references listed below. Open a criterion in the case review to compare the patient evidence with the payer requirement.", citations: citationsFor(result.explanations.map(item => item.criterion_id)), suggested_questions: suggestions, disclaimer };
  }
  const missing = result.missing_requirements;
  return { answer: result.status === "READY_FOR_REVIEW" ? `All ${result.requirements_total} synthetic criteria are currently satisfied. The case is ready for human review, not guaranteed insurer approval.` : `The case is currently ${result.status.toLowerCase().replaceAll("_", " ")}: ${result.requirements_met} of ${result.requirements_total} criteria are satisfied. The next actions are: ${missing.map(item => item.recommended_action).join("; ")}.`, citations: citationsFor(missing.map(item => item.criterion_id)), suggested_questions: suggestions, disclaimer };
}

export function parseAuthorizationResult(data: unknown, request: AnalyzeCaseRequest): AuthorizationResult {
  const parsed = authorizationResultSchema.safeParse(data);
  if (!parsed.success || parsed.data.patient_id !== request.patient_id || parsed.data.procedure !== request.procedure) {
    throw new AnalysisError("MALFORMED_RESPONSE");
  }
  return parsed.data;
}

function origin(baseUrl?: string) {
  return (baseUrl ?? configuredUrl).replace(/\/$/, "");
}

async function requestJson(path: string, options: RequestInit = {}, baseUrl?: string): Promise<unknown> {
  const response = await fetch(`${origin(baseUrl)}${path}`, {
    ...options,
    headers: { Accept: "application/json", ...options.headers },
  });
  if (!response.ok) throw new AnalysisError("UNAVAILABLE");
  return response.json();
}

// This remains the only analysis boundary. The lifecycle methods below are
// explicit human and verified-agent actions owned by the orchestrator.
export async function analyzeCase(input: AnalyzeCaseRequest, options: {
  baseUrl?: string; signal?: AbortSignal; fetcher?: typeof fetch; timeoutMs?: number;
} = {}): Promise<AuthorizationResult> {
  const request = analyzeCaseRequestSchema.parse(input);
  const baseUrl = options.baseUrl ?? configuredUrl;
  if (!baseUrl) {
    options.signal?.throwIfAborted();
    if (request.insurer !== "ExampleHealth PPO") throw new AnalysisError("NO_POLICY");
    return mockResult(request);
  }
  const timeout = AbortSignal.timeout(options.timeoutMs ?? 30_000);
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
  try {
    const response = await (options.fetcher ?? fetch)(`${origin(baseUrl)}/analyze-case`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(request),
      signal,
    });
    if (!response.ok) {
      const error: unknown = await response.json().catch(() => null);
      const code = error && typeof error === "object" && "code" in error ? error.code : null;
      if (code === "NO_POLICY" || code === "NO_POLICY_AVAILABLE") throw new AnalysisError("NO_POLICY");
      if (code === "NO_CLINICAL_EVIDENCE" || code === "NO_EVIDENCE") throw new AnalysisError("NO_CLINICAL_EVIDENCE");
      throw new AnalysisError("UNAVAILABLE");
    }
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      throw new AnalysisError("MALFORMED_RESPONSE");
    }
    return parseAuthorizationResult(data, request);
  } catch (error) {
    if (options.signal?.aborted) throw error;
    if (timeout.aborted) throw new AnalysisError("TIMEOUT");
    if (error instanceof AnalysisError) throw error;
    throw new AnalysisError("UNAVAILABLE");
  }
}

export async function confirmInstability(request: AnalyzeCaseRequest): Promise<AuthorizationResult> {
  if (!configuredUrl) {
    mockStage = "confirmed";
    return mockResult(request);
  }
  return parseAuthorizationResult(
    await requestJson(`/cases/${request.patient_id}/confirm-instability`, { method: "POST" }),
    request,
  );
}

export async function verifyPtAgent(): Promise<boolean> {
  if (!configuredUrl) {
    mockStage = "verified";
    return true;
  }
  const value = await requestJson("/agents/pt-agent/verify", { method: "POST" }) as { verified?: boolean };
  return value.verified === true;
}

export async function addVerifiedPtEvidence(request: AnalyzeCaseRequest): Promise<AuthorizationResult> {
  if (!configuredUrl) {
    if (mockStage !== "verified") throw new AnalysisError("UNAVAILABLE");
    mockStage = "ready";
    return mockResult(request);
  }
  return parseAuthorizationResult(
    await requestJson(`/cases/${request.patient_id}/external-pt-evidence`, { method: "POST" }),
    request,
  );
}

export async function askCaseAssistant(input: AnalyzeCaseRequest, question: string): Promise<CaseAssistantResponse> {
  const request = caseAssistantRequestSchema.parse({ ...input, question });
  if (!configuredUrl) return mockCaseAssistant(request, request.question);
  const response = await requestJson("/case-assistant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  const parsed = caseAssistantResponseSchema.safeParse(response);
  if (!parsed.success) throw new AnalysisError("MALFORMED_RESPONSE");
  return parsed.data;
}
