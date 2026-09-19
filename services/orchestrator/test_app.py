from fastapi.testclient import TestClient

from app import app, reset_state

client = TestClient(app)


def setup_function():
    reset_state()


def test_initial_case_is_blocked_by_one_unsatisfied_and_one_unknown_requirement():
    result = client.post("/analyze-case", json={
        "patient_id": "P001", "procedure": "ACL_RECONSTRUCTION", "insurer": "ExampleHealth PPO",
    })
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "BLOCKED"
    assert (body["requirements_met"], body["requirements_total"]) == (5, 7)
    assert {item["result"] for item in body["explanations"]} >= {"SATISFIED", "UNSATISFIED", "UNKNOWN"}


def test_verified_external_evidence_moves_case_to_ready():
    assert client.post("/cases/P001/confirm-instability").json()["requirements_met"] == 6
    blocked = client.post("/cases/P001/external-pt-evidence")
    assert blocked.status_code == 403
    assert client.post("/agents/pt-agent/verify").json()["verified"] is True
    ready = client.post("/cases/P001/external-pt-evidence")
    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "READY_FOR_REVIEW"
    assert body["requirements_met"] == 7
    assert body["identity_status"]["provider_agent_verified"] is True


def test_audit_trail_records_the_state_transition():
    client.post("/cases/P001/confirm-instability")
    client.post("/agents/pt-agent/verify")
    client.post("/cases/P001/external-pt-evidence")
    events = client.get("/cases/P001/audit").json()
    assert [event["event"] for event in events][-3:] == [
        "EVIDENCE_FOUND", "REQUIREMENT_SATISFIED", "CASE_READY"
    ]
