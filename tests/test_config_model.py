"""Unit tests for DataverseConfig computed fields"""

import pytest
from pydantic import ValidationError

from dataverse_client import DataverseConfig

BASE_ARGS = {
    "tenant_id": "tenant-123",
    "client_id": "client-456",
    "org": "myorg",
    "username": "jdoe",
    "password": "secret",
}


@pytest.fixture
def config():
    return DataverseConfig(**BASE_ARGS)


def test_api_url(config):
    assert config.api_url == "https://myorg.crm.dynamics.com/api/data/v9.2/"


def test_env_url(config):
    assert config.env_url == "https://myorg.crm.dynamics.com"


def test_authority(config):
    assert config.authority == "https://login.microsoftonline.com/tenant-123"


def test_scope_default(config):
    assert config.scope == "https://myorg.crm.dynamics.com/.default offline_access"


def test_use_msal_defaults_true(config):
    assert config.use_msal is True


def test_scope_additional_scopes():
    cfg = DataverseConfig(**BASE_ARGS, additional_scopes=["offline_access", "openid"])
    assert cfg.scope == "https://myorg.crm.dynamics.com/.default offline_access openid"


@pytest.mark.parametrize(
    "username, expected",
    [
        pytest.param("jdoe", "jdoe@alleninstitute.org", id="plain_username"),
        pytest.param("jdoe@alleninstitute.org", "jdoe@alleninstitute.org", id="already_has_domain"),
        pytest.param(
            "jdoe@other.org", "jdoe@other.org@alleninstitute.org", id="other_domain_appended"
        ),
    ],
)
def test_username_at_domain(username, expected):
    cfg = DataverseConfig(**{**BASE_ARGS, "username": username})
    assert cfg.username_at_domain == expected


def test_username_at_domain_custom_domain():
    cfg = DataverseConfig(**BASE_ARGS, domain="custom.org")
    assert cfg.username_at_domain == "jdoe@custom.org"


def test_client_credentials_scope(config):
    assert config.client_credentials_scope == "https://myorg.crm.dynamics.com/.default"


def test_client_secret_only():
    cfg = DataverseConfig(
        tenant_id="tenant-123",
        client_id="client-456",
        org="myorg",
        username=None,
        password=None,
        client_secret="shhh",
    )
    assert cfg.client_secret.get_secret_value() == "shhh"
    assert cfg.username_at_domain is None


def test_missing_credentials_raises():
    with pytest.raises(ValidationError, match="username and password, or client_secret"):
        DataverseConfig(
            tenant_id="tenant-123",
            client_id="client-456",
            org="myorg",
            username=None,
            password=None,
            client_secret=None,
        )


def test_username_without_password_raises():
    with pytest.raises(ValidationError, match="username and password, or client_secret"):
        DataverseConfig(
            tenant_id="tenant-123",
            client_id="client-456",
            org="myorg",
            username="jdoe",
            password=None,
            client_secret=None,
        )
