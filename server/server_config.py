"""
Database Configuration and Connection Management

Handles PostgreSQL connections for the voting system.
"""

import psycopg2
from psycopg2 import pool
import os


class DatabaseConfig:
    """PostgreSQL database configuration."""

    def __init__(self,
                 host=None,
                 port=None,
                 database=None,
                 user=None,
                 password=None):
        """
        Initialize database configuration.

        Reads from environment variables if not provided:
        - VOTING_DB_HOST (default: localhost)
        - VOTING_DB_PORT (default: 5432)
        - VOTING_DB_NAME (default: voting_system)
        - VOTING_DB_USER (default: postgres)
        - VOTING_DB_PASSWORD (default: empty)
        """
        self.host = host or os.getenv('VOTING_DB_HOST', 'localhost')
        self.port = port or os.getenv('VOTING_DB_PORT', 5432)
        self.database = database or os.getenv('VOTING_DB_NAME', 'voting_system')
        self.user = user or os.getenv('VOTING_DB_USER', 'postgres')
        self.password = password or os.getenv('VOTING_DB_PASSWORD', '')

    def get_connection_string(self):
        """Get PostgreSQL connection string."""
        if self.password:
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            return f"postgresql://{self.user}@{self.host}:{self.port}/{self.database}"

    def get_connect_kwargs(self):
        """Get connection kwargs for psycopg2."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password if self.password else None
        }


class DatabaseConnection:
    """PostgreSQL connection pool manager."""

    _pool = None

    @classmethod
    def initialize(cls, config, min_connections=2, max_connections=10):
        """
        Initialize connection pool.

        Args:
            config: DatabaseConfig instance
            min_connections: Minimum pool size
            max_connections: Maximum pool size
        """
        try:
            cls._pool = psycopg2.pool.SimpleConnectionPool(
                min_connections,
                max_connections,
                **config.get_connect_kwargs()
            )
        except psycopg2.Error as e:
            raise Exception(f"Failed to create database pool: {e}")

    @classmethod
    def get_connection(cls):
        """
        Get a connection from the pool.

        Returns:
            psycopg2 connection
        """
        if cls._pool is None:
            raise Exception("Database pool not initialized. Call initialize() first.")
        return cls._pool.getconn()

    @classmethod
    def return_connection(cls, conn):
        """Return connection to pool."""
        if cls._pool is not None:
            cls._pool.putconn(conn)

    @classmethod
    def close_all(cls):
        """Close all connections in pool."""
        if cls._pool is not None:
            cls._pool.closeall()


def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """
    Execute a database query.

    Args:
        query: SQL query string
        params: Query parameters (optional)
        fetch_one: Return single row
        fetch_all: Return all rows

    Returns:
        Query result or None
    """
    conn = DatabaseConnection.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())

        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = None

        cursor.close()
        return result
    except psycopg2.Error as e:
        conn.rollback()
        raise Exception(f"Database error: {e}")
    finally:
        DatabaseConnection.return_connection(conn)


def execute_many(query, params_list):
    """
    Execute a query multiple times with different parameters.

    Args:
        query: SQL query string
        params_list: List of parameter tuples

    Returns:
        Number of rows affected
    """
    conn = DatabaseConnection.get_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        rowcount = cursor.rowcount
        conn.commit()
        cursor.close()
        return rowcount
    except psycopg2.Error as e:
        conn.rollback()
        raise Exception(f"Database error: {e}")
    finally:
        DatabaseConnection.return_connection(conn)


def init_database(config):
    """
    Initialize database schema.

    Reads db_setup.sql and executes it.

    Args:
        config: DatabaseConfig instance
    """
    import os

    # Get path to db_setup.sql
    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_file = os.path.join(script_dir, 'db_setup.sql')

    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"Schema file not found: {schema_file}")

    # Read schema
    with open(schema_file, 'r') as f:
        schema_sql = f.read()

    # Execute schema
    conn = DatabaseConnection.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(schema_sql)
        conn.commit()
        cursor.close()
        print("✓ Database schema initialized")
    except psycopg2.Error as e:
        conn.rollback()
        raise Exception(f"Failed to initialize schema: {e}")
    finally:
        DatabaseConnection.return_connection(conn)
