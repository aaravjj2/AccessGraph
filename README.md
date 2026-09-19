# AccessGraph

AccessGraph is an AI-powered prior-authorization intelligence layer for surgeons and clinical teams. It turns synthetic clinical evidence and payer policy documents into explainable authorization-readiness results. It does not guarantee insurer approval.

Results are framed as **authorization readiness / criteria match**, never as a probability of insurer approval.

## Module status

| Module | State | Stack | Port | Produces |
| --- | --- | --- | --- | --- |
| [Payer Policy Agent](services/policy_agent/README.md) | Implemented | Python (stdlib) | 8001 | `PolicyRequirements` |
| [Clinical Evidence Agent](services/clinical_agent/README.md) | Implemented | Python / FastAPI | 8002 | `ClinicalEvidence` |
| HCP Frontend (`charan's work/`) | In progress | React / Vite | 5173 | Talks only to the Orchestrator |
| Orchestrator | Not started | — | 8000 | `AuthorizationResult` |
| Identity / ANS | Not started | — | — | `identity_status` |

## Run the modules

### Payer Policy Agent

```powershell
cd services/policy_agent
python app.py
```

Open `http://127.0.0.1:8001/` for its demo UI.

### Clinical Evidence Agent

```powershell
cd services/clinical_agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

Open `http://127.0.0.1:8002/` for its quality-check console: one-click
scenarios, an editable case, expected-vs-actual grading, and the decision trace
behind every extracted fact. Run `pytest` for the 48-test suite.

## Monorepo layout

```text
accessgraph/
├── charan's work/               # HCP frontend (React + Vite)
├── services/
│   ├── policy_agent/            # Implemented Payer Policy Agent
│   ├── clinical_agent/          # Implemented Clinical Evidence Agent
│   ├── orchestrator/            # Not started
│   └── identity/                # Not started
├── shared/
│   ├── schemas/                 # Cross-service API schemas
│   ├── sample_data/             # Shared synthetic ACL fixtures
│   └── constants/               # Procedure codes and field names
└── docs/api_contract.md         # Integration contracts
```

## Shared ACL demo

All modules target this synthetic case first.

- Procedure: `ACL_RECONSTRUCTION`
- Patient: Synthetic Patient A (`P001`)
- Insurer: ExampleHealth PPO
- Clinical facts: MRI-confirmed ACL tear, 8 weeks of physical therapy, NSAIDs attempted, persistent knee instability
- Policy criteria: MRI confirmation, at least 6 weeks of conservative treatment, persistent functional instability, and a recent qualifying physical exam
- Expected result: most requirements satisfied, recent physical exam missing, so the case must **not** be shown as guaranteed approved

Expected output fixtures:

- `services/policy_agent/examples/acl_policy_output.json`
- `services/clinical_agent/examples/acl_case_output.json`

## Integration rules

1. Work inside this monorepo.
2. Respect the contracts in [`docs/api_contract.md`](docs/api_contract.md) exactly.
3. Do not rename shared fields without team approval.
4. Build against mocks when another module is unavailable.
5. Return deterministic, schema-valid JSON.
6. Keep module code inside your own folder.
7. Ship a README with local run instructions.
8. Ship at least one sample input and sample output.
9. Every module must start independently.
10. Merge often, and test the shared ACL case before adding more cases.

The frontend depends only on the Orchestrator. The Orchestrator is the only service that combines outputs from the other modules.
