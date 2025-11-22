"""
Description: Data Quality checks for "patients" postgres table.
Requirement(s): TICKET-1246
Author(s): Stepan Zhuk
"""

import pytest
import logging
logger = logging.getLogger(__name__)

@pytest.fixture(scope='module')
def source_data(db_connection):
    source_query = """
    SELECT * from mydatabase.public.patients
    """
    source_data = db_connection.get_data_sql(source_query)
    logger.info("Preview:\n%s", source_data.head())
    print(type(source_data))
    return source_data

@pytest.mark.smoke
@pytest.mark.parquet_data
def test_check_postgres_patients_is_not_empty(source_data, data_quality_library):
    data_quality_library.check_dataset_is_not_empty(source_data)

@pytest.mark.smoke
@pytest.mark.parquet_data
def test_check_not_null_values(source_data, data_quality_library):
    print(source_data)
    data_quality_library.check_not_null_values(
        source_data,
        ["id", "external_id", "first_name", "last_name", "address", "date_of_birth"]
    )


@pytest.mark.parquet_data
def test_check_no_duplicates(source_data, data_quality_library):
    """Check that there are no duplicate rows in the dataset."""
    data_quality_library.check_duplicates(
        source_data,
        column_names=["id", "external_id", "first_name", "last_name", "address", "date_of_birth"],
        dataset_name="mydatabase.public.patients"
    )