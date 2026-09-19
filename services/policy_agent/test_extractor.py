import json
from pathlib import Path
import unittest

from extractor import extract_policy_requirements


class ExtractorTests(unittest.TestCase):
    def test_acl_demo_matches_committed_contract_output(self):
        examples = Path(__file__).parent / "examples"
        payload = json.loads((examples / "acl_policy_input.json").read_text())
        expected = json.loads((examples / "acl_policy_output.json").read_text())
        self.assertEqual(extract_policy_requirements(payload), expected)

    def test_missing_version_is_null(self):
        result = extract_policy_requirements({"insurer": "P", "procedure": "OTHER", "documents": [{"source_id": "x", "source_label": "X", "text": "Policy"}]})
        self.assertIsNone(result["policy_version"])
        self.assertEqual(result["requirements"], [])


if __name__ == "__main__":
    unittest.main()
