#!/usr/bin/env python
import argparse
import json
from pathlib import Path
import sys
from typing import Any

from app.pipeline.field_extraction import DeterministicFieldExtractorV1


DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "regression"


def _load_fixture(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def _observed_fields(text: str) -> dict[str, str]:
    matches = DeterministicFieldExtractorV1().extract(text)
    return {match.field_key: match.value for match in matches}


def run_fixture(path: Path) -> dict[str, Any]:
    fixture = _load_fixture(path)
    expected = fixture["expected_fields"]
    observed = _observed_fields(fixture["input_text"])
    mismatches = []
    for field_key, expected_value in expected.items():
        observed_value = observed.get(field_key)
        if observed_value != expected_value:
            mismatches.append(
                {
                    "field_key": field_key,
                    "expected": expected_value,
                    "observed": observed_value,
                }
            )
    return {
        "fixture": path.name,
        "status": "passed" if not mismatches else "failed",
        "expected_count": len(expected),
        "observed_count": len(observed),
        "mismatches": mismatches,
    }


def run_directory(fixtures_dir: Path) -> dict[str, Any]:
    fixture_paths = sorted(fixtures_dir.glob("*.json"))
    results = [run_fixture(path) for path in fixture_paths]
    failed = [result for result in results if result["status"] != "passed"]
    return {
        "status": "passed" if not failed else "failed",
        "fixture_count": len(results),
        "failed_count": len(failed),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run quick synthetic document regression fixtures.")
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=DEFAULT_FIXTURES_DIR,
        help="Directory containing synthetic regression fixtures.",
    )
    args = parser.parse_args()
    report = run_directory(args.fixtures_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
