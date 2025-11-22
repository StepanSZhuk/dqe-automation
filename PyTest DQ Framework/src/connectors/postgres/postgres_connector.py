
from typing import Optional
import psycopg2
from psycopg2.extensions import connection

import pandas as pd
import warnings

# Suppress pandas UserWarning about using raw DBAPI2 connection objects
# pandas recommends SQLAlchemy connectables; we still support DBAPI2 via psycopg2,
# but the warning is noisy during pytest runs so suppress it here specifically.
warnings.filterwarnings(
    "ignore",
    message="pandas only supports SQLAlchemy connectable.*",
    category=UserWarning,
)
from pandas import DataFrame

from data_dev.config import postgres_config


class PostgresConnectorContextManager:
    """
    PostgreSQL Database Context Manager.

    This class provides a convenient way to manage PostgreSQL database connections
    using a context manager. It handles connection setup and teardown, and provides
    utility methods for interacting with the database.

    Attributes:
        host (str): Hostname of the PostgreSQL server.
        port (int): Port number of the PostgreSQL server.
        db (str): Name of the database to connect to.
        user (str): Username for authentication.
        password (str): Password for authentication.
        autocommit (bool): Whether to enable autocommit mode for the connection.
        connection (Optional[connection]): The active database connection object.
    """

    def __init__(self, db_host=None, db_port=None, db_name=None, db_user=None, db_password=None, autocommit=False):
        self.host = db_host or postgres_config.host
        self.port = int(db_port or postgres_config.port)
        self.db = db_name or postgres_config.db
        self.user = db_user or postgres_config.user
        self.password = db_password or postgres_config.password
        self.autocommit = autocommit
        self.connection = None

    def __enter__(self):
        """
        Enter the context manager and establish a database connection.

        Returns:
            PostgresConnectorContextManager: The context manager instance with an active connection.
        """
        self.connection = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.db,
            user=self.user,
            password=self.password
        )
        self.connection.autocommit = self.autocommit
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """
        Exit the context manager and close the database connection.

        Args:
            exc_type (type): The type of exception raised, if any.
            exc_value (Exception): The exception instance raised, if any.
            exc_tb (traceback): The traceback object associated with the exception, if any.
        """
        if self.connection:
            self.connection.close()

    def get_connection(self) -> Optional[connection]:
        """
        Get the active database connection.

        Returns:
            Optional[connection]: The active database connection object, or None if no connection exists.
        """
        return self.connection

    def get_data_sql(self, query: str) -> DataFrame:
        """
        Execute a SQL query and return the results as a pandas DataFrame.

        Args:
            query (str): The SQL query to execute.

        Returns:
            DataFrame: A pandas DataFrame containing the query results.

        Raises:
            Exception: If the query execution fails, an exception is raised with the error message.
        """
        try:
            # pandas emits a UserWarning when using a raw DBAPI2 connection
            # (it prefers a SQLAlchemy connectable). Suppress that specific
            # warning here to keep pytest output clean. For a long-term
            # solution, consider using SQLAlchemy's create_engine.
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="pandas only supports SQLAlchemy connectable.*",
                    category=UserWarning,
                )
                data_df = pd.read_sql(query, self.connection)
            return data_df
        except Exception as e:
            print(f'Failed to receive data from DB\nError: {e}\n')
            raise


def target_data(db_connection):
    target_query = """
    SELECT * from mydatabase.public.patients
    """
    target_data = db_connection.get_data_sql(target_query)
    print(target_data)
    return target_data
