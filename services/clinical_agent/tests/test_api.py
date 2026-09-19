"""The HTTP surface the Orchestrator integrates against, plus the QC UI."""

from __future__ import annotations


# --------------------------------------------------------------------------
# POST /clinical/extract
# --------------------------------------------------------------------------


def test_returns_the_shared_acl_case_exactly_as_committed(client, sample_input, sample_output):
    response = client.post("/clinical/extract", json=sample_input)
    assert response.status_code == 200
    assert response.json() == sample_output


def test_tolerates_unknown_request_keys(client, sample_input, sample_output):
    response = client.post(
        "/clinical/extract",
        json={**sample_input, "correlation_id": "abc-123", "requested_by": "orchestrator"},
    )
    assert response.status_code == 200
    assert response.json() == sample_output


def test_never_returns_keys_outside_the_contract(client, sample_input):
    response = client.post("/clinical/extract", json=sample_input)
    assert sorted(response.json()) == [
        "diagnosis",
        "evidence",
        "patient_id",
        "procedure",
        "sources",
    ]


# --------------------------------------------------------------------------
# Error contract
# --------------------------------------------------------------------------


def test_a_missing_field_is_a_400_with_details(client):
    response = client.post("/clinical/extract", json={"procedure": "ACL_RECONSTRUCTION"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert len(body["error"]["details"]) > 0


def test_an_empty_document_list_is_rejected(client):
    response = client.post(
        "/clinical/extract",
        json={"patient_id": "P001", "procedure": "ACL_RECONSTRUCTION", "documents": []},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_an_unsupported_procedure_is_a_422(client, sample_input):
    response = client.post(
        "/clinical/extract", json={**sample_input, "procedure": "HIP_REPLACEMENT"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_PROCEDURE"


def test_malformed_json_is_a_400_not_a_stack_trace(client):
    response = client.post(
        "/clinical/extract",
        content=b"{ not json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_an_unknown_route_returns_the_same_error_shape(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# --------------------------------------------------------------------------
# Service metadata
# --------------------------------------------------------------------------


def test_health_reports_the_supported_procedures(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["supported_procedures"] == ["ACL_RECONSTRUCTION"]


def test_the_published_schema_describes_clinical_evidence(client):
    response = client.get("/clinical/schema")
    assert response.status_code == 200
    assert sorted(response.json()["required"]) == [
        "diagnosis",
        "evidence",
        "patient_id",
        "procedure",
        "sources",
    ]


def test_the_debug_endpoint_explains_the_decisions(client, sample_input):
    response = client.post("/clinical/extract/debug", json=sample_input)
    assert response.status_code == 200
    trace = response.json()["trace"]
    assert any("planned rather than completed" in entry["decision"] for entry in trace)


# --------------------------------------------------------------------------
# QC UI
# --------------------------------------------------------------------------


def test_the_ui_is_served_at_the_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "QC Console" in response.text


def test_the_ui_can_fetch_the_sample_case(client, sample_input):
    response = client.get("/ui/sample-case")
    assert response.status_code == 200
    assert response.json() == sample_input
