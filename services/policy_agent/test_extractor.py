import json
from pathlib import Path
import unittest

from extractor import PolicyExtractionError, extract_policy_requirements


class ExtractorTests(unittest.TestCase):
    def payload(self, text: str, **overrides):
        base = {
            "insurer": "ExampleHealth PPO",
            "procedure": "ACL_RECONSTRUCTION",
            "policy_version": "2026-09",
            "documents": [{"source_id": "policy", "source_label": "ACL Policy", "text": text}],
        }
        base.update(overrides)
        return base

    def test_acl_demo_matches_committed_contract_output(self):
        examples = Path(__file__).parent / "examples"
        payload = json.loads((examples / "acl_policy_input.json").read_text())
        expected = json.loads((examples / "acl_policy_output.json").read_text())
        self.assertEqual(extract_policy_requirements(payload), expected)

    def test_missing_version_is_null(self):
        result = extract_policy_requirements(self.payload("Policy", procedure="OTHER", policy_version=None))
        self.assertIsNone(result["policy_version"])
        self.assertEqual(result["requirements"], [])

    def test_extracts_all_supported_acl_requirements_in_contract_order(self):
        text = (
            "Section 3.1 MRI confirmation is required.\n"
            "Section 4.2 Complete at least 6 weeks of physical therapy.\n"
            "Section 4.3 Persistent functional instability required.\n"
            "Section 4.4 Recent qualifying physical examination required."
        )
        result = extract_policy_requirements(self.payload(text))
        self.assertEqual(
            [item["criterion_id"] for item in result["requirements"]],
            ["MRI_CONFIRMED", "PT_WEEKS", "PERSISTENT_INSTABILITY", "RECENT_PHYSICAL_EXAM"],
        )
        self.assertEqual(result["requirements"][1]["required_value"], 6)
        self.assertEqual(result["requirements"][1]["unit"], "weeks")

    def test_does_not_invent_requirements_from_irrelevant_text(self):
        result = extract_policy_requirements(self.payload("This policy discusses billing only."))
        self.assertEqual(result["requirements"], [])

    def test_uses_first_source_when_same_requirement_appears_twice(self):
        docs = [
            {"source_id": "first", "source_label": "First policy", "text": "Section 3.1 MRI confirmation required."},
            {"source_id": "second", "source_label": "Second policy", "text": "Section 3.1 MRI confirmation required."},
        ]
        result = extract_policy_requirements(self.payload("unused", documents=docs))
        self.assertEqual(result["requirements"][0]["source_label"], "First policy")

    def test_other_procedures_remain_schema_valid_but_empty(self):
        result = extract_policy_requirements(self.payload("MRI confirmation required.", procedure="HIP_REPLACEMENT"))
        self.assertEqual(result["procedure"], "HIP_REPLACEMENT")
        self.assertEqual(result["requirements"], [])

    def test_rejects_missing_top_level_fields(self):
        for payload in [{}, {"insurer": "P", "procedure": "ACL_RECONSTRUCTION"}, {"insurer": "", "procedure": "ACL_RECONSTRUCTION", "documents": []}]:
            with self.subTest(payload=payload):
                with self.assertRaises(PolicyExtractionError):
                    extract_policy_requirements(payload)

    def test_rejects_invalid_document_shape(self):
        invalid_documents = [[], [{}], [{"source_id": "x", "source_label": "X", "text": ""}], [{"source_id": "x", "source_label": 4, "text": "text"}]]
        for documents in invalid_documents:
            with self.subTest(documents=documents):
                with self.assertRaises(PolicyExtractionError):
                    extract_policy_requirements(self.payload("unused", documents=documents))

    def test_does_not_mutate_request_payload(self):
        payload = self.payload("Section 3.1 MRI confirmation required.")
        before = json.dumps(payload, sort_keys=True)
        extract_policy_requirements(payload)
        self.assertEqual(json.dumps(payload, sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
