# AccessGraph HCP frontend

Self-contained React + TypeScript + Vite module for Person 1. All implementation lives in `charan's work/`; no service code or shared contracts are modified. Node.js 22.12+ is recommended.

## Run independently

```sh
cd "charan's work"
npm ci
npm run dev
```

Open http://127.0.0.1:5173. No backend, credentials, or environment file is required for the default synthetic demo.

```sh
npm run build       # TypeScript validation + production bundle in dist/
npm run preview     # Serve the production build locally
npm test            # Contract, error handling, and presentation tests
npm run test:e2e    # Browser flow and intercepted live-HTTP contract tests
```

Browser tests use installed Google Chrome and start two local Vite servers (5173 and 5174). Install Chrome, or change `channel: 'chrome'` in `playwright.config.ts` to use an installed Playwright Chromium browser. No tests call a real external service.

## Switch to the Orchestrator: one configuration change

Create `.env.local` with one variable, then restart Vite (or rebuild for production):

```dotenv
VITE_ORCHESTRATOR_URL=http://127.0.0.1:8000
```

Blank or unset uses the deterministic local mock. A nonempty origin uses **only** `POST {origin}/analyze-case`; there is no silent fallback to mock results when a live request fails. The service must permit CORS from the frontend origin and accept JSON. Do not put credentials in `VITE_` variables; those are public build-time values.

The request contains exactly:

```json
{
  "patient_id": "P001",
  "procedure": "ACL_RECONSTRUCTION",
  "insurer": "ExampleHealth PPO"
}
```

The frontend consumes the canonical `AuthorizationResult`. `src/lib/contracts.ts` validates fields, ranges, identities, counts, and duplicate criterion IDs; `src/lib/api.ts` verifies the returned patient and procedure match the request. No UI component consumes `ClinicalEvidence` or `PolicyRequirements`, calculates readiness, matches evidence, estimates cost, or verifies identities. All those values come from the result.

Sample input: `src/mocks/analyzeCaseRequest.json`.
Sample output: **`src/mocks/authorizationResult.json`** (the canonical shape, expanded to all four criterion explanations).
Synthetic source fixtures: `public/samples/clinical-records.txt` and `public/samples/acl-policy.txt`.

## Demo script

1. Open the app: Synthetic Patient A, ACL reconstruction, and ExampleHealth PPO are preselected.
2. Click **Analyze Authorization Readiness**. The six-step animation illustrates the workflow; it does not claim to stream agent telemetry.
3. See **75%** readiness, **3 of 4** requirements met, and **Needs more evidence**.
4. The most prominent next action requests the most recent orthopedic physical exam note.
5. Review the **$1,200–$1,700** synthetic estimate and the simulated provider/insurer verification statuses.
6. Open **Conservative treatment** to see 8 weeks of PT compared with the 6-week requirement and both references.
7. Open **Review missing evidence** to inspect the physical exam gap and recommended action.

The UI describes criteria alignment, never a guaranteed chance of insurer approval. Only the shared ACL case is currently selectable. Additional cases need registered case/plan options and corresponding Orchestrator support.

## Integration limits handled explicitly

- **Source citations:** The canonical `AuthorizationResult` does not include dedicated source fields. The mock includes optional `[Source: label, location]` citations inside the existing `patient_evidence` and `payer_requirement` strings. The UI displays those references when present. Plain canonical strings also work and show “source reference not supplied.” There is no lookup into Clinical Agent or Policy Agent data and no fabricated live citations. Structured references require a future team-approved contract extension.
- **Uploads:** The canonical request has no upload field or ingestion endpoint. Optional PDF/TXT selection therefore provides local review only. TXT contents can be previewed; PDFs are listed by filename and size. Files stay in memory, are not sent to any service, and do not affect the mock or readiness. The UI explicitly directs users to their clinical records workflow to update registered case evidence. A real upload flow requires an Orchestrator-owned ingestion contract.
- **Identity unavailable:** Canonical identity fields are booleans. `false` is displayed as “Not verified,” with an explanation that verification may be unavailable. Missing/null identity objects are malformed responses; the frontend does not invent new nullable shared fields.
- **Partial results:** Schema-valid partial results remain usable. Abbreviated explanations (including the PRD’s one-explanation example) display the supplied details, explicit missing requirements, and a partial-details notice. Unexplained criteria are not labeled satisfied. The frontend never recalculates readiness from visible rows.
- **Failures:** Network/HTTP failures, invalid JSON, inconsistent results, wrong-patient results, and 30-second timeouts preserve case selections and offer retry. Optional non-2xx `{ "code": "NO_POLICY" }` or `{ "code": "NO_CLINICAL_EVIDENCE" }` envelopes produce specific guidance; unknown envelopes produce a generic service error. Successful canonical results with those statuses also display guidance. The PRD does not define a mandatory error envelope.

## Components and review behavior

`CaseSetup.tsx`: CaseSelector, ProcedureSelector, InsurerSelector, AnalyzeButton.
`ProcessingStepper.tsx`: ProcessingStepper.
`ResultCards.tsx`: ReadinessCard, CriteriaChecklist, MissingEvidenceCard, CostEstimateCard, IdentityVerificationCard, NextBestActionCard.
`Dialogs.tsx`: EvidenceExplanationDrawer, source document/local record preview, demo guide.

Native modal dialogs provide keyboard focus containment, Escape dismissal, and focus restoration. The layout supports mobile, reduced motion, and printing. State stays in memory; there is no database or browser-storage persistence. Fonts are bundled locally. The mock communicates simulated identity and cost results explicitly.

## Team handoff

This module is self-contained in `charan's work/`. Keep the existing field names. Set the Orchestrator origin and allow CORS to integrate. No deployment, push, or merge is performed by running this module.
