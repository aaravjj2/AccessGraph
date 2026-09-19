import fixture from "../mocks/authorizationResult.json";
import {
  analyzeCaseRequestSchema,
  authorizationResultSchema,
  type AnalyzeCaseRequest,
  type AuthorizationResult,
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
    return parseAuthorizationResult(structuredClone(fixture), request);
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
    return parseAuthorizationResult(await response.json(), request);
  } catch (error) {
    if (options.signal?.aborted) throw error;
    if (timeout.aborted) throw new AnalysisError("TIMEOUT");
    if (error instanceof AnalysisError) throw error;
    throw new AnalysisError("UNAVAILABLE");
  }
}

export async function confirmInstability(request: AnalyzeCaseRequest): Promise<AuthorizationResult> {
  if (!configuredUrl) throw new AnalysisError("UNAVAILABLE");
  return parseAuthorizationResult(
    await requestJson(`/cases/${request.patient_id}/confirm-instability`, { method: "POST" }),
    request,
  );
}

export async function verifyPtAgent(): Promise<boolean> {
  if (!configuredUrl) throw new AnalysisError("UNAVAILABLE");
  const value = await requestJson("/agents/pt-agent/verify", { method: "POST" }) as { verified?: boolean };
  return value.verified === true;
}

export async function addVerifiedPtEvidence(request: AnalyzeCaseRequest): Promise<AuthorizationResult> {
  if (!configuredUrl) throw new AnalysisError("UNAVAILABLE");
  return parseAuthorizationResult(
    await requestJson(`/cases/${request.patient_id}/external-pt-evidence`, { method: "POST" }),
    request,
  );
}
