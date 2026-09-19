# AccessGraph Orchestrator

The orchestrator is the single API boundary for the HCP frontend. It owns the synthetic ACL demo state and performs deterministic policy-to-evidence evaluation.

## Run

```sh
cd services/orchestrator
python -m venv .venv
. .venv/bin/activate # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

## Demo progression

1. `POST /analyze-case` returns 5 of 7 satisfied. PT is 35 of 42 required days; functional instability is `UNKNOWN`.
2. `POST /cases/P001/confirm-instability` requires human confirmation and moves the case to 6 of 7.
3. `POST /agents/pt-agent/verify` simulates ANS verification.
4. `POST /cases/P001/external-pt-evidence` accepts a verified 14-day record and moves the case to `READY_FOR_REVIEW`.
5. `GET /cases/P001/audit` shows the deterministic audit timeline.

## Case Guide side agent

`POST /case-assistant` accepts the same case selection as `/analyze-case` plus
a `question`. It returns deterministic, source-aware guidance based only on the
current `AuthorizationResult`. The endpoint is read-only: it cannot confirm
findings, attach records, or submit a case. Its response explicitly states that
readiness guidance is not coverage or insurer authorization.

Synthetic data only. This is readiness support, not an insurer decision engine.
