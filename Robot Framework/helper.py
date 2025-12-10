"""
Python helper functions for Robot Framework test automation.
Provides utilities for reading HTML tables, Parquet datasets, and comparing DataFrames.
"""
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from typing import Tuple, Optional
from io import StringIO


def read_html_table_to_dataframe(table_element_or_html):
    """
    Read an HTML table into a Pandas DataFrame.
    
    Args:
        table_element_or_html: Selenium WebElement or HTML string containing a table
        
    Returns:
        pandas.DataFrame: The extracted table data
    """
    try:
        # Check if it's a Selenium WebElement
        if hasattr(table_element_or_html, 'get_attribute'):
            # If it's a Selenium WebElement, extract only the collapsible rows
            from selenium.webdriver.common.by import By
            
            # Get all collapsible rows (main test result rows)
            collapsible_rows = table_element_or_html.find_elements(By.CSS_SELECTOR, 'tr.collapsible')
            
            # Extract data from each row
            data = []
            for row in collapsible_rows:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if cells and len(cells) >= 4:
                    row_data = [cell.text.strip() for cell in cells[:4]]
                    data.append(row_data)
            
            # Get header names
            headers = table_element_or_html.find_elements(By.CSS_SELECTOR, 'thead th')
            column_names = [h.text.strip() for h in headers] if headers else ['Result', 'Test', 'Duration', 'Links']
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=column_names[:len(data[0])] if data else column_names)
        else:
            # If it's HTML string, use pandas read_html
            html_string = str(table_element_or_html)
            df_list = pd.read_html(StringIO(html_string))
            
            if not df_list:
                raise ValueError("No table found in the provided HTML")
            
            df = df_list[0]
        
        # Clean column names: strip whitespace, lowercase, replace spaces with underscores
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Clean data: strip whitespace from string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        print(f"  Loaded HTML table: {len(df)} rows, {len(df.columns)} columns")
        print(f"  Columns: {list(df.columns)}")
        
        return df
        
    except Exception as e:
        raise RuntimeError(f"Failed to read HTML table: {str(e)}")


def read_parquet_with_filter(parquet_folder_path, filter_date=None):
    """
    Read a partitioned Parquet dataset with optional date filtering.
    
    Args:
        parquet_folder_path: Path to the Parquet dataset folder
        filter_date: Optional date string (YYYY-MM-DD) to filter by visit_date partition.
                    If None or empty, reads all data.
        
    Returns:
        pandas.DataFrame: The loaded Parquet data
    """
    try:
        parquet_path = Path(parquet_folder_path)
        
        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet folder not found: {parquet_path}")
        
        # Read the Parquet dataset
        if parquet_path.is_dir():
            # Read partitioned dataset
            dataset = pq.ParquetDataset(str(parquet_path))
            
            # Apply filter if provided
            if filter_date and filter_date.strip():
                filter_expr = ('visit_date', '=', filter_date.strip())
                table = dataset.read(filters=[filter_expr])
                print(f" Applied filter: visit_date = {filter_date}")
            else:
                table = dataset.read()
                print(f" No filter applied, reading all data")
            
            df = table.to_pandas()
        else:
            # Single Parquet file
            table = pq.read_table(str(parquet_path))
            df = table.to_pandas()
            
            # Apply filter if provided and column exists
            if filter_date and filter_date.strip() and 'visit_date' in df.columns:
                df = df[df['visit_date'] == filter_date.strip()]
                print(f"✓ Applied filter: visit_date = {filter_date}")
        
        # Clean column names: strip whitespace, lowercase, replace spaces with underscores
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Clean data: strip whitespace from string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        print(f" Loaded Parquet data: {len(df)} rows, {len(df.columns)} columns")
        print(f"  Columns: {list(df.columns)}")
        
        return df
        
    except Exception as e:
        raise RuntimeError(f"Failed to read Parquet data: {str(e)}")


def compare_dataframes(df1, df2, df1_name="DataFrame 1", df2_name="DataFrame 2"):
    """
    Compare two DataFrames for exact match and return detailed differences.
    
    Args:
        df1: First DataFrame (e.g., HTML table data)
        df2: Second DataFrame (e.g., Parquet data)
        df1_name: Name for the first DataFrame (for reporting)
        df2_name: Name for the second DataFrame (for reporting)
        
    Returns:
        tuple: (match: bool, report: str)
            - match: True if DataFrames are identical, False otherwise
            - report: Detailed comparison report string
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("DATAFRAME COMPARISON REPORT")
    report_lines.append("=" * 80)
    
    # Check shapes
    report_lines.append(f"\n Shape Comparison:")
    report_lines.append(f"  {df1_name}: {df1.shape[0]} rows × {df1.shape[1]} columns")
    report_lines.append(f"  {df2_name}: {df2.shape[0]} rows × {df2.shape[1]} columns")
    
    match = True
    
    # Compare row counts
    if df1.shape[0] != df2.shape[0]:
        match = False
        report_lines.append(f"\n Row count mismatch!")
        report_lines.append(f"  {df1_name} has {df1.shape[0]} rows")
        report_lines.append(f"  {df2_name} has {df2.shape[0]} rows")
        report_lines.append(f"  Difference: {abs(df1.shape[0] - df2.shape[0])} rows")
    
    # Compare column counts
    if df1.shape[1] != df2.shape[1]:
        match = False
        report_lines.append(f"\n Column count mismatch!")
        report_lines.append(f"  {df1_name} has {df1.shape[1]} columns")
        report_lines.append(f"  {df2_name} has {df2.shape[1]} columns")
    
    # Compare column names
    df1_cols = set(df1.columns)
    df2_cols = set(df2.columns)
    
    if df1_cols != df2_cols:
        match = False
        report_lines.append(f"\n Column name mismatch!")
        
        missing_in_df2 = df1_cols - df2_cols
        if missing_in_df2:
            report_lines.append(f"  Columns in {df1_name} but not in {df2_name}: {sorted(missing_in_df2)}")
        
        missing_in_df1 = df2_cols - df1_cols
        if missing_in_df1:
            report_lines.append(f"  Columns in {df2_name} but not in {df1_name}: {sorted(missing_in_df1)}")
    else:
        report_lines.append(f"\n✓ Column names match: {sorted(df1_cols)}")
    
    # If shapes and columns match, compare data values
    if df1.shape == df2.shape and df1_cols == df2_cols:
        # Sort both DataFrames by all columns to ensure same order
        common_cols = sorted(df1_cols)
        df1_sorted = df1[common_cols].sort_values(by=common_cols).reset_index(drop=True)
        df2_sorted = df2[common_cols].sort_values(by=common_cols).reset_index(drop=True)
        
        # Compare values
        try:
            pd.testing.assert_frame_equal(df1_sorted, df2_sorted, check_dtype=False)
            report_lines.append(f"\n✅ Data values match exactly!")
        except AssertionError as e:
            match = False
            report_lines.append(f"\n Data value mismatch!")
            
            # Find differing rows
            comparison = df1_sorted != df2_sorted
            differing_rows = comparison.any(axis=1)
            num_diff_rows = differing_rows.sum()
            
            if num_diff_rows > 0:
                report_lines.append(f"  Number of differing rows: {num_diff_rows}")
                report_lines.append(f"\n  Sample differences (first 5 rows):")
                
                diff_indices = differing_rows[differing_rows].index[:5]
                for idx in diff_indices:
                    report_lines.append(f"\n  Row {idx}:")
                    for col in common_cols:
                        val1 = df1_sorted.loc[idx, col]
                        val2 = df2_sorted.loc[idx, col]
                        if val1 != val2:
                            report_lines.append(f"    {col}: '{val1}' != '{val2}'")
    
    # Summary
    report_lines.append("\n" + "=" * 80)
    if match:
        report_lines.append(" RESULT: DataFrames match exactly!")
    else:
        report_lines.append(" RESULT: DataFrames DO NOT match!")
    report_lines.append("=" * 80)
    
    report = "\n".join(report_lines)
    return match, report