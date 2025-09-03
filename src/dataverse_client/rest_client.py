"""Client for interacting with the Dataverse API"""

from typing import Optional

import msal
from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings
import requests


class DataverseConfig(
    BaseSettings,
    validate_default=True,
    env_prefix="DATAVERSE_",
):
    """
    Configuration settings for the Dataverse client.
    Loads from environment variables prefixed with "DATAVERSE_"
    """

    tenant_id: str = "32669cd6-737f-4b39-8bdd-d6951120d3fc"
    client_id: str = "df37356e-3316-484a-b732-319b6b4ad464"
    org: str = "orgc1997c24"

    additional_scopes: list[str] = ["offline_access"]

    username: str = "svc_sipe"
    password: SecretStr

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
        return f"{self.env_url}/.default" + " ".join(self.additional_scopes)


class DataverseRestClient:
    """Client for basic CRUD operations on Dataverse entities."""

    def __init__(self, config: DataverseConfig):
        """
        Initialize the DataverseRestClient with configuration.
        Acquires an authentication token and sets up request headers.
        Args:
            config (DataverseConfig): Config object with credentials and URLs.
        """
        self.config = config
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
        )

        if not self.config.username.endswith("@alleninstitute.org"):
            username = self.config.username + "@alleninstitute.org"
        else:
            username = self.config.username

        token = app.acquire_token_by_username_password(
            username,
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

    def _construct_url(
        self,
        table: str,
        entry_id: Optional[str | dict] = None,
        filters: Optional[str] = None,
    ) -> str:
        """
        Construct the URL for a Dataverse table entry.
        Args:
            table (str): Table name.
            entry_id (str or dict, optional): Entry ID or alternate key.
        Returns:
            str: Constructed URL for the entry.
        """
        if entry_id is None:
            query = ""
        elif isinstance(entry_id, str):
            query = f"({entry_id})"
        elif isinstance(entry_id, dict):  # Can query by alternate key
            key = list(entry_id.keys())[0]
            value = list(entry_id.values())[0]
            if isinstance(value, str):
                # strings in url query must be formatted with single quotes
                value = f"'{value}'"
            query = f"({key}={value})"

        if filters:
            query += f"?$filter={filters}"

        url = self.config.api_url + table + query
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
            ValueError: If the entry cannot be fetched.
        """
        url = self._construct_url(table, id)
        response = requests.get(url, headers=self.headers)
        if not response.status_code == 200:
            raise ValueError(
                f"Error fetching {table}:"
                f" {response.status_code} {response.text}"
            )
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
            ValueError: If the entry cannot be added.
        """
        url = self._construct_url(table)
        response = requests.post(url, headers=self.headers, json=data)
        if not response.status_code == 200:
            raise ValueError(
                f"Error adding {table} entry:"
                f" {response.status_code} {response.text}"
            )
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
            ValueError: If the entry cannot be updated.
        """
        url = self._construct_url(table, id)
        headers = self.headers | {"Prefer": "return=representation"}
        response = requests.patch(url, headers=headers, json=update_data)
        if not response.status_code == 200:
            raise ValueError(
                f"Error updating {table} entry with id {id}:"
                f" {response.status_code} {response.text}"
            )
        return response.json()
