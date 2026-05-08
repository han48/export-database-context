"""Environment file parser for Database Schema Export Tool.

This module reads and parses the .env file to extract database connection
configuration. It supports both single database (DB_DATABASE) and multiple
databases (DB_DATABASES as comma-separated list).
"""

from __future__ import annotations

import os

from dotenv import dotenv_values

from db_schema_export.exceptions import (
    EnvFileNotFoundError,
    MissingVariableError,
    NoDatabaseError,
)
from db_schema_export.models import DbConfig

# Required environment variables for database connection
REQUIRED_VARS = [
    "DB_CONNECTION",
    "DB_HOST",
    "DB_PORT",
    "DB_USERNAME",
    "DB_PASSWORD",
]


def parse_env(env_path: str) -> DbConfig:
    """Parse .env file and return database configuration.

    Reads the specified .env file and extracts database connection variables.
    Supports both single database (DB_DATABASE) and multiple databases
    (DB_DATABASES as comma-separated list with whitespace trimming).

    Args:
        env_path: Path to the .env file.

    Returns:
        DbConfig with parsed connection parameters and database list.

    Raises:
        EnvFileNotFoundError: If the .env file doesn't exist at the specified path.
        MissingVariableError: If any required variables are missing from the .env file.
        NoDatabaseError: If neither DB_DATABASES nor DB_DATABASE is defined.
    """
    # Check if file exists
    if not os.path.isfile(env_path):
        raise EnvFileNotFoundError(env_path)

    # Read .env file using python-dotenv
    values = dotenv_values(env_path)

    # Check for missing required variables
    missing = [var for var in REQUIRED_VARS if not values.get(var)]
    if missing:
        raise MissingVariableError(missing)

    # Parse databases: DB_DATABASES takes priority over DB_DATABASE
    databases: list[str] = []
    db_databases = values.get("DB_DATABASES")
    db_database = values.get("DB_DATABASE")

    if db_databases:
        # Parse comma-separated list and trim whitespace from each name
        databases = [db.strip() for db in db_databases.split(",") if db.strip()]
    elif db_database:
        databases = [db_database.strip()]

    if not databases:
        raise NoDatabaseError()

    return DbConfig(
        connection=values["DB_CONNECTION"],
        host=values["DB_HOST"],
        port=int(values["DB_PORT"]),
        username=values["DB_USERNAME"],
        password=values["DB_PASSWORD"],
        databases=databases,
    )
