"""
Description: Data Quality checks for "patients" postgres table.
Requirement(s): TICKET-1247
Author(s): Stepan Zhuk
"""

import pytest
import logging
logger = logging.getLogger(__name__)

@pytest.fixture(scope='module')
def source_data(db_connection):
    source_query = """
    SELECT * from mydatabase.public.facilities
    """
    source_data = db_connection.get_data_sql(source_query)
    logger.info("Preview:\n%s", source_data.head())
    return source_data

@pytest.mark.smoke
@pytest.mark.parquet_data
def test_check_postgres_facilities_is_not_empty(source_data, data_quality_library):
    data_quality_library.check_dataset_is_not_empty(source_data)

@pytest.mark.smoke
@pytest.mark.parquet_data
def test_check_not_null_values(source_data, data_quality_library):
    data_quality_library.check_not_null_values(
        source_data,
        ["id", "external_id", "facility_name", "facility_name", "address", "city", "state"]
    )


@pytest.mark.parquet_data
def test_check_no_duplicates(source_data, data_quality_library):
    """Check that there are no duplicate rows in the dataset."""
    data_quality_library.check_duplicates(
        source_data,
        column_names=["id", "external_id", "facility_name", "facility_type", "address", "city", "state"],
        dataset_name="mydatabase.public.facilities"
    )