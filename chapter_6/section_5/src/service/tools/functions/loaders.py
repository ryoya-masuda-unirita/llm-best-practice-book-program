"""Data loading functions for reading JSON files from the data directory."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"


def get_data_directory() -> Path:
    """Get the path to the data directory."""
    return DATA_DIR


def load_json_file(filename: str) -> dict | list:
    """Load a JSON file from the data directory."""
    file_path = DATA_DIR / filename
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def list_json_files() -> list[str]:
    """List all JSON files in the data directory."""
    return [f.name for f in DATA_DIR.glob("*.json")]


def load_students() -> list[dict]:
    """Load the students.json file."""
    return load_json_file("students.json")


def load_test_scores(quarter: int) -> list[dict]:
    """Load test scores for a specific quarter (1-4)."""
    filename = f"{quarter_to_ordinal(quarter)}_quarter_test_score.json"
    return load_json_file(filename)


def load_grade_report(quarter: int) -> list[dict]:
    """Load grade reports for a specific quarter (1-4)."""
    filename = f"{quarter_to_ordinal(quarter)}_quarter_grade_report.json"
    return load_json_file(filename)


def load_curriculum(quarter: int) -> dict:
    """Load curriculum data for a specific quarter (1-4)."""
    filename = f"{quarter_to_ordinal(quarter)}_quarter_curriculum.json"
    return load_json_file(filename)


def load_all_quarterly_scores() -> dict[int, list[dict]]:
    """Load test scores for all quarters (1-4)."""
    return {q: load_test_scores(q) for q in range(1, 5)}


def load_all_quarterly_grades() -> dict[int, list[dict]]:
    """Load grade reports for all quarters (1-4)."""
    return {q: load_grade_report(q) for q in range(1, 5)}


def load_all_quarterly_curriculum() -> dict[int, dict]:
    """Load curriculum data for all quarters (1-4)."""
    return {q: load_curriculum(q) for q in range(1, 5)}


def quarter_to_ordinal(quarter: int) -> str:
    """Convert quarter number (1-4) to ordinal string (1st, 2nd, etc.)."""
    ordinals = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
    return ordinals.get(quarter, f"{quarter}th")
