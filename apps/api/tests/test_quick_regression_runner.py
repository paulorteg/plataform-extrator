from pathlib import Path

from scripts.run_quick_regression import run_directory


def test_quick_regression_fixture_passes_with_synthetic_data():
    fixtures_dir = Path(__file__).parent / "fixtures" / "regression"

    report = run_directory(fixtures_dir)

    assert report["status"] == "passed"
    assert report["fixture_count"] >= 1
    assert report["failed_count"] == 0


def test_regression_fixture_is_marked_synthetic():
    fixture_path = Path(__file__).parent / "fixtures" / "regression" / "sp_synthetic_minimal.json"

    assert "synthetic" in fixture_path.read_text(encoding="utf-8").lower()
