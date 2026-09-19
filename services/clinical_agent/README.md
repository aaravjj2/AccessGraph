# Clinical Evidence Agent

Converts synthetic patient medical records into structured, source-backed
`ClinicalEvidence` JSON for the AccessGraph prior-authorization pipeline.

```text
clinical records  →  ClinicalEvidence JSON
```

This service does **not** decide anything about authorization. It does not score
readiness, interpret payer policy, or estimate cost. It reports what the records
say, with a citation for every fact.

Python 3.11+, FastAPI, Pydantic v2.

## Run it

```bash
cd services/clinical_agent
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

Then open **<http://localhost:8002/>** for the QC console.

| Command | What it does |
| --- | --- |
| `uvicorn app.main:app --reload --port 8002` | Run the service and the UI |
| `pytest` | Run the full suite (48 tests) |
| `python scripts/run_case.py examples/acl_case_input.json` | Extract without a server |
| `python scripts/run_case.py examples/acl_case_input.json --trace` | Show the reasoning |
| `python scripts/generate_schema.py` | Regenerate JSON Schemas and the example output |

## Quality-check console

`GET /` serves a self-contained page for exercising the agent by hand. It is a
developer tool, not the HCP-facing product — that is Person 4's frontend, which
talks to the Orchestrator rather than to this service.

It gives you:

- **Eight one-click scenarios**, each carrying its own expected result, so the
  page grades itself instead of making you eyeball JSON. Besides the shared ACL
  case they cover the adversarial inputs: a negated MRI, planned-only PT, an
  NSAID allergy, a failed NSAID trial, a recent exam, an undated exam, and a
  record with nothing relevant in it.
- **A fully editable case.** Change any document text, add or remove documents,
  move `as_of_date` or the recency window, and re-run.
- **Expected vs actual**, which also re-issues the request and compares bytes to
  confirm the determinism guarantee, and checks that every citation resolves to
  a document you actually supplied.
- **The decision trace**, grouped by field, green for accepted and red for
  rejected, quoting the exact sentence behind each call. The rejections are the
  interesting part: they are the guards against inventing evidence doing their
  job.
- **The raw contract response**, which is exactly what the Orchestrator receives.

## Try the shared ACL case from the command line

```bash
python scripts/run_case.py examples/acl_case_input.json
```

```bash
curl -X POST http://localhost:8002/clinical/extract \
  -H "Content-Type: application/json" \
  -d @examples/acl_case_input.json
```

PowerShell:

```powershell
Invoke-RestMethod -Uri http://localhost:8002/clinical/extract -Method Post `
  -ContentType 'application/json' `
  -InFile examples/acl_case_input.json | ConvertTo-Json -Depth 6
```

All three return `examples/acl_case_output.json`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/clinical/extract` | The contract. Returns exactly `ClinicalEvidence`. |
| `POST` | `/clinical/extract/debug` | Same extraction plus a decision trace. Not part of the contract. |
| `GET` | `/clinical/schema` | JSON Schema for `ClinicalEvidence`, so other modules can validate. |
| `GET` | `/health` | Liveness and the list of supported procedures. |
| `GET` | `/` | QC console. |
| `GET` | `/docs` | FastAPI's interactive API docs. |

### Request

```json
{
  "patient_id": "P001",
  "procedure": "ACL_RECONSTRUCTION",
  "documents": [
    { "source_id": "mri_01", "source_label": "MRI Report", "text": "..." }
  ]
}
```

Optional per document: `document_date` (`YYYY-MM-DD`) and `location` (overrides
the derived `page N` citation string).

Optional per request: `as_of_date` (reference date for recency) and
`recency_window_days` (defaults to 90).

Unknown keys in the request are ignored rather than rejected, so the Orchestrator
can add fields like `correlation_id` without a coordinated release. The response
is strict and will never contain keys outside `ClinicalEvidence`.

### Errors

Every failure has the same shape:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Request body does not match the clinical extract contract.",
    "details": [{ "path": "documents", "message": "List should have at least 1 item" }]
  }
}
```

| Code | Status | When |
| --- | --- | --- |
| `INVALID_REQUEST` | 400 | Body is not valid JSON, or fails the request contract |
| `UNSUPPORTED_PROCEDURE` | 422 | No extraction rule pack for that procedure |
| `NOT_FOUND` | 404 | Unknown route |
| `SCHEMA_VIOLATION` | 500 | Internal bug: extraction produced non-contract output |
| `INTERNAL_ERROR` | 500 | Anything else |

A procedure with no rule pack fails loudly instead of returning an all-negative
result that would look like real extracted evidence.

## How extraction works

Rules and regular expressions, no LLM and no network. The same request always
produces the same bytes, which is what makes the demo reproducible and the tests
meaningful. The Orchestrator cannot tell the difference and should not care.

Each document is split into pages (on form feeds or `Page N` marker lines) and
then into sentences, which is where citation locations come from. Six extractors
then run over those sentences:

| Field | Rule |
| --- | --- |
| `diagnosis` | Canonical `"ACL tear"` when a document states one as a fact, otherwise `null` |
| `mri_confirmed` | Requires an imaging *finding* of an ACL tear. Inside a report recognised as imaging, the findings are confirmatory by nature; elsewhere explicit confirmation language is required |
| `physical_therapy_weeks` | Longest *documented* course near therapy wording. Months convert at a conservative 4 weeks; a range takes its lower bound |
| `nsaid_trial` | A named NSAID or the drug class, excluding allergy and contraindication mentions |
| `persistent_instability` | Instability with a persistence cue, or instability documented in two or more independent documents |
| `recent_physical_exam` | A documented exam that can be *dated* inside the recency window |

Three guards keep the agent from inventing evidence, and they are the part worth
reviewing:

- **Negation** is scoped to the clause. `"denies numbness, but reports
  instability"` still yields instability, while `"no ACL tear identified"`
  yields nothing. Outcome negations are exempt: `"no relief from naproxen"` and
  `"failed NSAIDs"` both still mean the drug was tried.
- **Speculation and hedging** are rejected. A planned 12-week course of PT, a
  `"suspected"` tear, and an MRI that was merely ordered are not facts.
- **Recency** needs a date. An undated or stale exam stays `false`. When an exam
  is stale it is still cited, with its age, so the Orchestrator can tell the HCP
  exactly what to upload.

Absent evidence returns `false`, `0`, or `null`. It is never upgraded to a
positive finding.

### Case sensitivity note

`PT` in capitals means physical therapy; lowercase `pt` means patient. The
duration extractor honours that distinction, so `"the pt reports 10 weeks of
soreness"` does not become ten weeks of therapy.

## Adding a procedure

1. Add it to `SUPPORTED_PROCEDURES` in `app/contracts.py`.
2. Add or adjust extractors under `app/extractors/`.
3. Add an example pair under `examples/`, a scenario in the QC console, and a test.

Until step 1 happens, the service returns a `422` for that procedure rather than
guessing.

## Layout

```text
services/clinical_agent/
├── app/
│   ├── main.py             FastAPI routes and error mapping
│   ├── contracts.py        Pydantic models — the shared field names live here
│   ├── extract.py          Pipeline: prepare → extract → validate → return
│   ├── errors.py           The error envelope
│   ├── extractors/         One module per clinical fact
│   ├── text/               Segmentation, dates, negation and hedging
│   └── ui/index.html       QC console (no build step, no CDN)
├── examples/               Sample input and its exact output
├── scripts/                Offline runner and schema generation
└── tests/                  48 tests
```

## Tests

```bash
pytest
```

`tests/test_acceptance.py` is the PRD's acceptance criteria, including a check
that `examples/acl_case_output.json` still matches what the code produces, so
the committed example cannot drift. `tests/test_extraction.py` covers negation,
hedging and recency. `tests/test_api.py` covers the HTTP contract, the error
envelope, and the UI routes.
