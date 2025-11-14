import pytest
import pandas as pd
import csv
from pathlib import Path

@pytest.fixture(scope="session")
def path_to_file():
    """
    Returns the absolute path to the CSV file under this repo: PyTest Introduction/src/data/data.csv
    """
    base = Path(__file__).resolve().parents[1]
    csv_path = base / "src" / "data" / "data.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found at {csv_path}")
    return str(csv_path)

# Fixture to read the CSV file
@pytest.fixture(scope="session")
def read_csv(path_to_file):
    """
    Reads CSV and returns a list of ordered dicts.
    """
    with open(path_to_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows

# Fixture to validate the schema of the file
@pytest.fixture(scope="session")
def schema_validator():
    """
    Returns a callable that validates actual_schema against expected_schema.
    Both parameters should be iterable of column names.
    """
    def _validate(actual_schema, expected_schema):
        # Compare the first N columns (expected_schema length) with actual schema
        actual_list = list(actual_schema)
        if len(actual_list) < len(expected_schema):
            raise AssertionError(f"Actual schema has fewer columns than expected. Expected at least {len(expected_schema)}, got {len(actual_list)}.")
        if len(actual_list) > len(expected_schema):
            raise AssertionError(f"Actual schema has more columns than expected. Expected at most {len(expected_schema)}, got {len(actual_list)}.")
        if actual_list[:len(expected_schema)] != list(expected_schema):
            raise AssertionError(f"Schema mismatch.\nExpected (first {len(expected_schema)}): {expected_schema}\nActual (first {len(expected_schema)}): {actual_list[:len(expected_schema)]}")
        return True
    return _validate

# Pytest hook to mark unmarked tests with a custom mark
def pytest_collection_modifyitems(session, config, items):
    """
    Mark tests that have NO explicit markers with 'unmarked'.
    """
    for item in items:
        # Skip tests that already have markers (explicit)
        explicit_markers = list(item.iter_markers())
        if not explicit_markers:
            item.add_marker(pytest.mark.unmarked)