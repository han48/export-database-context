"""Unit tests for data models."""

from db_schema_export.models import (
    ColumnMetadata,
    DbConfig,
    ForeignKeyMetadata,
    FunctionMetadata,
    InferredFK,
    SchemaMetadata,
    TableMetadata,
    TriggerMetadata,
    ViewMetadata,
)


def test_column_metadata_defaults():
    """Test ColumnMetadata has correct default values."""
    col = ColumnMetadata(name="id", data_type="integer", is_nullable=False, default_value=None)
    assert col.name == "id"
    assert col.data_type == "integer"
    assert col.is_nullable is False
    assert col.default_value is None
    assert col.is_primary_key is False
    assert col.is_foreign_key is False
    assert col.comment is None
    assert col.max_length is None


def test_column_metadata_all_fields():
    """Test ColumnMetadata with all fields specified."""
    col = ColumnMetadata(
        name="username",
        data_type="varchar",
        is_nullable=True,
        default_value="'anonymous'",
        is_primary_key=False,
        is_foreign_key=False,
        comment="User login name",
        max_length=255,
    )
    assert col.name == "username"
    assert col.max_length == 255
    assert col.comment == "User login name"


def test_table_metadata_defaults():
    """Test TableMetadata has correct default values."""
    table = TableMetadata(schema="public", name="users")
    assert table.schema == "public"
    assert table.name == "users"
    assert table.columns == []
    assert table.comment is None


def test_table_metadata_with_columns():
    """Test TableMetadata with columns list."""
    col = ColumnMetadata(name="id", data_type="integer", is_nullable=False, default_value=None)
    table = TableMetadata(schema="public", name="users", columns=[col], comment="Users table")
    assert len(table.columns) == 1
    assert table.columns[0].name == "id"
    assert table.comment == "Users table"


def test_foreign_key_metadata_defaults():
    """Test ForeignKeyMetadata has correct default values."""
    fk = ForeignKeyMetadata(
        source_schema="public",
        source_table="orders",
        source_column="user_id",
        target_schema="public",
        target_table="users",
        target_column="id",
    )
    assert fk.status == "confirmed"
    assert fk.confidence is None


def test_foreign_key_metadata_inferred():
    """Test ForeignKeyMetadata with inferred status."""
    fk = ForeignKeyMetadata(
        source_schema="public",
        source_table="orders",
        source_column="user_id",
        target_schema="public",
        target_table="users",
        target_column="id",
        status="inferred",
        confidence="high",
    )
    assert fk.status == "inferred"
    assert fk.confidence == "high"


def test_view_metadata_defaults():
    """Test ViewMetadata has correct default values."""
    view = ViewMetadata(
        schema="public",
        name="active_users",
        definition="SELECT * FROM users WHERE active = true",
    )
    assert view.columns == []


def test_view_metadata_with_columns():
    """Test ViewMetadata with columns."""
    col = ColumnMetadata(name="id", data_type="integer", is_nullable=False, default_value=None)
    view = ViewMetadata(
        schema="public",
        name="active_users",
        definition="SELECT * FROM users WHERE active = true",
        columns=[col],
    )
    assert len(view.columns) == 1


def test_function_metadata():
    """Test FunctionMetadata instantiation."""
    func = FunctionMetadata(
        schema="public",
        name="calc_tax",
        arguments="price_without_tax integer, tax_rate numeric",
        return_type="numeric",
        language="plpgsql",
        func_type="function",
    )
    assert func.schema == "public"
    assert func.name == "calc_tax"
    assert func.func_type == "function"


def test_trigger_metadata():
    """Test TriggerMetadata instantiation."""
    trigger = TriggerMetadata(
        schema="public",
        name="audit_log_trigger",
        table_name="orders",
        timing="AFTER",
        event="INSERT",
        function_name="log_changes",
    )
    assert trigger.timing == "AFTER"
    assert trigger.event == "INSERT"
    assert trigger.function_name == "log_changes"


def test_schema_metadata():
    """Test SchemaMetadata instantiation with all components."""
    table = TableMetadata(schema="public", name="users")
    fk = ForeignKeyMetadata(
        source_schema="public",
        source_table="orders",
        source_column="user_id",
        target_schema="public",
        target_table="users",
        target_column="id",
    )
    view = ViewMetadata(schema="public", name="v_users", definition="SELECT * FROM users")
    func = FunctionMetadata(
        schema="public",
        name="calc",
        arguments="x int",
        return_type="int",
        language="sql",
        func_type="function",
    )
    trigger = TriggerMetadata(
        schema="public",
        name="trg",
        table_name="orders",
        timing="BEFORE",
        event="UPDATE",
        function_name="validate",
    )

    meta = SchemaMetadata(
        database_name="testdb",
        schemas=["public"],
        tables=[table],
        foreign_keys=[fk],
        views=[view],
        functions=[func],
        triggers=[trigger],
    )
    assert meta.database_name == "testdb"
    assert len(meta.schemas) == 1
    assert len(meta.tables) == 1
    assert len(meta.foreign_keys) == 1
    assert len(meta.views) == 1
    assert len(meta.functions) == 1
    assert len(meta.triggers) == 1


def test_inferred_fk():
    """Test InferredFK instantiation."""
    inferred = InferredFK(
        source_schema="public",
        source_table="orders",
        source_column="user_id",
        target_schema="public",
        target_table="users",
        target_column="id",
        confidence="high",
        reason="Exact match: user_id -> users.id",
    )
    assert inferred.confidence == "high"
    assert inferred.reason == "Exact match: user_id -> users.id"


def test_db_config():
    """Test DbConfig instantiation."""
    config = DbConfig(
        connection="pgsql",
        host="127.0.0.1",
        port=5432,
        username="admin",
        password="secret",
        databases=["db1", "db2"],
    )
    assert config.connection == "pgsql"
    assert config.port == 5432
    assert config.databases == ["db1", "db2"]


def test_table_metadata_columns_not_shared():
    """Test that default list factory creates independent lists for each instance."""
    table1 = TableMetadata(schema="public", name="t1")
    table2 = TableMetadata(schema="public", name="t2")
    col = ColumnMetadata(name="id", data_type="int", is_nullable=False, default_value=None)
    table1.columns.append(col)
    assert len(table1.columns) == 1
    assert len(table2.columns) == 0
