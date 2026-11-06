"""Configuration for the Dataverse client"""

from pathlib import Path

from platformdirs import site_data_dir
from pydantic import SecretStr, computed_field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

data_directory = Path(
    site_data_dir(
        "dataverse_client",
        "AllenInstitute",
    )
)


class DataverseConfig(
    BaseSettings,
    validate_default=True,
    extra="ignore",
    env_prefix="DATAVERSE_",
    env_file=".env",
    yaml_file=data_directory / "config.yml",
):
    """
    Configuration settings for the Dataverse client.
    Loads from environment variables prefixed with "DATAVERSE_"

    Authentication requires either a username and password (delegated user
    flow) or a client_secret (app-only client credentials flow).
    """

    tenant_id: str
    client_id: str
    org: str

    additional_scopes: list[str] = ["offline_access"]

    username: str | None = None
    password: SecretStr | None = None

    client_secret: SecretStr | None = None

    domain: str = "alleninstitute.org"

    use_msal: bool = True

    request_timeout_s: float = 60

    @model_validator(mode="after")
    def _check_credentials(self) -> "DataverseConfig":
        """Require either username/password or client_secret credentials."""
        has_user_credentials = self.username is not None and self.password is not None
        if not has_user_credentials and self.client_secret is None:
            raise ValueError(
                "Must provide either username and password, or client_secret, "
                "for authentication"
            )
        return self

    @computed_field
    @property
    def username_at_domain(self) -> str | None:
        """Username with domain for authentication. None if no username is set."""
        if self.username is None:
            return None
        if self.username.endswith(f"@{self.domain}"):
            return self.username
        return self.username + "@" + self.domain

    @computed_field
    @property
    def api_url(self) -> str:
        """Base URL for the Dataverse API."""
        return f"https://{self.org}.crm.dynamics.com/api/data/v9.2/"

    @computed_field
    @property
    def env_url(self) -> str:
        """Base URL for the Dataverse environment."""
        return f"https://{self.org}.crm.dynamics.com"

    @computed_field
    @property
    def authority(self) -> str:
        """Base URL for the Azure AD authority."""
        return f"https://login.microsoftonline.com/{self.tenant_id}"

    @computed_field
    @property
    def scope(self) -> str:
        """Scope for the Dataverse API (delegated user flow)."""
        return f"{self.env_url}/.default " + " ".join(self.additional_scopes)

    @computed_field
    @property
    def client_credentials_scope(self) -> str:
        """Scope for the client credentials (app-only) flow.
        Reserved scopes such as offline_access are not allowed here."""
        return f"{self.env_url}/.default"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Specify order of settings sources (yaml file, env vars, etc)"""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YamlConfigSettingsSource(settings_cls),
        )
