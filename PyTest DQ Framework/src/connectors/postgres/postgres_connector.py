
from typing import Optional
import psycopg2
from psycopg2.extensions import connection

import pandas as pd
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

    def __init__(self, autocommit: bool = False):
        """
        Initialize the database context manager.

        Args:
            autocommit (bool): Enable or disable autocommit mode for the connection.
                               Defaults to False.
        """
        self.host = postgres_config.host
        self.port = postgres_config.port
        self.db = postgres_config.db
        self.user = postgres_config.user
        self.password = postgres_config.password
        self.autocommit = autocommit
        self.connection: Optional[connection] = None

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
            data_df = pd.read_sql(query, self.connection)
            return data_df
        except Exception as e:
            print(f'Failed to receive data from DB\nError: {e}\n')
            raise


