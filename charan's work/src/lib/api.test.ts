import { describe, expect, it, vi } from "vitest";
import fixture from "../mocks/authorizationResult.json";
import request from "../mocks/analyzeCaseRequest.json";
import { AnalysisError, analyzeCase, parseAuthorizationResult } from "./api";
import { analysisNotice, criteriaFor, narrative } from "./presentation";

describe("canonical Orchestrator boundary", () => {
  it("returns deterministic isolated mock data with the shared ACL result", async () => {
    const first = await analyzeCase(request, { baseUrl: "" });
    const second = await analyzeCase(request, { baseUrl: "" });
    expect(first).toEqual(fixture);
    expect(second).toEqual(first);
    first.missing_requirements.length = 0;
    expect(second.missing_requirements).toHaveLength(2);
    expect(second.authorization_readiness).toBeCloseTo(0.7143);
    expect(second.status).toBe("BLOCKED");
  });

  it("calls only POST /analyze-case with exactly the three canonical fields", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(fixture)));
    await analyzeCase(request, {
      baseUrl: "https://orchestrator.example/",
      fetcher,
    });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher).toHaveBeenCalledWith(
      "https://orchestrator.example/analyze-case",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(request),
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
      }),
    );
  });

  it.each([
    ["wrong patient", { ...fixture, patient_id: "P999" }],
    ["wrong procedure", { ...fixture, procedure: "OTHER" }],
    ["unbounded readiness", { ...fixture, authorization_readiness: 1.5 }],
    ["inconsistent counts", { ...fixture, requirements_met: 8 }],
    [
      "reversed cost",
      {
        ...fixture,
        estimated_patient_cost: {
          ...fixture.estimated_patient_cost,
          low: 2000,
        },
      },
    ],
    ["missing identity", { ...fixture, identity_status: null }],
    ["malformed explanations", { ...fixture, explanations: [null] }],
    [
      "duplicate criterion",
      {
        ...fixture,
        explanations: [...fixture.explanations, fixture.explanations[0]],
      },
    ],
  ])("rejects %s without exposing raw response data", (_name, data) => {
    expect(() => parseAuthorizationResult(data, request)).toThrow(
      "MALFORMED_RESPONSE",
    );
  });

  it.each([
    ["NO_POLICY", "NO_POLICY"],
    ["NO_CLINICAL_EVIDENCE", "NO_CLINICAL_EVIDENCE"],
    ["UNKNOWN", "UNAVAILABLE"],
  ])("handles service error %s", async (code, expected) => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        new Response(JSON.stringify({ code }), { status: 422 }),
      );
    await expect(
      analyzeCase(request, {
        baseUrl: "https://orchestrator.example",
        fetcher,
      }),
    ).rejects.toMatchObject({ code: expected });
  });

  it("handles unavailable backends and malformed JSON separately", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(
      analyzeCase(request, {
        baseUrl: "https://orchestrator.example",
        fetcher,
      }),
    ).rejects.toMatchObject({ code: "UNAVAILABLE" });
    fetcher.mockResolvedValue(new Response("<html>oops</html>"));
    await expect(
      analyzeCase(request, {
        baseUrl: "https://orchestrator.example",
        fetcher,
      }),
    ).rejects.toMatchObject({ code: "MALFORMED_RESPONSE" });
  });

  it("bounds long-running requests and preserves user cancellation", async () => {
    const fetcher: typeof fetch = (_url, init) =>
      new Promise((_resolve, reject) => {
        init?.signal?.addEventListener(
          "abort",
          () => reject(init.signal?.reason),
          { once: true },
        );
      });
    await expect(
      analyzeCase(request, {
        baseUrl: "https://orchestrator.example",
        fetcher,
        timeoutMs: 10,
      }),
    ).rejects.toMatchObject({ code: "TIMEOUT" });
    const controller = new AbortController();
    const pending = analyzeCase(request, {
      baseUrl: "https://orchestrator.example",
      fetcher,
      signal: controller.signal,
    });
    controller.abort();
    await expect(pending).rejects.not.toBeInstanceOf(AnalysisError);
  });
});

describe("explanations without backend coupling", () => {
  it("supports the original abbreviated canonical response as a partial detail view", () => {
    const partial = parseAuthorizationResult(
      { ...fixture, explanations: [fixture.explanations[1]] },
      request,
    );
    expect(criteriaFor(partial)).toHaveLength(3);
    expect(analysisNotice(partial)?.title).toContain("unavailable");
  });
  it("never invents sources absent from the response", () => {
    expect(narrative("8 weeks PT documented")).toEqual({
      text: "8 weeks PT documented",
      source: null,
    });
    expect(narrative(fixture.explanations[1].patient_evidence).source).toBe(
      "PT Progress Note, page 2",
    );
  });
  it("tolerates a valid unverified identity without marking it verified", () => {
    const result = parseAuthorizationResult(
      {
        ...fixture,
        identity_status: {
          provider_agent_verified: false,
          insurer_agent_verified: false,
        },
      },
      request,
    );
    expect(result.identity_status.provider_agent_verified).toBe(false);
  });
});
