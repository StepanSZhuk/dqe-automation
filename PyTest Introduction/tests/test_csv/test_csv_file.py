import pytest
import re

email_re = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

def test_file_not_empty(read_csv):
    rows = read_csv
    assert rows, "CSV file is empty."


@pytest.mark.validate_csv
def test_validate_schema(schema_validator, read_csv):
    """
    Validate the CSV schema.
    """
    rows = read_csv
    actual_schema = list(rows[0].keys()) if rows else []
    expected_schema = ["id", "name", "age", "email", "is_active"]
    schema_validator(actual_schema, expected_schema)



@pytest.mark.validate_csv
@pytest.mark.skip(reason="Age validation intentionally skipped in this run (marked skip).")
def test_age_column_valid(read_csv):
    """Validate that age values are integers between 0 and 100 (inclusive)."""
    rows = read_csv
    assert rows, "Cannot validate age column on empty CSV."

    for i, r in enumerate(rows, start=1):
        raw = r.get("age", "").strip()
        try:
            age = int(raw)
        except Exception:
            pytest.fail(f"Row {i}: invalid integer in 'age' column: '{raw}'")
        assert 0 <= age <= 100, f"Row {i}: age {age} out of allowed range 0-100."


@pytest.mark.validate_csv
def test_email_column_valid(read_csv):
    """Validate that email column contains valid email addresses."""
    rows = read_csv
    assert rows, "Cannot validate emails on empty CSV."
    for i, r in enumerate(rows, start=1):
        email = (r.get("email") or "").strip()
        assert email_re.match(email), f"Row {i}: invalid email format: '{email}'"



@pytest.mark.validate_csv
@pytest.mark.xfail(reason="Sample data contains duplicates; this test is expected to fail (xfail).")
def test_duplicates(read_csv):
    """
    Validate there are no duplicate rows.
    This test is marked xfail because the sample CSV intentionally contains duplicates.
    """
    rows = read_csv
    headers = list(rows[0].keys()) if rows else []
    seen = set()
    for i, r in enumerate(rows, start=1):
        # Create tuple of values in header order for reliable comparison
        key = tuple(r.get(h, "").strip() for h in headers)
        if key in seen:
           pytest.fail(f"Duplicate row detected at data row {i}: {key}") 
        seen.add(key)


@pytest.mark.parametrize("id, is_active", [(1, False), (2, True)])
def test_is_active_parametrized(read_csv, id, is_active):
    """Validate that:
            is_active = False for id = 1.
            is_active = True for id = 2.
    """
    rows = read_csv
    assert rows, "CSV is empty."
    matches = [r for r in rows if str(r.get("id", "")).strip() == str(id)]
    assert matches, f"No row found with id={id}."
    # If multiple rows with same id, assert first one
    actual_val = matches[0].get("is_active", "").strip().lower()
    assert actual_val == str(is_active).lower(), f"For id={id}: expected is_active={is_active}, got '{actual_val}'."


def test_is_active_single_for_id2(read_csv):
    """Same check as above for id=2 but without parametrization."""
    target_id = 2
    rows = read_csv
    matches = [r for r in rows if str(r.get("id", "")).strip() == str(target_id)]
    assert matches, f"No row found with id={target_id}."
    actual_bool = matches[0].get("is_active", "").strip().lower()
    expected = True
    assert actual_bool == str(expected).lower(), f"For id={target_id}: expected is_active={expected}, got '{actual_bool}'."