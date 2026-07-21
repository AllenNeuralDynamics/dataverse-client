"""Unit tests for make_model_from_table_metadata"""

import pytest

from dataverse_client.rest_client import ColumnMetadata, TableMetadata
from generate_table_models import ModelModel, make_model_from_table_metadata


def col(name: str, atype: str, idx: int = 0) -> ColumnMetadata:
    return ColumnMetadata(MetadataId=str(idx), LogicalName=name, AttributeType=atype)


@pytest.fixture
def table():
    """Standard TableMetadata covering all supported column types."""
    return TableMetadata(
        SchemaName="aibs_mouse",
        LogicalCollectionName="aibs_mouses",
        Attributes=[
            col("name", "String", 0),
            col("owner", "Lookup", 1),
            col("ownername", "String", 2),  # shadow field — should be removed
            col("status", "Picklist", 3),
            col("statusname", "Virtual", 4),  # virtual — should be ignored
            col("record_id", "Uniqueidentifier", 5),
            col("score", "Double", 6),
            col("created_on", "DateTime", 7),
        ],
    )


def attr_names(model: ModelModel) -> list[str]:
    return [a.name for a in model.attributes]


# --- model name ---


@pytest.mark.parametrize(
    "schema_name, expected_class_name",
    [
        pytest.param("aibs_mouse", "AibsMouse", id="two_parts"),
        pytest.param("aibs_dim_mices", "AibsDimMices", id="three_parts"),
        pytest.param("simple", "Simple", id="no_underscore"),
    ],
)
def test_model_name_capwords(schema_name, expected_class_name):
    t = TableMetadata(SchemaName=schema_name, LogicalCollectionName="collection", Attributes=[])
    assert make_model_from_table_metadata(t).name == expected_class_name


# --- class vars ---


def test_class_var_attributes_set(table):
    model = make_model_from_table_metadata(table)
    names = attr_names(model)
    assert "_table_name" in names
    assert "_table_display_name" in names
    tname = next(a for a in model.attributes if a.name == "_table_name")
    assert '"aibs_mouses"' in tname.value
    tdname = next(a for a in model.attributes if a.name == "_table_display_name")
    assert '"aibs_mouse"' in tdname.value


# --- simple types ---


@pytest.mark.parametrize(
    "attr_type, expected_hint",
    [
        pytest.param("String", "Optional[str]", id="string"),
        pytest.param("Memo", "Optional[str]", id="memo"),
        pytest.param("Boolean", "Optional[bool]", id="boolean"),
        pytest.param("Integer", "Optional[int]", id="integer"),
        pytest.param("BigInt", "Optional[int]", id="bigint"),
        pytest.param("Double", "Optional[float]", id="double"),
        pytest.param("Decimal", "Optional[Decimal]", id="decimal"),
        pytest.param("DateTime", "Optional[datetime]", id="datetime"),
        pytest.param("Money", "Optional[Decimal]", id="money"),
        pytest.param("Owner", "Optional[str]", id="owner"),
        pytest.param("State", "Optional[int]", id="state"),
        pytest.param("Status", "Optional[int]", id="status"),
    ],
)
def test_simple_type_field(attr_type, expected_hint):
    t = TableMetadata(
        SchemaName="T", LogicalCollectionName="ts", Attributes=[col("my_col", attr_type)]
    )
    model = make_model_from_table_metadata(t)
    attr = next(a for a in model.attributes if a.name == "my_col")
    assert attr.type_hint == expected_hint
    assert attr.value == "None"


# --- UniqueIdentifier ---


def test_uniqueidentifier_field(table):
    model = make_model_from_table_metadata(table)
    attr = next(a for a in model.attributes if a.name == "record_id")
    assert attr.type_hint == "str"
    assert attr.value is None


# --- Lookup ---


def test_lookup_adds_guid_and_formatted_fields(table):
    model = make_model_from_table_metadata(table)
    names = attr_names(model)
    assert "owner_guid" in names
    assert "owner_formatted" in names
    guid_attr = next(a for a in model.attributes if a.name == "owner_guid")
    assert "_owner_value" in guid_attr.value
    fmt_attr = next(a for a in model.attributes if a.name == "owner_formatted")
    assert "FormattedValue" in fmt_attr.value


def test_lookup_removes_shadow_field(table):
    """The 'ownername' String shadow field that accompanies a Lookup should be dropped."""
    model = make_model_from_table_metadata(table)
    assert "ownername" not in attr_names(model)


def test_lookup_no_shadow_field_no_error():
    """No error when the lookup has no accompanying shadow String field."""
    t = TableMetadata(
        SchemaName="T", LogicalCollectionName="ts", Attributes=[col("owner", "Lookup")]
    )
    model = make_model_from_table_metadata(t)
    assert "owner_guid" in attr_names(model)


# --- Picklist ---


def test_picklist_adds_int_and_formatted_fields(table):
    model = make_model_from_table_metadata(table)
    names = attr_names(model)
    assert "status" in names
    assert "status_formatted" in names
    int_attr = next(a for a in model.attributes if a.name == "status")
    assert int_attr.type_hint == "Optional[int]"
    fmt_attr = next(a for a in model.attributes if a.name == "status_formatted")
    assert "FormattedValue" in fmt_attr.value


# --- Virtual ---


def test_virtual_fields_ignored(table):
    model = make_model_from_table_metadata(table)
    assert "statusname" not in attr_names(model)


# --- mixed columns ---


def test_mixed_columns(table):
    model = make_model_from_table_metadata(table)
    names = attr_names(model)

    assert "name" in names
    assert "owner_guid" in names
    assert "owner_formatted" in names
    assert "ownername" not in names
    assert "status" in names
    assert "status_formatted" in names
    assert "statusname" not in names
    assert "record_id" in names
