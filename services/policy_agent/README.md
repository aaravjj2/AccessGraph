# AccessGraph Policy Agent

Converts supplied payer-policy text into the shared `PolicyRequirements` JSON contract. It is intentionally deterministic for the ACL reconstruction demo and never receives patient data, calculates readiness, estimates costs, or predicts authorization.

## Run

Requires Python 3.10+ and no third-party packages.

```powershell
cd services/policy_agent
python app.py
```

The service exposes a browser UI at `GET /`, health at `GET /health`, and extraction at `POST /policy/extract` on port `8001` (or `PORT`).

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/policy/extract -ContentType 'application/json' -InFile examples/acl_policy_input.json
```

Run the contract test:

```powershell
python -m unittest test_extractor.py
```

`examples/acl_policy_input.json` and `examples/acl_policy_output.json` are the integration fixture. The output has canonical fields: `insurer`, `procedure`, `policy_version`, and source-backed `requirements`.
