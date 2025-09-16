"""Client for interacting with the Dataverse API"""

import logging
from pathlib import Path
from typing import Optional

import msal
from platformdirs import site_data_dir
from pydantic import SecretStr, computed_field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)
import requests

logger = logging.getLogger(__name__)

data_directory = Path(
    site_data_dir(
        "dataverse_client",
        "AllenInstitute",
    )
)


class DataverseConfig(
    BaseSettings,
    validate_default=True,
    env_prefix="DATAVERSE_",
    yaml_file=data_directory / "config.yml",
):
    """
    Configuration settings for the Dataverse client.
    Loads from environment variables prefixed with "DATAVERSE_"
    """

    tenant_id: str
    client_id: str
    org: str

    additional_scopes: list[str] = ["offline_access"]

    username: str
    password: SecretStr

    domain: str = "alleninstitute.org"

    request_timeout_s: float = 60

    @computed_field
    @property
    def username_at_domain(self) -> str:
        """Username with domain for authentication."""
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
        """Scope for the Dataverse API."""
        return f"{self.env_url}/.default " + " ".join(self.additional_scopes)

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


class DataverseRestClient:
    """Client for basic CRUD operations on Dataverse entities."""

    def __init__(self, config: Optional[DataverseConfig] = None):
        """
        Initialize the DataverseRestClient with configuration.
        Acquires an authentication token and sets up request headers.
        Args:
            config (DataverseConfig or None): Config object with credentials and URLs.
                If not provided, DataverseConfig() is called with no arguments, which
                will load from a file and environment variables
        """
        self.config = config or DataverseConfig()
        self.token = self._acquire_token()
        self.headers = {
            "Authorization": f"Bearer {self.token['access_token']}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
            "If-None-Match": None,
            "Content-Type": "application/json",
        }

    def _acquire_token(self):
        """
        Acquire an access token using MSAL and user credentials.
        Returns:
            dict: Token dictionary containing 'access_token'.
        Raises:
            ValueError: If token acquisition fails.
        """
        app = msal.PublicClientApplication(
            client_id=self.config.client_id,
            authority=self.config.authority,
            client_credential=None,
            timeout=self.config.request_timeout_s,
        )

        token = app.acquire_token_by_username_password(
            self.config.username_at_domain,
            self.config.password.get_secret_value(),
            scopes=[self.config.scope],
        )
        if "access_token" in token:
            return token
        else:
            raise ValueError(
                f"Error acquiring token: "
                f"{token.get('error')} : {token.get('error_description')}"
            )

    @staticmethod
    def _format_queries(
        filter: Optional[str] = None,
        order_by: Optional[str | list[str]] = None,
        top: Optional[int] = None,
        count: Optional[bool] = None,
        select: Optional[str | list[str]] = None,
    ) -> str:
        """
        Format query parameters for a Dataverse API request.
        Args:
            filter (str, optional): OData filter query.
            order_by (str or list[str], optional): OData order by clause.
            top (int, optional): OData top value.
            count (bool, optional): Include "@odata.count" in the response, counting matches
            select (str or list[str], optional): OData select clause.
        Returns:
            str: Formatted query string.
        """
        queries = []
        if filter:
            queries.append(f"$filter={filter}")
        if order_by:
            if isinstance(order_by, str):
                order_by = [order_by]
            queries.append(f"$orderby={','.join(order_by)}")
        if top is not None:
            queries.append(f"$top={top}")
        if count is not None:
            queries.append(f"$count={str(count).lower()}")
        if select:
            if isinstance(select, str):
                select = [select]
            queries.append(f"$select={','.join(select)}")
        return "?" + "&".join(queries) if len(queries) else ""

    def _construct_url(
        self,
        table: str,
        entry_id: Optional[str | dict] = None,
        filter: Optional[str] = None,
        order_by: Optional[str | list[str]] = None,
        top: Optional[int] = None,
        count: Optional[bool] = None,
        select: Optional[str | list[str]] = None,
    ) -> str:
        """
        Construct the URL for a Dataverse table entry.
        Args:
            table (str): Table name.
            entry_id (str or dict, optional): Entry ID or alternate key.
            filter (str, optional): OData filter query, e.g. "column eq 'value'".
            order_by (str or list[str], optional): Column or list of columns to order by
            top (int, optional): Return the top n results
            count (bool, optional): Include "@odata.count" in the response, counting matches
            select (str or list[str], optional): Columns to include in the response
        Returns:
            str: Constructed URL for the entry.
        """
        if entry_id is None:
            identifier = ""
        elif isinstance(entry_id, str):
            identifier = f"({entry_id})"
        elif isinstance(entry_id, dict):  # Can query by alternate key
            key = list(entry_id.keys())[0]
            value = list(entry_id.values())[0]
            if isinstance(value, str):
                # strings in url query must be formatted with single quotes
                value = f"'{value}'"
            identifier = f"({key}={value})"

        queries = self._format_queries(
            filter=filter,
            order_by=order_by,
            top=top,
            count=count,
            select=select,
        )

        url = self.config.api_url + table + identifier + queries

        return url

    def get_entry(self, table: str, id: str | dict) -> dict:
        """
        Get a Dataverse entry by ID or alternate key.
        Args:
            table (str): Table name.
            id (str or dict): Entry ID or alternate key.
        Returns:
            dict: Entry data as a dictionary.
        Raises:
            requests.HTTPError: If the entry cannot be fetched.
        """
        url = self._construct_url(table, id)
        response = requests.get(url, headers=self.headers, timeout=self.config.request_timeout_s)
        logger.info(
            f'Dataverse GET: "{url}", status code: {response.status_code}, '
            f"duration: {response.elapsed.total_seconds()} seconds"
        )
        response.raise_for_status()
        return response.json()

    def add_entry(self, table: str, data: dict) -> dict:
        """
        Add a new entry to a Dataverse table.
        Args:
            table (str): Table name.
            data (dict): Entry data to add.
        Returns:
            dict: Response data from Dataverse.
        Raises:
            requests.HTTPError: If the entry cannot be added.
        """
        url = self._construct_url(table)
        response = requests.post(
            url, headers=self.headers, json=data, timeout=self.config.request_timeout_s
        )
        logger.info(
            f'Dataverse POST: "{url}", status code: {response.status_code}, '
            f"duration: {response.elapsed.total_seconds()} seconds"
        )
        response.raise_for_status()
        return response.json()

    def update_entry(
        self,
        table: str,
        id: str | dict,
        update_data: dict,
    ) -> dict:
        """
        Update an existing entry in a Dataverse table.
        Args:
            table (str): Table name.
            id (str or dict): Entry ID or alternate key.
            update_data (dict): Data to update.
        Returns:
            dict: Updated entry data from Dataverse.
        Raises:
            requests.HTTPError: If the entry cannot be updated.
        """
        url = self._construct_url(table, id)
        headers = self.headers | {"Prefer": "return=representation"}
        response = requests.patch(
            url, headers=headers, json=update_data, timeout=self.config.request_timeout_s
        )
        logger.info(
            f'Dataverse PATCH: "{url}", status code: {response.status_code}, '
            f"duration: {response.elapsed.total_seconds()} seconds"
        )
        response.raise_for_status()
        return response.json()

    def query(
        self,
        table: str,
        filter: Optional[str] = None,
        order_by: Optional[str | list[str]] = None,
        top: Optional[int] = None,
        select: Optional[str | list[str]] = None,
    ) -> list[dict]:
        """
        Query a Dataverse table for multiple entries based on filters.
        For details, see https://www.odata.org/getting-started/basic-tutorial/#queryData
        https://docs.oasis-open.org/odata/odata/v4.0/errata03/os/complete/part1-protocol/odata-v4.0-errata03-os-part1-protocol-complete.html#_The_$filter_System # noqa
        Args:
            table (str): Table name.
            filter (str, optional): OData filter query, e.g. "column eq 'value'".
            order_by (str or list[str], optional): Column or list of columns to order by
            top (int, optional): Return the top n results
            select (str or list[str], optional): Columns to include in the response
        Returns:
            dict: Query results from Dataverse.
        Raises:
            requests.HTTPError: If the query fails.
        """
        url = self._construct_url(
            table,
            filter=filter,
            order_by=order_by,
            top=top,
            select=select,
        )
        # Note: Could also provide `count`, but it's not useful for this method as this
        # returns a list of values, and wouldn't include the "@odata.count" property anyway
        response = requests.get(url, headers=self.headers, timeout=self.config.request_timeout_s)
        logger.info(
            f'Dataverse GET: "{url}", status code: {response.status_code}, '
            f"duration: {response.elapsed.total_seconds()} seconds"
        )
        response.raise_for_status()
        return response.json().get("value", [])
