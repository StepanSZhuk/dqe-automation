import sys
import os
from pathlib import Path

# Ensure repo root is on sys.path
_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import pytest
from src.connectors.postgres.postgres_connector import PostgresConnectorContextManager
from src.data_quality.data_quality_validation_library import DataQualityLibrary
from src.connectors.file_system.parquet_reader import ParquetReader

def _detect_environment():
    """Detect if running in container (Jenkins) or local environment."""
    return (
        os.path.exists('/.dockerenv') or 
        os.environ.get('JENKINS_HOME') or 
        os.environ.get('DB_HOST') == 'postgres'
    )

def pytest_addoption(parser):
    # Detect environment and set defaults
    in_container = _detect_environment()
    default_host = 'postgres' if in_container else 'localhost'
    default_port = '5432' if in_container else '5434'
    
    parser.addoption("--db_host", action="store", default=default_host, help="Database host")
    parser.addoption("--db_port", action="store", default=default_port, help="Database port")
    parser.addoption("--db_name", action="store", default="mydatabase", help="Database name")
    parser.addoption("--db_user", action="store", default=None, help="Database user (required)")
    parser.addoption("--db_password", action="store", default=None, help="Database password (required)")
    parser.addoption(
        "--parquet_root",
        action="store",
        default=None,
        help="Override parquet root directory for tests that read parquet data",
    )

def pytest_configure(config):
    """Validates that all required command-line options are provided."""
    required_options = ["--db_user", "--db_password"]
    for option in required_options:
        if not config.getoption(option):
            pytest.fail(f"Missing required option: {option}")

@pytest.fixture(scope='session')
def db_connection(request):
    db_host = request.config.getoption("--db_host")
    db_name = request.config.getoption("--db_name")
    db_port = request.config.getoption("--db_port")
    db_user = request.config.getoption("--db_user")
    db_password = request.config.getoption("--db_password")

    try:
        with PostgresConnectorContextManager(
            db_host=db_host,
            db_port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password
        ) as db_connector:
            yield db_connector
    except Exception as e:
        pytest.fail(f"Failed to initialize PostgresConnectorContextManager: {e}")

@pytest.fixture(scope='session')
def parquet_reader(request):
    try:
        reader = ParquetReader()
        yield reader
    except Exception as e:
        pytest.fail(f"Failed to initialize ParquetReader: {e}")
    finally:
        del reader

@pytest.fixture(scope='session')
def data_quality_library():
    try:
        data_quality_library = DataQualityLibrary()
        yield data_quality_library
    except Exception as e:
        pytest.fail(f"Failed to initialize DataQualityLibrary: {e}")
    finally:
        del data_quality_library