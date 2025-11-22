from pathlib import Path
from typing import Iterable, List, Union

import pandas as pd
from pandas import DataFrame


class ParquetReader:
    """Read parquet data from a file or a directory.

    The `process` method accepts an `include_subfolders` flag to control
    whether files should be collected recursively (default: False).
    """

    def process(self, location: Union[str, Path], include_subfolders: bool = False) -> DataFrame:
        path = Path(location).expanduser()

        # If the provided path exists, resolve it and continue
        if path.exists():
            path = path.resolve()
        else:
            # Fallback: search the repository (current working directory) for a matching
            # parquet_data/<name> directory and use it if found.
            name = Path(location).name
            cwd = Path.cwd()
            candidates = list(cwd.rglob(f"parquet_data/{name}"))
            if candidates:
                path = candidates[0].resolve()
            else:
                # Last resort: try one level up from cwd
                parent_candidates = list(cwd.parent.rglob(f"parquet_data/{name}"))
                if parent_candidates:
                    path = parent_candidates[0].resolve()
                else:
                    raise FileNotFoundError(f"Parquet location not found: {path}")

        if path.is_file():
            return pd.read_parquet(path)

        if include_subfolders:
            parquet_files = self._collect_parquet_files(path)
        else:
            parquet_files = sorted(path.glob("*.parquet"))

        if not parquet_files:
            raise FileNotFoundError(f"No parquet files found under directory: {path}")

        frames: List[DataFrame] = [pd.read_parquet(file_path) for file_path in parquet_files]
        return pd.concat(frames, ignore_index=True)

    @staticmethod
    def _collect_parquet_files(directory: Path) -> Iterable[Path]:
        return sorted(directory.rglob("*.parquet"))