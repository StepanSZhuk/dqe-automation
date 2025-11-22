from src.connectors.postgre_connector import PostgresConnectorContextManager
from src.data.inject_generated_data_to_src import GeneratedDataLoader
from src.data.nf3_loader import NF3Loader
from src.data.parquet_loader import LoadParquet
from src.reporting.report_generator import ReportGenerator

import logging
import warnings
import os

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    # Read DB credentials from environment variables (set by Jenkins or locally)
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'mydatabase')
    db_user = os.environ.get('DB_USER') or os.environ.get('POSTGRES_SECRET_USR')
    db_password = os.environ.get('DB_PASSWORD') or os.environ.get('POSTGRES_SECRET_PSW')
    
    if not all([db_user, db_password]):
        raise ValueError(
            "Database credentials not found. Set DB_USER/DB_PASSWORD or "
            "POSTGRES_SECRET_USR/POSTGRES_SECRET_PSW environment variables."
        )
    
    with PostgresConnectorContextManager(
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password
    ) as connection_object:
        # generate and load generated data into src layer
        try:
            logging.info(f"Starting data generation and injection into Postgres...")
            gdi = GeneratedDataLoader(connection_object.get_connection())
            gdi.inject_data()
            logging.info(f"Data generation and injection into Postgres Completed!")
        except Exception as e:
            logging.exception(f"Data generation and injection into Postgres FAILED: {e}")
        # load to nf3 layer
        try:
            logging.info(f"Starting transformation of injected data...")
            l3nf = NF3Loader(connection_object.get_connection())
            l3nf.load_data()
            logging.info(f"Transformation of injected data completed!")
        except Exception as e:
            logging.exception(f"Transformation of injected data FAILED: {e}")
        # load parquet files
        try:
            logging.info(f"Starting transformation of parquet files...")
            ld = LoadParquet(connection_object)
            ld.load_parquet()
            logging.info(f"Transformation of parquet files completed!")
        except Exception as e:
            logging.exception(f"Transformation of parquet files FAILED: {e}")
        try:
            logging.info(f"Starting report generation...")
            rp = ReportGenerator()
            rp.generate_report()
            logging.info(f"Report generation completed!")
        except Exception as e:
            logging.exception(f"Report generation FAILED: {e}")


if __name__ == '__main__':
    main()
