"""Guards against the failure mode that matters most: inventing evidence."""

from __future__ import annotations

from app.contracts import ClinicalEvidence
from conftest import extract_from_text

EXAM_NOTE = "\n".join(
    [
        "ORTHOPEDIC OFFICE NOTE",
        "Physical Examination:",
        "Left knee with a small effusion. Lachman test positive. Anterior drawer positive.",
    ]
)


# --------------------------------------------------------------------------
# Negation
# --------------------------------------------------------------------------


def test_a_negative_mri_does_not_confirm_a_tear():
    evidence = extract_from_text(
        "MRI LEFT KNEE\nThe anterior cruciate ligament is intact. No ACL tear is identified.",
        source_label="MRI Report",
    )
    assert evidence.evidence.mri_confirmed is False
    assert evidence.diagnosis is None


def test_denied_instability_is_not_reported():
    evidence = extract_from_text(
        "The patient denies any persistent instability or giving way of the knee."
    )
    assert evidence.evidence.persistent_instability is False


def test_an_nsaid_allergy_is_not_a_trial():
    evidence = extract_from_text("Allergies: ibuprofen, causing urticaria.")
    assert evidence.evidence.nsaid_trial is False


def test_negation_does_not_reach_across_a_conjunction():
    evidence = extract_from_text(
        "The patient denies numbness, but reports persistent instability with pivoting."
    )
    assert evidence.evidence.persistent_instability is True


def test_failing_a_drug_still_counts_as_having_tried_it():
    evidence = extract_from_text("Naproxen was taken daily with no relief of symptoms.")
    assert evidence.evidence.nsaid_trial is True


# --------------------------------------------------------------------------
# Planned versus documented care
# --------------------------------------------------------------------------


def test_a_recommended_course_of_pt_is_not_a_completed_one():
    evidence = extract_from_text("Plan: recommend a 12 week course of physical therapy.")
    assert evidence.evidence.physical_therapy_weeks == 0


def test_a_hedged_diagnosis_is_not_a_documented_one():
    evidence = extract_from_text("Assessment: possible anterior cruciate ligament tear.")
    assert evidence.diagnosis is None


def test_an_mri_that_is_merely_ordered_confirms_nothing():
    evidence = extract_from_text("Will obtain an MRI to rule out an ACL tear.")
    assert evidence.evidence.mri_confirmed is False


# --------------------------------------------------------------------------
# Physical therapy duration
# --------------------------------------------------------------------------


def test_reads_a_completed_duration():
    evidence = extract_from_text("The patient completed 10 weeks of physical therapy.")
    assert evidence.evidence.physical_therapy_weeks == 10


def test_reads_spelled_out_numbers():
    evidence = extract_from_text("Completed eight weeks of supervised physiotherapy.")
    assert evidence.evidence.physical_therapy_weeks == 8


def test_converts_months_conservatively():
    evidence = extract_from_text("Underwent 3 months of formal physical therapy.")
    assert evidence.evidence.physical_therapy_weeks == 12


def test_takes_the_lower_bound_of_a_range():
    evidence = extract_from_text("Completed 6 to 8 weeks of physical therapy.")
    assert evidence.evidence.physical_therapy_weeks == 6


def test_ignores_durations_with_no_therapy_context():
    evidence = extract_from_text("The pt reports 10 weeks of intermittent knee soreness.")
    assert evidence.evidence.physical_therapy_weeks == 0


def test_keeps_the_longest_documented_course():
    evidence = extract_from_text(
        "Completed 4 weeks of physical therapy in spring.\n"
        "Subsequently completed 9 weeks of physical therapy."
    )
    assert evidence.evidence.physical_therapy_weeks == 9


# --------------------------------------------------------------------------
# Physical exam recency
# --------------------------------------------------------------------------


def test_an_exam_inside_the_window_counts_as_recent():
    evidence = extract_from_text(
        EXAM_NOTE, document_date="2026-09-01", as_of_date="2026-09-15"
    )
    assert evidence.evidence.recent_physical_exam is True


def test_an_exam_outside_the_window_does_not():
    evidence = extract_from_text(
        EXAM_NOTE, document_date="2026-01-05", as_of_date="2026-09-15"
    )
    assert evidence.evidence.recent_physical_exam is False


def test_the_window_is_configurable():
    evidence = extract_from_text(
        EXAM_NOTE,
        document_date="2026-01-05",
        as_of_date="2026-09-15",
        recency_window_days=365,
    )
    assert evidence.evidence.recent_physical_exam is True


def test_an_undated_exam_cannot_be_called_recent():
    evidence = extract_from_text(EXAM_NOTE, as_of_date="2026-09-15")
    assert evidence.evidence.recent_physical_exam is False


def test_a_stale_exam_is_cited_so_a_newer_one_can_be_requested():
    evidence = extract_from_text(
        EXAM_NOTE, document_date="2026-01-05", as_of_date="2026-09-15"
    )
    assert "recency window" in evidence.sources[-1].fact


def test_a_therapy_note_is_not_mistaken_for_a_physical_exam():
    evidence = extract_from_text(
        "PHYSICAL THERAPY PROGRESS NOTE\nCompleted 8 weeks of physical therapy.",
        document_date="2026-09-10",
        as_of_date="2026-09-15",
    )
    assert evidence.evidence.recent_physical_exam is False


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


def test_page_markers_become_the_citation_location():
    evidence = extract_from_text(
        "PT PROGRESS NOTE\nIntake summary.\n--- Page 2 ---\n"
        "Completed 8 weeks of physical therapy."
    )
    pt = next(s for s in evidence.sources if "physical therapy" in s.fact)
    assert pt.location == "page 2"


def test_an_explicit_location_overrides_the_derived_page():
    evidence = extract_from_text(
        "Completed 8 weeks of physical therapy.", location="section 4, paragraph 2"
    )
    pt = next(s for s in evidence.sources if "physical therapy" in s.fact)
    assert pt.location == "section 4, paragraph 2"


# --------------------------------------------------------------------------
# Absent evidence
# --------------------------------------------------------------------------


def test_an_unrelated_record_yields_negatives_not_guesses():
    evidence = extract_from_text(
        "Annual wellness visit. Blood pressure 118/76. No complaints."
    )
    ClinicalEvidence.model_validate(evidence.model_dump())
    assert evidence.evidence.model_dump() == {
        "mri_confirmed": False,
        "physical_therapy_weeks": 0,
        "persistent_instability": False,
        "nsaid_trial": False,
        "recent_physical_exam": False,
    }
    assert evidence.diagnosis is None
    assert evidence.sources == []


def test_an_empty_document_is_handled_without_throwing():
    evidence = extract_from_text("")
    ClinicalEvidence.model_validate(evidence.model_dump())
