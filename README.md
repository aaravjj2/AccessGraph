# AccessGraph

AccessGraph is an AI-powered prior-authorization intelligence layer for surgeons and clinical teams. It turns synthetic clinical evidence and payer policy documents into explainable authorization-readiness results. It does not guarantee insurer approval.

## Current module: Payer Policy Agent

This repository currently implements the Payer Policy Agent for the shared ACL reconstruction demo. It accepts payer policy text and produces source-backed `PolicyRequirements` JSON. It never processes patient records, calculates readiness, estimates cost, or predicts approvals.

Run it locally:

```powershell
cd services/policy_agent
python app.py
```

Open `http://127.0.0.1:8001/` for the demo UI. See the module [README](services/policy_agent/README.md) for API details.

## Monorepo layout

```text
accessgraph/
├── services/policy_agent/       # Implemented Payer Policy Agent
├── shared/schemas/              # Cross-service API schemas
├── shared/sample_data/          # Shared synthetic ACL policy fixture
└── docs/api_contract.md         # Integration contracts
```

## Shared ACL demo

- Procedure: `ACL_RECONSTRUCTION`
- Insurer: ExampleHealth PPO
- Policy criteria: MRI confirmation, at least 6 weeks of conservative treatment, persistent functional instability, and a recent qualifying physical exam.

The agent’s expected output fixture is at `services/policy_agent/examples/acl_policy_output.json`.
