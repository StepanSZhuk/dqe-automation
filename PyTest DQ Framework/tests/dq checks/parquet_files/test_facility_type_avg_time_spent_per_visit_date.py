"""
Description: Data Quality checks for "facility_type_avg_time_spent_per_visit_date" parquet file
Requirement(s): TICKET-1235
Author(s): Stepan Zhuk
"""


import pandas as pd
import pytest
from data_dev.config import parquet_storage_config
import logging
logger = logging.getLogger(__name__)


@pytest.fixture(scope='module')
def source_data(db_connection):
    """Raw data from Postgres: facilities and visits with duration_minutes"""
    source_query = """
SELECT
  f.facility_type,
  DATE(v.visit_timestamp) AS visit_date,
  ROUND(AVG(v.duration_minutes)::numeric, 2) AS avg_time_spent
FROM mydatabase.public.visits v
JOIN mydatabase.public.facilities f
  ON v.facility_id = f.id
WHERE
  v.visit_timestamp IS NOT NULL
  AND f.facility_type IS NOT NULL
  AND v.duration_minutes IS NOT NULL
GROUP BY
  f.facility_type,
  visit_date
ORDER BY
  f.facility_type,
  visit_date;
    """
    source_data = db_connection.get_data_sql(source_query)
    logger.info("Source data shape: %s", source_data.shape)
    logger.info("Preview:\n%s", source_data.head())
    return source_data

@pytest.fixture(scope='module')
def target_data(parquet_reader):
    target_path = '/parquet_data/facility_type_avg_time_spent_per_visit_date'
    target_data = parquet_reader.process(target_path, include_subfolders=True)
    return target_data

@pytest.mark.parquet_data
@pytest.mark.smoke
@pytest.mark.facility_type_avg_time_spent_per_visit_date
def test_check_dataset_is_not_empty(target_data, data_quality_library):
    data_quality_library.check_dataset_is_not_empty(target_data)


@pytest.mark.parquet_data
@pytest.mark.facility_type_avg_time_spent_per_visit_date
def test_check_not_null_values(target_data, data_quality_library):
    print(target_data)
    data_quality_library.check_not_null_values(
        target_data,
        ["facility_type", "visit_date", "avg_time_spent"],
    )


@pytest.mark.parquet_data
@pytest.mark.facility_type_avg_time_spent_per_visit_date
def test_check_no_duplicates(target_data, data_quality_library):
    """Check that there are no duplicate rows in the dataset."""
    data_quality_library.check_duplicates(
        target_data,
        column_names=["facility_type", "visit_date", "avg_time_spent"],
        dataset_name="facility_type_avg_time_spent_per_visit_date"
    )

@pytest.mark.parquet_data
@pytest.mark.facility_type_avg_time_spent_per_visit_date
def test_check_count(source_data, target_data, data_quality_library):
    """Compare record counts: target (aggregated) should be == source (raw)"""
    data_quality_library.check_count(
        source_data, 
        target_data,
        source_name="source (visits_facilities)",
        target_name="target (aggregated parquet)"
    )

@pytest.mark.parquet_data
@pytest.mark.facility_type_avg_time_spent_per_visit_date
def test_check_data_completeness(source_data, target_data, data_quality_library):
    """
    Validate that target aggregation matches source data.
    
    Target transformation:
    - GROUP BY facility_type, visit_date (from visit_timestamp)
    - AVG(duration_minutes) AS avg_time_spent
    """
    data_quality_library.check_data_completeness(
        source_df=source_data,
        target_df=target_data,
        source_groupby_cols=['facility_type', 'visit_date'],
        source_agg_col='duration_minutes',
        target_groupby_cols=['facility_type', 'visit_date'],
        target_agg_col='avg_time_spent',
        agg_function='avg',
        source_name="source (Postgres visits_facilities)",
        target_name="target (parquet aggregated)"
    )