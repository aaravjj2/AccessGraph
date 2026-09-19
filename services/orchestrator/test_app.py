from fastapi.testclient import TestClient

from app import app, reset_state

client = TestClient(app)
VALID = {"patient_id": "P001", "procedure": "ACL_RECONSTRUCTION", "insurer": "ExampleHealth PPO"}


def setup_function():
    reset_state()


def analyze():
    return client.post("/analyze-case", json=VALID)


def test_health_declares_synthetic_boundary():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["synthetic_data_only"] is True


def test_initial_case_has_seven_explainable_requirements():
    body = analyze().json()
    assert body["status"] == "BLOCKED"
    assert (body["requirements_met"], body["requirements_total"]) == (5, 7)
    assert {item["result"] for item in body["explanations"]} == {"SATISFIED", "UNSATISFIED", "UNKNOWN"}
    assert len({item["criterion_id"] for item in body["explanations"]}) == 7
    assert all("[Source:" in item["patient_evidence"] for item in body["explanations"])


def test_initial_blocking_set_is_minimal_and_ordered():
    missing = analyze().json()["missing_requirements"]
    assert [item["criterion_id"] for item in missing] == ["FUNCTIONAL_INSTABILITY", "PT_DURATION"]


def test_case_assistant_explains_missing_evidence_with_existing_citations():
    response = client.post("/case-assistant", json={**VALID, "question": "What is blocking this case?"})
    assert response.status_code == 200
    body = response.json()
    assert "5 of 7" in body["answer"]
    assert "Confirm the positive Lachman finding" in body["answer"]
    assert "PT Encounter Timeline, synthetic" in body["citations"]
    assert "does not determine coverage" in body["disclaimer"]


def test_case_assistant_answers_cost_without_claiming_coverage():
    response = client.post("/case-assistant", json={**VALID, "question": "What will the patient pay?"})
    assert response.status_code == 200
    assert "$1,450–$1,900 USD" in response.json()["answer"]
    assert "does not determine coverage" in response.json()["disclaimer"]


def test_case_assistant_requires_a_valid_case_and_question():
    invalid_case = client.post("/case-assistant", json={**VALID, "patient_id": "P404", "question": "What is missing?"})
    invalid_question = client.post("/case-assistant", json=VALID)
    assert invalid_case.status_code == 422
    assert invalid_case.json()["code"] == "NO_CLINICAL_EVIDENCE"
    assert invalid_question.status_code == 400
    assert invalid_question.json()["code"] == "INVALID_REQUEST"


def test_unknown_case_and_policy_use_machine_readable_errors():
    wrong_case = client.post("/analyze-case", json={**VALID, "patient_id": "P404"})
    wrong_policy = client.post("/analyze-case", json={**VALID, "insurer": "Other"})
    assert wrong_case.status_code == 422
    assert wrong_case.json()["code"] == "NO_CLINICAL_EVIDENCE"
    assert wrong_policy.status_code == 422
    assert wrong_policy.json()["code"] == "NO_POLICY"


def test_invalid_payload_never_returns_fastapi_default_error_shape():
    response = client.post("/analyze-case", json={"patient_id": "P001"})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_unverified_agent_cannot_mutate_case_state():
    denied = client.post("/cases/P001/external-pt-evidence")
    assert denied.status_code == 403
    assert denied.json()["code"] == "UNVERIFIED_AGENT"
    body = analyze().json()
    assert body["requirements_met"] == 5
    assert body["identity_status"]["provider_agent_verified"] is False


def test_confirmation_is_idempotent_and_only_changes_one_requirement():
    first = client.post("/cases/P001/confirm-instability").json()
    second = client.post("/cases/P001/confirm-instability").json()
    assert first["requirements_met"] == second["requirements_met"] == 6
    audit = client.get("/cases/P001/audit").json()
    assert [event["event"] for event in audit].count("HUMAN_EVIDENCE_CONFIRMATION") == 1


def test_verified_external_evidence_moves_case_to_ready():
    client.post("/cases/P001/confirm-instability")
    assert client.post("/agents/pt-agent/verify").json()["verified"] is True
    body = client.post("/cases/P001/external-pt-evidence").json()
    assert body["status"] == "READY_FOR_REVIEW"
    assert body["requirements_met"] == body["requirements_total"] == 7
    assert body["missing_requirements"] == []
    assert body["identity_status"]["provider_agent_verified"] is True


def test_external_evidence_is_idempotent():
    client.post("/cases/P001/confirm-instability")
    client.post("/agents/pt-agent/verify")
    client.post("/cases/P001/external-pt-evidence")
    client.post("/cases/P001/external-pt-evidence")
    events = client.get("/cases/P001/audit").json()
    assert [event["event"] for event in events].count("EVIDENCE_FOUND") == 1
    assert [event["event"] for event in events][-3:] == ["EVIDENCE_FOUND", "REQUIREMENT_SATISFIED", "CASE_READY"]


def test_reset_restores_initial_state_and_audit_baseline():
    client.post("/cases/P001/confirm-instability")
    client.post("/agents/pt-agent/verify")
    client.post("/cases/P001/reset")
    body = analyze().json()
    assert (body["requirements_met"], body["requirements_total"]) == (5, 7)
    assert body["identity_status"]["provider_agent_verified"] is False
    assert [event["event"] for event in client.get("/cases/P001/audit").json()] == ["CASE_CREATED", "POLICY_LOADED"]


def test_unknown_case_routes_have_consistent_error_envelope():
    for endpoint in ["/cases/nope/audit", "/cases/nope/reset", "/cases/nope/confirm-instability"]:
        response = client.post(endpoint) if endpoint.endswith(("reset", "confirm-instability")) else client.get(endpoint)
        assert response.status_code == 404
        assert response.json()["code"] == "CASE_NOT_FOUND"


def test_cors_preflight_allows_the_hcp_frontend_only():
    allowed = client.options("/analyze-case", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"})
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
