"""Unit tests for the DataverseRestClient"""

import logging
from unittest.mock import MagicMock

import pytest

from dataverse_client import (
    DataverseConfig,
    DataverseRestClient,
    ClientSecretTokenHandler,
    TokenHandlerNoMsal,
    UserPasswordTokenHandler,
    get_token_handler,
)

MOCK_TOKEN = {"access_token": "fake-token"}


@pytest.fixture
def mock_config():
    config = MagicMock(spec=DataverseConfig)
    config.client_id = "client_id"
    config.authority = "authority"
    config.username = "user"
    config.password = MagicMock()
    config.password.get_secret_value.return_value = "pass"
    config.client_secret = None
    config.use_msal = True
    config.scope = "scope"
    config.api_url = "https://api/"
    config.request_timeout_s = 60
    return config


@pytest.fixture
def app_config():
    """Config for the client credentials (app-only) flow."""
    config = MagicMock(spec=DataverseConfig)
    config.client_id = "client_id"
    config.authority = "authority"
    config.username = None
    config.password = None
    config.client_secret = MagicMock()
    config.client_secret.get_secret_value.return_value = "secret"
    config.use_msal = True
    config.client_credentials_scope = "https://org.crm.dynamics.com/.default"
    config.api_url = "https://api/"
    config.request_timeout_s = 60
    return config


@pytest.fixture
def client(mock_config, mocker):
    mock_app = MagicMock()
    mock_app.acquire_token_by_username_password.return_value = MOCK_TOKEN
    mocker.patch(
        "src.dataverse_client.auth_utils.msal.PublicClientApplication", return_value=mock_app
    )
    return DataverseRestClient(mock_config)


@pytest.fixture
def app_client(app_config, mocker):
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = MOCK_TOKEN
    mocker.patch(
        "src.dataverse_client.auth_utils.msal.ConfidentialClientApplication",
        return_value=mock_app,
    )
    return DataverseRestClient(app_config)


@pytest.fixture
def failed_auth_client(mock_config, mocker):
    mock_app = MagicMock()
    mock_app.acquire_token_by_username_password.return_value = {}
    mock_app.get_accounts.return_value = []
    mocker.patch(
        "src.dataverse_client.auth_utils.msal.PublicClientApplication", return_value=mock_app
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


def test_client_credentials_uses_confidential_app(app_config, mocker):
    mock_confidential = mocker.patch(
        "src.dataverse_client.auth_utils.msal.ConfidentialClientApplication"
    )
    DataverseRestClient(app_config)
    mock_confidential.assert_called_once_with(
        client_id="client_id",
        authority="authority",
        client_credential="secret",
    )


def test_acquire_token_client_credentials_success(app_client):
    assert app_client.connected
    assert MOCK_TOKEN["access_token"] in app_client.headers["Authorization"]
    app_client._token_handler._msal_app.acquire_token_for_client.assert_called_with(
        scopes=["https://org.crm.dynamics.com/.default"]
    )


def test_acquire_token_client_credentials_failure(app_config, mocker):
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {
        "error": "invalid_client",
        "error_description": "bad secret",
    }
    mocker.patch(
        "src.dataverse_client.auth_utils.msal.ConfidentialClientApplication",
        return_value=mock_app,
    )
    failed_client = DataverseRestClient(app_config)
    assert not failed_client.connected
    with pytest.raises(ValueError, match="invalid_client"):
        _ = failed_client.headers


def test_no_credentials_raises(app_config, mocker):
    mocker.patch("src.dataverse_client.auth_utils.msal.PublicClientApplication")
    app_config.client_secret = None
    app_config.username = None
    app_config.password = None
    with pytest.raises(ValueError, match="No credentials configured"):
        DataverseRestClient(app_config)


# --- TokenHandlerNoMsal ---


def test_factory_selects_handlers(mock_config, app_config, mocker):
    mocker.patch("src.dataverse_client.auth_utils.msal.PublicClientApplication")
    mocker.patch("src.dataverse_client.auth_utils.msal.ConfidentialClientApplication")
    assert isinstance(get_token_handler(mock_config), UserPasswordTokenHandler)
    assert isinstance(get_token_handler(app_config), ClientSecretTokenHandler)
    assert isinstance(get_token_handler(app_config, use_msal=False), TokenHandlerNoMsal)


def test_factory_config_use_msal_false(app_config):
    app_config.use_msal = False
    assert isinstance(get_token_handler(app_config), TokenHandlerNoMsal)


def test_factory_no_msal_requires_client_secret(mock_config):
    mock_config.use_msal = False
    with pytest.raises(ValueError, match="only supported via MSAL"):
        get_token_handler(mock_config)


def test_no_msal_handler_acquires_and_caches_token(app_config, mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "fake-token", "expires_in": 3600}
    mock_post = mocker.patch(
        "src.dataverse_client.auth_utils.requests.post", return_value=mock_response
    )
    handler = TokenHandlerNoMsal(app_config)
    assert handler.connected
    assert handler.access_token == "fake-token"
    assert mock_post.call_count == 1  # token is cached, not re-requested
    assert mock_post.call_args[0][0] == "authority/oauth2/v2.0/token"
    payload = mock_post.call_args.kwargs["data"]
    assert payload["grant_type"] == "client_credentials"
    assert payload["client_secret"] == "secret"
    assert payload["scope"] == "https://org.crm.dynamics.com/.default"


def test_no_msal_handler_refreshes_expired_token(app_config, mocker):
    mock_response = MagicMock()
    mock_response.json.side_effect = [
        {"access_token": "token-1", "expires_in": 0},  # expires immediately
        {"access_token": "token-2", "expires_in": 3600},
    ]
    mock_post = mocker.patch(
        "src.dataverse_client.auth_utils.requests.post", return_value=mock_response
    )
    handler = TokenHandlerNoMsal(app_config)
    assert handler.access_token == "token-1"
    assert handler.access_token == "token-2"
    assert mock_post.call_count == 2


def test_no_msal_handler_failure(app_config, mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "error": "invalid_client",
        "error_description": "bad secret",
    }
    mocker.patch("src.dataverse_client.auth_utils.requests.post", return_value=mock_response)
    handler = TokenHandlerNoMsal(app_config)
    assert not handler.connected
    with pytest.raises(ValueError, match="invalid_client"):
        _ = handler.access_token


def test_no_msal_handler_requires_client_secret(app_config):
    app_config.client_secret = None
    with pytest.raises(ValueError, match="client_secret"):
        TokenHandlerNoMsal(app_config)


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
