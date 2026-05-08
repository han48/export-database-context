"""Shared pytest fixtures for db_schema_export tests."""

import pytest


@pytest.fixture
def sample_env_content():
    """Sample .env file content with all required variables."""
    return (
        'DB_CONNECTION=pgsql\n'
        'DB_HOST=127.0.0.1\n'
        'DB_PORT=5432\n'
        'DB_USERNAME=testuser\n'
        'DB_PASSWORD="testpass"\n'
        'DB_DATABASE=testdb\n'
    )


@pytest.fixture
def sample_env_multi_db_content():
    """Sample .env file content with multiple databases."""
    return (
        'DB_CONNECTION=pgsql\n'
        'DB_HOST=127.0.0.1\n'
        'DB_PORT=5432\n'
        'DB_USERNAME=testuser\n'
        'DB_PASSWORD="testpass"\n'
        'DB_DATABASES="db_one, db_two, db_three"\n'
    )


@pytest.fixture
def tmp_env_file(tmp_path, sample_env_content):
    """Create a temporary .env file with sample content."""
    env_file = tmp_path / ".env"
    env_file.write_text(sample_env_content)
    return env_file
