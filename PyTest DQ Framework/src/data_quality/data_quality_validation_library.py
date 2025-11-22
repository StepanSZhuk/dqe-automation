import pandas as pd
from pandas import DataFrame

class DataQualityLibrary:
    """
    A library of static methods for performing data quality checks on pandas DataFrames.

    This class is intended to be used in a PyTest-based testing framework to validate
    the quality of data in DataFrames. Each method performs a specific data quality
    check and uses assertions to ensure that the data meets the expected conditions.
    """

    @staticmethod
    def check_duplicates(df: DataFrame, column_names=None, dataset_name: str = "dataset") -> None:
        """
        Check for duplicate rows in a DataFrame.
        Args:
            df (DataFrame): The DataFrame to check for duplicates.
            column_names (list, optional): List of column names to check for duplicates.
                                          If None, checks all columns.
            dataset_name (str): Name of the dataset for error messages.

        Raises:
            AssertionError: If duplicate rows are found.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"{dataset_name} must be a pandas DataFrame.")
        
        # Determine which columns to check
        columns_to_check = column_names if column_names else df.columns.tolist()
        
        # Find duplicates
        duplicates = df[df.duplicated(subset=columns_to_check, keep=False)]
        
        if not duplicates.empty:
            # Get count of duplicates
            duplicate_count = df.duplicated(subset=columns_to_check).sum()
            
            # Show example of duplicates
            example_duplicates = duplicates.head(5)
            
            assert False, (
                f"{dataset_name} contains {duplicate_count} duplicate row(s) "
                f"based on columns {columns_to_check}.\n"
                f"Example duplicates:\n{example_duplicates}"
            )

    @staticmethod
    def check_count(source_df: DataFrame, target_df: DataFrame, 
                   source_name: str = "source", target_name: str = "target") -> None:
        """
        Compare record counts between source and target datasets.
        
        For aggregated data, target count should be <= source count.
        Use tolerance to allow acceptable variance.
        
        Args:
            source_df (DataFrame): Source dataset
            target_df (DataFrame): Target dataset (typically aggregated)
            source_name (str): Name of source dataset for messages
            target_name (str): Name of target dataset for messages
            tolerance (int): Acceptable difference in record counts (default: 0)
            
        Raises:
            AssertionError: If counts don't meet expectations
        """
        if not isinstance(source_df, pd.DataFrame):
            raise TypeError(f"{source_name} must be a pandas DataFrame.")
        if not isinstance(target_df, pd.DataFrame):
            raise TypeError(f"{target_name} must be a pandas DataFrame.")
            
        source_count = len(source_df)
        target_count = len(target_df)
        
        # For aggregated target data, target should have fewer or equal records than source
        assert target_count > 0, f"{target_name} is empty (0 records)"
        assert source_count > 0, f"{source_name} is empty (0 records)"
        
        # Log the counts for visibility
        print(f"\nRecord Count Comparison:")
        print(f"  {source_name}: {source_count:,} records")
        print(f"  {target_name}: {target_count:,} records")
        print(f"  Difference: {source_count - target_count:,} records")
        print(f"  Ratio: {target_count/source_count:.2%} (target/source)")
        
        # For aggregated data, target should be smaller or equal
        assert target_count == source_count, (
            f"{target_name} has MORE records than {source_name}! "
            f"Target: {target_count:,}, Source: {source_count:,}"
        )
    
    @staticmethod
    def check_data_completeness(
        source_df: DataFrame,
        target_df: DataFrame,
        source_groupby_cols: list,
        source_agg_col: str,
        target_groupby_cols: list,
        target_agg_col: str,
        agg_function: str = "min",
        source_name: str = "source",
        target_name: str = "target",
        numeric_tolerance: float = 0.01,
    ) -> None:
        """
        Compare source and target DataFrames directly without performing grouping.
        Requires `source_df` to already be pre-aggregated at the same grain as `target_df`.
        """
        # Validate inputs
        if not isinstance(source_df, pd.DataFrame):
            raise TypeError(f"{source_name} must be a pandas DataFrame.")
        if not isinstance(target_df, pd.DataFrame):
            raise TypeError(f"{target_name} must be a pandas DataFrame.")

        # Columns to compare (use target names)
        group_cols = list(target_groupby_cols)
        val_col = target_agg_col

        # Ensure target has the comparison columns
        missing_t = [c for c in group_cols + [val_col] if c not in target_df.columns]
        assert not missing_t, f"{target_name} missing columns: {missing_t}"

        # Prepare source for comparison:
        # if source already has target val col, use it; otherwise try to rename source_agg_col -> val_col
        if all(c in source_df.columns for c in group_cols + [val_col]):
            s = source_df[group_cols + [val_col]].copy()
        elif all(c in source_df.columns for c in group_cols + [source_agg_col]):
            s = source_df[group_cols + [source_agg_col]].copy().rename(columns={source_agg_col: val_col})
        else:
            missing_s = [c for c in group_cols + [source_agg_col] if c not in source_df.columns]
            raise AssertionError(
                f"{source_name} missing required pre-aggregated columns: {missing_s}. "
                "This check requires source to already be aggregated to the same grain as target."
            )

        t = target_df[group_cols + [val_col]].copy()

        # Ensure source is pre-aggregated (no duplicate group keys)
        dup_mask = s.duplicated(subset=group_cols, keep=False)
        if dup_mask.any():
            raise AssertionError(
                f"{source_name} appears to have multiple rows per group (must be pre-aggregated). "
                f"Example duplicates:\n{s[dup_mask].head(5)}"
            )

        # Normalize date/timestamp columns and numeric column
        def _normalize_dates(df, cols):
            for c in cols:
                if 'date' in c.lower() or 'timestamp' in c.lower():
                    if c in df.columns:
                        df[c] = pd.to_datetime(df[c], errors='coerce').dt.normalize()

        _normalize_dates(s, group_cols)
        _normalize_dates(t, group_cols)

        s[val_col] = pd.to_numeric(s[val_col], errors='coerce')
        t[val_col] = pd.to_numeric(t[val_col], errors='coerce')

        # Drop rows with any NA in key or value columns (they are invalid for comparison)
        s = s.dropna(subset=group_cols + [val_col])
        t = t.dropna(subset=group_cols + [val_col])

        # Sort deterministically
        s = s.sort_values(by=group_cols).reset_index(drop=True)
        t = t.sort_values(by=group_cols).reset_index(drop=True)

        # Quick shape check with helpful diagnostics
        if s.shape != t.shape:
            merged = s.merge(t, on=group_cols, how='outer', indicator=True)
            missing_in_target = merged[merged['_merge'] == 'left_only'][group_cols].head(5)
            extra_in_target = merged[merged['_merge'] == 'right_only'][group_cols].head(5)
            msg = (
                f"Shape mismatch: {source_name} {s.shape} vs {target_name} {t.shape}.\n"
            )
            if not missing_in_target.empty:
                msg += f"Groups in {source_name} but missing in {target_name} (examples):\n{missing_in_target.to_string(index=False)}\n"
            if not extra_in_target.empty:
                msg += f"Groups in {target_name} but missing in {source_name} (examples):\n{extra_in_target.to_string(index=False)}\n"
            raise AssertionError(msg)

        # Compare numeric values with tolerance
        diffs = (s[val_col] - t[val_col]).abs()
        both_nan = s[val_col].isna() & t[val_col].isna()
        if not both_nan.all():
            # exclude positions where both are NaN
            diffs = diffs[~both_nan]
        if (diffs > numeric_tolerance).any():
            bad_idx = diffs[diffs > numeric_tolerance].index[:10]
            sample = pd.DataFrame({
                **{c: s.loc[bad_idx, c].values for c in group_cols},
                f"{val_col}_expected": s.loc[bad_idx, val_col].values,
                f"{val_col}_actual": t.loc[bad_idx, val_col].values,
                "abs_diff": diffs.loc[bad_idx].values
            })
            raise AssertionError(
                f"Found {len(diffs[diffs > numeric_tolerance])} mismatches where '{val_col}' differs by more than {numeric_tolerance}.\n"
                f"Example rows:\n{sample.to_string(index=False)}"
            )

        # Success
        print(f"  ✓ Data completeness OK: {len(s):,} groups match between {source_name} and {target_name}")


    @staticmethod
    def check_dataset_is_not_empty(df: DataFrame, dataset_name: str = "dataset") -> None:
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"{dataset_name} must be a pandas DataFrame.")
        assert not df.empty, f"{dataset_name} is empty."


    @staticmethod
    def check_not_null_values(df: DataFrame, column_names=None, dataset_name: str = "dataset") -> None:
        columns = column_names or df.columns
        null_counts = df[columns].isnull().sum()
        failing = null_counts[null_counts > 0]
        assert failing.empty, f"{dataset_name} has NULL values: {failing.to_dict()}"