"""Unit tests for the DataverseRestClient"""

import logging
from unittest.mock import MagicMock

import pytest

from dataverse_client import DataverseConfig, DataverseRestClient

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
def client(mock_config, mocker):
    mock_app = MagicMock()
    mock_app.acquire_token_by_username_password.return_value = MOCK_TOKEN
    mocker.patch(
        "src.dataverse_client.rest_client.msal.PublicClientApplication", return_value=mock_app
    )
    return DataverseRestClient(mock_config)


@pytest.fixture
def failed_auth_client(mock_config, mocker):
    mock_app = MagicMock()
    mock_app.acquire_token_by_username_password.return_value = {}
    mock_app.get_accounts.return_value = []
    mocker.patch(
        "src.dataverse_client.rest_client.msal.PublicClientApplication", return_value=mock_app
    )
    return DataverseRestClient(mock_config)


# --- _construct_url ---


@pytest.mark.parametrize(
    "entry_id, filter, expected",
    [
        pytest.param(None, None, "https://api/table", id="no_id"),
        pytest.param("123", None, "https://api/table(123)", id="string_id"),
        pytest.param({"key": "val"}, None, "https://api/table(key='val')", id="dict_str_value"),
        pytest.param({"num": 42}, None, "https://api/table(num=42)", id="dict_int_value"),
        pytest.param(
            {"key": "val", "key2": "val2"},
            None,
            "https://api/table(key='val')",
            id="dict_first_key_only",
        ),
        pytest.param(
            None, "key eq 'val'", "https://api/table?$filter=key eq 'val'", id="filter_only"
        ),
    ],
)
def test_construct_url(client, entry_id, filter, expected):
    assert client._construct_url("table", entry_id, filter) == expected


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        pytest.param(
            {"filter": "column eq 'value'"},
            "https://api/table?$filter=column eq 'value'",
            id="filter",
        ),
        pytest.param(
            {"order_by": "column"}, "https://api/table?$orderby=column", id="order_by_str"
        ),
        pytest.param(
            {"order_by": ["column1", "column2"]},
            "https://api/table?$orderby=column1,column2",
            id="order_by_list",
        ),
        pytest.param({"top": 5}, "https://api/table?$top=5", id="top"),
        pytest.param({"count": True}, "https://api/table?$count=true", id="count_true"),
        pytest.param({"count": False}, "https://api/table?$count=false", id="count_false"),
        pytest.param({"select": "col1"}, "https://api/table?$select=col1", id="select_str"),
        pytest.param(
            {"select": ["col1", "col2"]}, "https://api/table?$select=col1,col2", id="select_list"
        ),
        pytest.param(
            {"expand": "related_entity"},
            "https://api/table?$expand=related_entity",
            id="expand_str",
        ),
        pytest.param(
            {"expand": ["related_entity", "another_entity"]},
            "https://api/table?$expand=related_entity,another_entity",
            id="expand_list",
        ),
        pytest.param(
            {
                "filter": "column eq 'value'",
                "order_by": "column",
                "top": 10,
                "count": True,
                "select": ["col1", "col2"],
            },
            "https://api/table?$filter=column eq 'value'&$orderby=column&$top=10&$count=true&$select=col1,col2",
            id="combined",
        ),
    ],
)
def test_construct_url_queries(client, kwargs, expected):
    assert client._construct_url("table", **kwargs) == expected


# --- auth ---


def test_acquire_token_success(client):
    assert client.connected
    assert MOCK_TOKEN["access_token"] in client.headers["Authorization"]


def test_acquire_token_failure(failed_auth_client):
    with pytest.raises(ValueError):
        _ = failed_auth_client.headers


def test_connection_failure(failed_auth_client):
    assert not failed_auth_client.connected


# --- CRUD ---


def test_get_entry_success(client, mocker):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "ok"}
    mocker.patch("src.dataverse_client.rest_client.requests.get", return_value=mock_response)
    assert client.get_entry("table", "id") == {"result": "ok"}


def test_add_entry_success(client, mocker):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"added": True}
    mocker.patch("src.dataverse_client.rest_client.requests.post", return_value=mock_response)
    assert client.add_entry("table", {"data": 1}) == {"added": True}


def test_update_entry_success(client, mocker):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"updated": True}
    mocker.patch("src.dataverse_client.rest_client.requests.patch", return_value=mock_response)
    assert client.update_entry("table", "id", {"update": 1}) == {"updated": True}


# --- query ---


def test_query_returns_value_list(client, mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"value": [{"id": 1}, {"id": 2}]}
    mocker.patch("src.dataverse_client.rest_client.requests.get", return_value=mock_response)
    assert client.query("table") == [{"id": 1}, {"id": 2}]


def test_query_empty_value(client, mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"value": []}
    mocker.patch("src.dataverse_client.rest_client.requests.get", return_value=mock_response)
    assert client.query("table") == []


def test_query_missing_value_key(client, mocker):
    """query returns [] when the response has no 'value' key"""
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mocker.patch("src.dataverse_client.rest_client.requests.get", return_value=mock_response)
    assert client.query("table") == []


def test_query_raises_on_http_error(client, mocker):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("404")
    mocker.patch("src.dataverse_client.rest_client.requests.get", return_value=mock_response)
    with pytest.raises(Exception, match="404"):
        client.query("table")


def test_query_passes_params_in_url(client, mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"value": []}
    mock_get = mocker.patch(
        "src.dataverse_client.rest_client.requests.get", return_value=mock_response
    )
    client.query("table", filter="col eq 'x'", top=5, select=["col"])
    called_url = mock_get.call_args[0][0]
    assert "$filter=col eq 'x'" in called_url
    assert "$top=5" in called_url
    assert "$select=col" in called_url


# --- logging ---


@pytest.mark.parametrize(
    "method, operation, call_fn",
    [
        pytest.param(
            "src.dataverse_client.rest_client.requests.get",
            "GET",
            lambda c: c.get_entry("table", "id"),
            id="get_entry",
        ),
        pytest.param(
            "src.dataverse_client.rest_client.requests.post",
            "POST",
            lambda c: c.add_entry("table", {"k": "v"}),
            id="add_entry",
        ),
        pytest.param(
            "src.dataverse_client.rest_client.requests.patch",
            "PATCH",
            lambda c: c.update_entry("table", "id", {"k": "v"}),
            id="update_entry",
        ),
        pytest.param(
            "src.dataverse_client.rest_client.requests.get",
            "GET",
            lambda c: c.query("table"),
            id="query",
        ),
    ],
)
def test_debug_log_on_request(client, mocker, caplog, method, operation, call_fn):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"value": []}
    mocker.patch(method, return_value=mock_response)
    with caplog.at_level(logging.DEBUG, logger="dataverse_client.rest_client"):
        call_fn(client)
    assert any(
        f"Dataverse {operation}:" in r.message and "status code:" in r.message
        for r in caplog.records
    )
