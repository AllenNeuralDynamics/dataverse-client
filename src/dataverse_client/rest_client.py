"""Client for interacting with the Dataverse API"""

import logging
from pathlib import Path
from typing import Optional
import json

import msal
from platformdirs import site_data_dir
from pydantic import BaseModel, SecretStr, computed_field
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
    extra="ignore",
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


#### Simple models for database table metadata


class ColumnMetadata(BaseModel):
    MetadataId: str
    LogicalName: str
    AttributeType: str


class TableMetadata(BaseModel):
    SchemaName: str
    LogicalCollectionName: str
    Attributes: Optional[list[ColumnMetadata]] = None


####


class DataverseRestClient:
    """Client for basic CRUD operations on Dataverse entities."""

    def __init__(self, config: DataverseConfig):
        """
        Initialize the DataverseRestClient with configuration.

        Args:
            config: Config object with credentials and URLs
        """
        self.config = config
        self._msal_app = msal.PublicClientApplication(
            client_id=self.config.client_id,
            authority=self.config.authority,
            client_credential=None,
        )

    @property
    def connected(self) -> bool:
        """Check if the client can acquire an access token."""
        try:
            _ = self._get_access_token()
            return True
        except ValueError:
            return False

    @property
    def headers(self) -> dict:
        """Get the headers for Dataverse API requests."""
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
            "If-None-Match": None,
            "Content-Type": "application/json",
            "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue",return=representation',
        }

    def _get_access_token(self) -> str:
        """
        Get a valid access token.

        Returns:
            str: Valid access token

        Raises:
            ValueError: If token acquisition fails
        """
        accounts = self._msal_app.get_accounts(username=self.config.username_at_domain)

        if accounts:
            result = self._msal_app.acquire_token_silent(
                scopes=[self.config.scope], account=accounts[0]
            )
            if result and "access_token" in result:
                return result["access_token"]

        result = self._msal_app.acquire_token_by_username_password(
            username=self.config.username_at_domain,
            password=self.config.password.get_secret_value(),
            scopes=[self.config.scope],
        )

        if "access_token" in result:
            return result["access_token"]
        else:
            raise ValueError(
                f"Error acquiring token: {result.get('error')} : {result.get('error_description')}"
            )

    @staticmethod
    def _format_queries(
        filter: Optional[str] = None,
        order_by: Optional[str | list[str]] = None,
        top: Optional[int] = None,
        count: Optional[bool] = None,
        select: Optional[str | list[str]] = None,
        expand: Optional[str | list[str]] = None,
    ) -> str:
        """
        Format query parameters for a Dataverse API request.

        Args:
            filter: OData filter query. Defaults to None
            order_by: OData order by clause. Defaults to None
            top: OData top value. Defaults to None
            count: Include "@odata.count" in the response, counting matches. Defaults to None
            select: OData select clause. Defaults to None
            expand: OData expand clause. Defaults to None

        Returns:
            str: Formatted query string
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
        if expand:
            if isinstance(expand, str):
                expand = [expand]
            queries.append(f"$expand={','.join(expand)}")
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
        expand: Optional[str | list[str]] = None,
    ) -> str:
        """
        Construct the URL for a Dataverse table entry.

        Args:
            table: Table name
            entry_id: Entry ID or alternate key. Defaults to None
            filter: OData filter query, e.g. "column eq 'value'". Defaults to None
            order_by: Column or list of columns to order by. Defaults to None
            top: Return the top n results. Defaults to None
            count: Include "@odata.count" in the response, counting matches. Defaults to None
            select: Columns to include in the response. Defaults to None
            expand: Related entities to include in the response. Defaults to None
        Returns:
            str: Constructed URL for the entry
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
        else:
            raise ValueError("entry_id must be a string or dictionary")

        queries = self._format_queries(
            filter=filter,
            order_by=order_by,
            top=top,
            count=count,
            select=select,
            expand=expand,
        )

        url = self.config.api_url + table + identifier + queries

        return url

    def get_entry(self, table: str, id: str | dict) -> dict:
        """
        Get a Dataverse entry by ID or alternate key.

        Args:
            table: Table name
            id: Entry ID or alternate key

        Returns:
            dict: Entry data as a dictionary

        Raises:
            ValueError: If the entry cannot be fetched
        """
        url = self._construct_url(table, id)
        response = requests.get(url, headers=self.headers, timeout=self.config.request_timeout_s)
        logger.debug(
            f'Dataverse GET: "{url}", status code: {response.status_code}, '
            f"duration: {response.elapsed.total_seconds()} seconds"
        )
        response.raise_for_status()
        return response.json()

    def add_entry(self, table: str, data: dict) -> Optional[dict]:
        """
        Add a new entry to a Dataverse table.

        Args:
            table: Table name
            data: Entry data to add

        Returns:
            Optional[dict]: Response data from Dataverse

        Raises:
            ValueError: If the entry cannot be added
        """
        url = self._construct_url(table)
        response = requests.post(
            url, headers=self.headers, json=data, timeout=self.config.request_timeout_s
        )
        logger.debug(
            f'Dataverse POST: "{url}", status code: {response.status_code}, '
            f"duration: {response.elapsed.total_seconds()} seconds"
        )
        response.raise_for_status()
        if response.status_code == 204:
            return None
        else:
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
            table: Table name
            id: Entry ID or alternate key
            update_data: Data to update

        Returns:
            dict: Updated entry data from Dataverse

        Raises:
            ValueError: If the entry cannot be updated
        """
        url = self._construct_url(table, id)
        headers = self.headers | {"Prefer": "return=representation"}
        response = requests.patch(
            url, headers=headers, json=update_data, timeout=self.config.request_timeout_s
        )
        logger.debug(
            f'Dataverse PATCH: "{url}", status code: {response.status_code}, '
            f"duration: {response.elapsed.total_seconds()} seconds"
        )
        response.raise_for_status()
        return response.json()

    def query(
        self,
        table: str,
        filter: Optional[str] = None,
        order_by: Optional[str] = None,
        top: Optional[int] = None,
        select: Optional[list[str]] = None,
        expand: Optional[str | list[str]] = None,
    ) -> list[dict]:
        """
        Query a Dataverse table for multiple entries based on filters.

        For details, see https://www.odata.org/getting-started/basic-tutorial/#queryData
        and https://docs.oasis-open.org/odata/odata/v4.0/errata03/os/complete/part1-protocol/odata-v4.0-errata03-os-part1-protocol-complete.html#_The_$filter_System # noqa

        Args:
            table: Table name
            filter: OData filter query, e.g. "column eq 'value'". Defaults to None
            order_by: Column or list of columns to order by. Defaults to None
            top: Return the top n results. Defaults to None
            select: Columns to include in the response. Defaults to None
            expand: Related entities to include in the response. Defaults to None
        Returns:
            list[dict]: Query results from Dataverse
        """
        url = self._construct_url(
            table,
            filter=filter,
            order_by=order_by,
            top=top,
            select=select,
            expand=expand,
        )
        # Note: Could also provide `count`, but it's not useful for this method as this
        # returns a list of values, and wouldn't include the "@odata.count" property anyway
        response = requests.get(
            url,
            headers=self.headers,  # | {"Prefer": "return=representation"},
            timeout=self.config.request_timeout_s,
        )
        logger.debug(
            f'Dataverse GET: "{url}", status code: {response.status_code}, '
            f"duration: {response.elapsed.total_seconds()} seconds"
        )
        response.raise_for_status()
        return response.json().get("value", [])

    def list_table_names(self, filter_by_prefix: str = "") -> list[TableMetadata]:
        """List all table names in the Dataverse environment, optionally filtering by prefix.
        For each table, return the logical name and the display name (schema name)

        Args:
            filter_by_prefix: If provided, only return tables whose logical name starts with this prefix.
        Returns:
            list[TableMetadata]: List of table metadata objects with no column information
        """
        data = self.query("EntityDefinitions", select=["SchemaName", "LogicalCollectionName"])
        tables = [TableMetadata(**t) for t in data if t["LogicalCollectionName"] is not None]
        if filter_by_prefix:
            tables = [t for t in tables if t.LogicalCollectionName.startswith(filter_by_prefix)]
        return tables

    def table_info(
        self,
        table_name: str | TableMetadata,
        column_filter_prefix: str = "",
    ) -> TableMetadata:
        """Get metadata for a Dataverse table, including column names and types.

        Args:
            table_name: The logical name of the table or a TableMetadata object.
            column_filter_prefix: If provided, only include columns whose logical name starts with this prefix.
        Returns:
            TableMetadata: Metadata for the specified table, including column information
        """
        if isinstance(table_name, TableMetadata):
            table_name = table_name.LogicalCollectionName
        data = self.query(
            "EntityDefinitions",
            filter=f"LogicalCollectionName eq '{table_name}'",
            select=["SchemaName", "LogicalCollectionName"],
            expand="Attributes($select=LogicalName,AttributeType)",
        )[0]
        table = TableMetadata(**data)
        if column_filter_prefix:
            table.Attributes = [
                a for a in table.Attributes or [] if a.LogicalName.startswith(column_filter_prefix)
            ]
        return table

    def list_table_info(
        self,
        table_filter_prefix: str = "",
        column_filter_prefix: str = "",
        output_file: Optional[Path] = None,
    ) -> list[TableMetadata]:
        """Get table metadata for all tables, optionally filtering table logical name by prefix.
        Microsoft doesn't let you filter metadata by "starts_with(...)" so we have to filter on our own.

        Args:
            table_filter_prefix: If provided, only include tables whose logical name starts with this prefix.
            column_filter_prefix: If provided, only include columns whose logical name starts with this prefix.
            output_file: If provided, write the metadata to this file in JSON format.
        Returns:
            list[TableMetadata]: List of table metadata objects, including column information
        """
        all_tables = self.query(
            "EntityDefinitions",
            select=["SchemaName", "LogicalCollectionName"],
            expand="Attributes($select=LogicalName,AttributeType)",
        )
        if table_filter_prefix:
            tables_of_interest = [
                TableMetadata(**t)
                for t in all_tables
                if t["LogicalCollectionName"] is not None
                and t["LogicalCollectionName"].startswith(table_filter_prefix)
            ]
        if column_filter_prefix:
            for t in tables_of_interest:
                t.Attributes = [
                    a for a in t.Attributes or [] if a.LogicalName.startswith(column_filter_prefix)
                ]
        if output_file:
            Path(output_file).parent.mkdir(exist_ok=True, parents=True)
            with open(output_file, "w") as f:
                json.dump([t.model_dump() for t in tables_of_interest], f, indent=2)
        return tables_of_interest
