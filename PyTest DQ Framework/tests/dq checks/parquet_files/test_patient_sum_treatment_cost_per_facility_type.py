"""
Description: Data Quality checks for "patient_sum_treatment_cost_per_facility_type" parquet file
Requirement(s): TICKET-1236
Author(s): Stepan Zhuk
"""


import pandas as pd
import pytest
from data_dev.config import parquet_storage_config
import logging
logger = logging.getLogger(__name__)

@pytest.fixture(scope='module')
def source_data(db_connection):
    """Raw data from Postgres"""
    source_query = """
SELECT
  f.facility_type,
  CONCAT_WS(' ', TRIM(p.first_name), TRIM(p.last_name)) AS full_name,
  ROUND(SUM(v.treatment_cost)::numeric, 2) AS sum_treatment_cost
FROM mydatabase.public.visits v
JOIN mydatabase.public.facilities f ON v.facility_id = f.id
JOIN mydatabase.public.patients p   ON v.patient_id = p.id
WHERE
  v.treatment_cost IS NOT NULL
  AND v.treatment_cost >= 0
  AND f.facility_type IS NOT NULL
  AND p.first_name IS NOT NULL
  AND p.last_name IS NOT NULL
GROUP BY
  f.facility_type,
  CONCAT_WS(' ', TRIM(p.first_name), TRIM(p.last_name))
ORDER BY
  f.facility_type,
  full_name;
    """
    source_data = db_connection.get_data_sql(source_query)
    logger.info("Source data shape: %s", source_data.shape)
    logger.info("Preview:\n%s", source_data.head())
    return source_data


@pytest.fixture(scope='module')
def target_data(parquet_reader):
    target_path = '/parquet_data/patient_sum_treatment_cost_per_facility_type'
    target_data = parquet_reader.process(target_path, include_subfolders=True)
    return target_data

@pytest.mark.smoke
@pytest.mark.parquet_data
@pytest.mark.patient_sum_treatment_cost_per_facility_type
@pytest.mark.validity_check
def test_check_not_null_values(target_data, data_quality_library):
    data_quality_library.check_not_null_values(
        target_data,
        ["facility_type", "full_name", "sum_treatment_cost"],
    )


@pytest.mark.smoke
@pytest.mark.parquet_data
@pytest.mark.patient_sum_treatment_cost_per_facility_type
@pytest.mark.consistency_check
def test_check_dataset_is_not_empty(target_data, data_quality_library):
    data_quality_library.check_dataset_is_not_empty(target_data)


@pytest.mark.smoke
@pytest.mark.parquet_data
@pytest.mark.patient_sum_treatment_cost_per_facility_type
@pytest.mark.uniqueness
def test_check_no_duplicates(target_data, data_quality_library):
    """Check that there are no duplicate rows in the dataset."""
    data_quality_library.check_duplicates(
        target_data,
        column_names=["facility_type", "full_name", "sum_treatment_cost"],
        dataset_name="patient_sum_treatment_cost_per_facility_type"
    )

@pytest.mark.parquet_data
@pytest.mark.patient_sum_treatment_cost_per_facility_type
@pytest.mark.completeness
def test_check_count(source_data, target_data, data_quality_library):
    """Compare record counts: target (aggregated) should be == source (raw)"""
    data_quality_library.check_count(
        source_data, 
        target_data,
        source_name="source (visits_facilities_patients)",
        target_name="target (aggregated parquet)"
    )

@pytest.mark.smoke
@pytest.mark.parquet_data
@pytest.mark.patient_sum_treatment_cost_per_facility_type
@pytest.mark.completeness
def test_check_data_completeness(source_data, target_data, data_quality_library):
    """
    Validate that target aggregation matches source data.
    
    Target transformation:
    - GROUP BY facility_type and full_name as first_name + last_name
    sum_treatment_cost	as SUM(v.treatment_cost)
    """
    data_quality_library.check_data_completeness(
        source_df=source_data,
        target_df=target_data,
        source_groupby_cols=['facility_type', 'full_name'],
        source_agg_col='sum_treatment_cost',
        target_groupby_cols=['facility_type', 'full_name'],
        target_agg_col='sum_treatment_cost',
        agg_function='sum',
        source_name="source (Postgres visits_facilities_patients)",
        target_name="target (parquet aggregated)"
    )