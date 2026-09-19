"""The acceptance criteria from the PRD, run against the shared ACL case."""

from __future__ import annotations

import pytest

from app.contracts import ClinicalEvidence, ExtractRequest
from app.extract import extract_clinical_evidence


@pytest.fixture(scope="module")
def request_model(sample_input) -> ExtractRequest:
    return ExtractRequest.model_validate(sample_input)


@pytest.fixture(scope="module")
def evidence(request_model) -> ClinicalEvidence:
    return extract_clinical_evidence(request_model).evidence


def test_returns_schema_valid_clinical_evidence(evidence):
    ClinicalEvidence.model_validate(evidence.model_dump())


def test_echoes_patient_and_procedure(evidence):
    assert evidence.patient_id == "P001"
    assert evidence.procedure == "ACL_RECONSTRUCTION"
    assert evidence.diagnosis == "ACL tear"


def test_mri_is_extracted_as_confirmed(evidence):
    assert evidence.evidence.mri_confirmed is True


def test_pt_weeks_is_8_not_the_12_that_were_only_planned(evidence):
    assert evidence.evidence.physical_therapy_weeks == 8


def test_persistent_instability_is_true(evidence):
    assert evidence.evidence.persistent_instability is True


def test_nsaid_trial_is_true(evidence):
    assert evidence.evidence.nsaid_trial is True


def test_recent_physical_exam_is_false_because_the_only_exam_is_stale(evidence):
    assert evidence.evidence.recent_physical_exam is False


def test_every_positive_fact_carries_provenance(evidence):
    cited = {source.source_id for source in evidence.sources}
    assert "mri_01" in cited, "MRI finding must be cited"
    assert "pt_note_01" in cited, "PT duration must be cited"
    assert "med_hx_01" in cited, "NSAID trial must be cited"

    for source in evidence.sources:
        assert source.fact.strip()
        assert source.source_label.strip()
        assert source.location.strip()


def test_citations_point_at_supplied_documents(evidence, request_model):
    supplied = {doc.source_id for doc in request_model.documents}
    for source in evidence.sources:
        assert source.source_id in supplied, f"unknown source_id {source.source_id}"


def test_committed_example_output_is_in_sync(evidence, sample_output):
    assert evidence.model_dump() == sample_output


def test_extraction_is_deterministic(evidence, request_model):
    again = extract_clinical_evidence(request_model).evidence
    assert again.model_dump_json() == evidence.model_dump_json()
