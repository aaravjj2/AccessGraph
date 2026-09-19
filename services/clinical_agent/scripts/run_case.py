"""Offline runner: ``python scripts/run_case.py examples/acl_case_input.json [--trace]``

Useful for teammates who want extractor output without starting a server.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.contracts import ExtractRequest  # noqa: E402
from app.extract import extract_clinical_evidence  # noqa: E402


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python scripts/run_case.py <input.json> [--trace]", file=sys.stderr)
        return 2

    request = ExtractRequest.model_validate(json.loads(Path(argv[0]).read_text(encoding="utf-8")))
    result = extract_clinical_evidence(request)

    if "--trace" in argv[1:]:
        payload = {
            "as_of_date": result.as_of_date,
            "trace": [asdict(entry) for entry in result.trace],
        }
    else:
        payload = result.evidence.model_dump()

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
