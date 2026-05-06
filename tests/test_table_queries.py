"""Unit tests for DataverseRestClient table query methods"""

import json
from unittest.mock import MagicMock

import pytest

from dataverse_client import DataverseConfig, DataverseRestClient
from dataverse_client.rest_client import TableMetadata

MOCK_TOKEN = {"access_token": "fake-token"}


@pytest.fixture
def mock_config():
    config = MagicMock(spec=DataverseConfig)
    config.client_id = "client_id"
    config.authority = "authority"
    config.username = "user"
    config.password = MagicMock()
    config.password.get_secret_value.return_value = "pass"
    config.scope = "scope"
    config.api_url = "https://api/"
    config.request_timeout_s = 60
    return config


@pytest.fixture
def table_raw():
    """Standard raw API response: two named tables (with mixed attributes) and one None-collection entry."""
    return [
        {
            "SchemaName": "AindMice",
            "LogicalCollectionName": "aind_mice",
            "Attributes": [
                {"MetadataId": "1", "LogicalName": "aind_col", "AttributeType": "String"},
                {"MetadataId": "2", "LogicalName": "other_col", "AttributeType": "Integer"},
            ],
        },
        {
            "SchemaName": "OtherSessions",
            "LogicalCollectionName": "other_sessions",
            "Attributes": [],
        },
        {
            "SchemaName": "NoCollection",
            "LogicalCollectionName": None,
            "Attributes": [],
        },
    ]


@pytest.fixture
def client(mock_config, mocker, table_raw):
    mock_app = MagicMock()
    mock_app.acquire_token_by_username_password.return_value = MOCK_TOKEN
    mocker.patch(
        "src.dataverse_client.rest_client.msal.PublicClientApplication", return_value=mock_app
    )
    client = DataverseRestClient(mock_config)
    mocker.patch.object(client, "query", return_value=table_raw)
    return client


# --- list_table_names ---


@pytest.mark.parametrize(
    "prefix, expected_names",
    [
        pytest.param("", ["aind_mice", "other_sessions"], id="no_filter_skips_none"),
        pytest.param("aind_", ["aind_mice"], id="prefix_filters_tables"),
    ],
)
def test_list_table_names(client, prefix, expected_names):
    result = client.list_table_names(filter_by_prefix=prefix)
    assert [t.LogicalCollectionName for t in result] == expected_names


# --- table_info ---


@pytest.mark.parametrize(
    "table_name",
    [
        pytest.param("aind_mice", id="string_name"),
        pytest.param(
            TableMetadata(SchemaName="AindMice", LogicalCollectionName="aind_mice"),
            id="table_metadata_object",
        ),
    ],
)
def test_table_info_name_types(client, table_name):
    """table_info accepts both a string and a TableMetadata object"""
    result = client.table_info(table_name)
    assert result.LogicalCollectionName == "aind_mice"
    assert "aind_mice" in str(client.query.call_args)


@pytest.mark.parametrize(
    "column_filter_prefix, expected_names",
    [
        pytest.param("aind_", ["aind_col"], id="aind_prefix"),
        pytest.param("other_", ["other_col"], id="other_prefix"),
        pytest.param("", ["aind_col", "other_col"], id="no_prefix"),
    ],
)
def test_table_info_column_filter(client, column_filter_prefix, expected_names):
    """table_info filters columns by column_filter_prefix"""
    result = client.table_info("aind_mice", column_filter_prefix=column_filter_prefix)
    assert [a.LogicalName for a in result.Attributes] == expected_names


def test_table_info_none_attributes_becomes_empty(client, mocker):
    """table_info sets Attributes to [] when API returns None"""
    raw = [{"SchemaName": "AindMice", "LogicalCollectionName": "aind_mice", "Attributes": None}]
    mocker.patch.object(client, "query", return_value=raw)
    assert client.table_info("aind_mice").Attributes == []


# --- list_table_info ---


@pytest.mark.parametrize(
    "kwargs, expected_table_names",
    [
        pytest.param({}, ["aind_mice", "other_sessions"], id="no_filters_skips_none"),
        pytest.param({"table_filter_prefix": "aind_"}, ["aind_mice"], id="table_filter_prefix"),
    ],
)
def test_list_table_info_table_filters(client, kwargs, expected_table_names):
    result = client.list_table_info(**kwargs)
    assert [t.LogicalCollectionName for t in result] == expected_table_names


@pytest.mark.parametrize(
    "column_filter_prefix, expected_names",
    [
        pytest.param("aind_", ["aind_col"], id="aind_prefix"),
        pytest.param("other_", ["other_col"], id="other_prefix"),
        pytest.param("", ["aind_col", "other_col"], id="no_prefix"),
    ],
)
def test_list_table_info_column_filter(client, column_filter_prefix, expected_names):
    """list_table_info filters columns by column_filter_prefix"""
    result = client.list_table_info(column_filter_prefix=column_filter_prefix)
    assert [a.LogicalName for a in result[0].Attributes] == expected_names


def test_list_table_info_none_attributes_becomes_empty(client, mocker):
    """list_table_info sets Attributes to [] when API returns None"""
    raw = [{"SchemaName": "A", "LogicalCollectionName": "aind_mice", "Attributes": None}]
    mocker.patch.object(client, "query", return_value=raw)
    assert client.list_table_info()[0].Attributes == []


def test_list_table_info_output_file(client, mocker, table_raw, tmp_path):
    """list_table_info writes JSON output to file when output_file is provided"""
    out_file = tmp_path / "out" / "tables.json"
    mocker.patch.object(client, "query", return_value=table_raw[:1])
    client.list_table_info(output_file=out_file)
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert len(data) == 1
    assert data[0]["LogicalCollectionName"] == "aind_mice"
