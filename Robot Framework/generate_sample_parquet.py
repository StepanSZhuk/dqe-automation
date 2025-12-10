"""
Generate sample Parquet data for Robot Framework testing.
Creates a Parquet file with sample test result data.
"""
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

# Sample data matching HTML report structure
data = {
    'result': ['Passed'] * 16 + ['Failed'] * 8,
    'test': [
        'dq checks/parquet_files/test_facility_name_min_time_spent_per_visit_date.py::test_check_not_null_values',
        'dq checks/parquet_files/test_facility_name_min_time_spent_per_visit_date.py::test_check_dataset_is_not_empty',
        'dq checks/parquet_files/test_facility_type_avg_time_spent_per_visit_date.py::test_check_dataset_is_not_empty',
        'dq checks/parquet_files/test_facility_type_avg_time_spent_per_visit_date.py::test_check_not_null_values',
        'dq checks/parquet_files/test_facility_type_avg_time_spent_per_visit_date.py::test_check_no_duplicates',
        'dq checks/parquet_files/test_patient_sum_treatment_cost_per_facility_type.py::test_check_dataset_is_not_empty',
        'dq checks/parquet_files/test_patient_sum_treatment_cost_per_facility_type.py::test_check_no_duplicates',
        'test_postgres_facilities.py::test_check_postgres_facilities_is_not_empty',
        'test_postgres_facilities.py::test_check_not_null_values',
        'test_postgres_facilities.py::test_check_no_duplicates',
        'test_postgres_patiens.py::test_check_postgres_patients_is_not_empty',
        'test_postgres_patiens.py::test_check_not_null_values',
        'test_postgres_patiens.py::test_check_no_duplicates',
        'test_postgres_visits.py::test_check_postgres_visits_is_not_empty',
        'test_postgres_visits.py::test_check_not_null_values',
        'test_postgres_visits.py::test_check_no_duplicates',
        'dq checks/parquet_files/test_facility_name_min_time_spent_per_visit_date.py::test_check_count',
        'dq checks/parquet_files/test_facility_name_min_time_spent_per_visit_date.py::test_check_data_completeness',
        'dq checks/parquet_files/test_facility_name_min_time_spent_per_visit_date.py::test_check_no_duplicates',
        'dq checks/parquet_files/test_facility_type_avg_time_spent_per_visit_date.py::test_check_count',
        'dq checks/parquet_files/test_facility_type_avg_time_spent_per_visit_date.py::test_check_data_completeness',
        'dq checks/parquet_files/test_patient_sum_treatment_cost_per_facility_type.py::test_check_not_null_values',
        'dq checks/parquet_files/test_patient_sum_treatment_cost_per_facility_type.py::test_check_count',
        'dq checks/parquet_files/test_patient_sum_treatment_cost_per_facility_type.py::test_check_data_completeness',
    ],
    'duration': [
        '00:00:03', '10 ms', '00:00:02', '14 ms', '8 ms', '1 ms', '2 ms',
        '4 ms', '4 ms', '2 ms', '3 ms', '2 ms', '1 ms', '525 ms', '7 ms', '25 ms',
        '669 ms', '345 ms', '28 ms', '483 ms', '132 ms', '40 ms', '245 ms', '15 ms'
    ],
    'links': [''] * 24
}

# Create DataFrame
df = pd.DataFrame(data)

# Clean column names to match helper.py expectations
df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

print(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
print(f"Columns: {list(df.columns)}")
print(f"\nFirst few rows:")
print(df.head())
print(f"\nValue counts by result:")
print(df['result'].value_counts())

# Save to Parquet
output_dir = Path(__file__).parent / 'parquet_data'
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'data.parquet'

# Write to Parquet
table = pa.Table.from_pandas(df)
pq.write_table(table, str(output_file))

print(f"\n Parquet file saved to: {output_file}")
print(f"  File size: {output_file.stat().st_size} bytes")
