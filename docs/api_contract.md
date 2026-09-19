# AccessGraph API Contract

Shared interface definitions. Field names here are load-bearing for all four
modules: renaming anything requires team approval.

| Service | Owner module | Port | Status |
| --- | --- | --- | --- |
| Orchestrator | `services/orchestrator` | 8000 | Not started |
| Policy Agent | `services/policy_agent` | 8001 | Implemented |
| Clinical Evidence Agent | `services/clinical_agent` | 8002 | Implemented |
| Identity / ANS | `services/identity` | — | Not started |

The frontend depends only on the Orchestrator. The Orchestrator is the only
service that combines outputs from the other modules.

## Policy Agent

The Policy Agent is independently addressable by the Orchestrator only.

```http
POST /policy/extract
Content-Type: application/json
```

Request:

```json
{
  "insurer": "ExampleHealth PPO",
  "procedure": "ACL_RECONSTRUCTION",
  "policy_version": "2026-09",
  "documents": [{
    "source_id": "policy_acl_2026_09",
    "source_label": "ACL Reconstruction Policy",
    "text": "Policy text"
  }]
}
```

Response conforms to `shared/schemas/policy_requirements.schema.json`:

```json
{
  "insurer": "ExampleHealth PPO",
  "procedure": "ACL_RECONSTRUCTION",
  "policy_version": "2026-09",
  "requirements": []
}
```

Every requirement must contain `criterion_id`, `description`, `type`, `required_value`, `source_label`, and `source_location`. The only supported requirement types are `boolean`, `numeric_min`, `numeric_max`, `categorical`, and `text_presence`.

`policy_version` is a string when supplied and `null` when unavailable. Consumers must not infer a version.

## Clinical Evidence Agent

Converts synthetic medical records into `ClinicalEvidence`. It performs no
scoring, no policy interpretation, and no cost estimation. Addressable by the
Orchestrator only.

```http
POST /clinical/extract
Content-Type: application/json
```

Request:

```json
{
  "patient_id": "P001",
  "procedure": "ACL_RECONSTRUCTION",
  "as_of_date": "2026-09-15",
  "recency_window_days": 90,
  "documents": [{
    "source_id": "mri_01",
    "source_label": "MRI Report",
    "document_date": "2026-07-20",
    "text": "MRI LEFT KNEE ..."
  }]
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `patient_id` | yes | Echoed back unchanged |
| `procedure` | yes | `ACL_RECONSTRUCTION` today; anything else returns `422` |
| `documents[]` | yes | At least one |
| `documents[].source_id` | yes | Used verbatim in `sources[].source_id` |
| `documents[].source_label` | yes | Human-readable, shown to the HCP |
| `documents[].text` | yes | Raw document text |
| `documents[].document_date` | no | `YYYY-MM-DD`. Drives exam recency |
| `documents[].location` | no | Overrides the derived `page N` citation |
| `as_of_date` | no | Reference date for recency. Defaults to the newest document date |
| `recency_window_days` | no | Defaults to `90` |

Unknown request keys are ignored, so the Orchestrator may add fields such as
`correlation_id` without breaking this service.

Response conforms to `shared/schemas/clinical_evidence.schema.json`:

```json
{
  "patient_id": "P001",
  "procedure": "ACL_RECONSTRUCTION",
  "diagnosis": "ACL tear",
  "evidence": {
    "mri_confirmed": true,
    "physical_therapy_weeks": 8,
    "persistent_instability": true,
    "nsaid_trial": true,
    "recent_physical_exam": false
  },
  "sources": [{
    "fact": "8 weeks physical therapy completed",
    "source_id": "pt_note_01",
    "source_label": "PT Progress Note",
    "location": "page 2"
  }]
}
```

`diagnosis` is required but nullable: the key is always present, so consumers
never have to distinguish "absent" from "no diagnosis documented". Absent
evidence is reported as `false`, `0`, or `null`, never as a positive finding.
`recent_physical_exam` is `false` for a stale or undated exam as well as a
missing one; when an exam is stale it is still cited, with its age, so the
Orchestrator can tell the HCP what to upload.

### Other routes

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/clinical/extract/debug` | `ClinicalEvidence` plus a decision trace. Debugging only, not a contract |
| `GET` | `/clinical/schema` | JSON Schema for `ClinicalEvidence` |
| `GET` | `/health` | Liveness and supported procedures |
| `GET` | `/` | Quality-check console. A developer tool, not the HCP frontend |
| `GET` | `/docs` | FastAPI interactive API docs |

### Guarantees the Orchestrator can rely on

1. The response always validates against `shared/schemas/clinical_evidence.schema.json`.
2. Extraction is deterministic: identical requests produce identical bytes. No
   model calls, no network, no wall-clock reads.
3. Absent evidence is never upgraded to a positive finding.
4. Every positive fact appears in `sources` with a `source_id` that was present
   in the request.
5. Failures use the error envelope below, never a stack trace or plain text.

## Error envelope

The Clinical Evidence Agent returns this shape for every failure:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Human-readable summary.",
    "details": [{ "path": "documents", "message": "List should have at least 1 item" }]
  }
}
```

Codes: `INVALID_REQUEST` (400), `NOT_FOUND` (404), `UNSUPPORTED_PROCEDURE`
(422), `SCHEMA_VIOLATION` (500), `INTERNAL_ERROR` (500).

## Pipeline

```text
HCP Frontend
    ↓
POST /analyze-case
    ↓
Orchestrator
    ├── Clinical Agent   POST :8002/clinical/extract  → ClinicalEvidence
    ├── Policy Agent     POST :8001/policy/extract    → PolicyRequirements
    ├── Identity / ANS   (owner to define)            → identity_status
    └── Cost + Evidence Matching
    ↓
AuthorizationResult
    ↓
Frontend
```
