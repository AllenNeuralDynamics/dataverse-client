"""Unit tests for the DataverseRestClient"""

import unittest
from unittest.mock import patch, MagicMock
from dataverse_client import (
    DataverseRestClient,
    DataverseConfig,
)


class TestDataverseRestClient(unittest.TestCase):
    """Unit tests for the DataverseRestClient"""

    def setUp(self):
        """Set up mocks"""
        self.mock_token = {"access_token": "fake-token"}
        self.mock_config = MagicMock(spec=DataverseConfig)
        self.mock_config.client_id = "client_id"
        self.mock_config.authority = "authority"
        self.mock_config.username = "user"
        self.mock_config.password = MagicMock()
        self.mock_config.password.get_secret_value.return_value = "pass"
        self.mock_config.scope = "scope"
        self.mock_config.api_url = "https://api/"
        self.mock_config.request_timeout_s = 60

    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_construct_url_parametrized(self, mock_msal):
        """Parametrized test for _construct_url using subTest."""
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = self.mock_token
        mock_msal.return_value = mock_app
        client = DataverseRestClient(self.mock_config)
        client.config = MagicMock()
        client.config.api_url = "https://api/"
        test_cases = [
            {
                "table": "table",
                "entry_id": None,
                "expected": "https://api/table",
            },
            {
                "table": "table",
                "entry_id": "123",
                "expected": "https://api/table(123)",
            },
            {
                "table": "table",
                "entry_id": {"key": "val"},
                "expected": "https://api/table(key='val')",
            },
            {
                "table": "table",
                "entry_id": {"num": 42},
                "expected": "https://api/table(num=42)",
            },
            {
                "table": "table",
                "entry_id": {"key": "val", "key2": "val2"},
                "expected": "https://api/table(key='val')",  # only one key
            },
            {
                "table": "table",
                "entry_id": None,
                "filter": "key eq 'val'",
                "expected": "https://api/table?$filter=key eq 'val'",
            },
        ]
        for case in test_cases:
            with self.subTest(case["expected"]):
                result = client._construct_url(case["table"], case["entry_id"], case.get("filter"))
                self.assertEqual(result, case["expected"])

    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_construct_url_queries(self, mock_msal):
        """Parametrized test for _construct_url using subTest."""
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = self.mock_token
        mock_msal.return_value = mock_app
        client = DataverseRestClient(self.mock_config)
        client.config = MagicMock()
        client.config.api_url = "https://api/"
        table = "table"
        test_cases = [
            {
                "filter": "column eq 'value'",
                "expected": "https://api/table?$filter=column eq 'value'",
            },
            {
                "order_by": "column",
                "expected": "https://api/table?$orderby=column",
            },
            {
                "order_by": ["column1", "column2"],
                "expected": "https://api/table?$orderby=column1,column2",
            },
            {
                "top": 5,
                "expected": "https://api/table?$top=5",
            },
            {
                "count": True,
                "expected": "https://api/table?$count=true",
            },
            {
                "count": False,
                "expected": "https://api/table?$count=false",
            },
            {
                "select": "col1",
                "expected": "https://api/table?$select=col1",
            },
            {
                "select": ["col1", "col2"],
                "expected": "https://api/table?$select=col1,col2",
            },
            {
                "filter": "column eq 'value'",
                "order_by": "column",
                "top": 10,
                "count": True,
                "select": ["col1", "col2"],
                "expected": "https://api/table?$filter=column eq 'value'"
                + "&$orderby=column&$top=10&$count=true&$select=col1,col2",
            },
        ]
        for case in test_cases:
            with self.subTest(case["expected"]):
                expected = case.pop("expected")
                result = client._construct_url(table, **case)
                self.assertEqual(result, expected)

    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_acquire_token_success(self, mock_msal):
        """Test successful token acquisition"""
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = self.mock_token
        mock_msal.return_value = mock_app
        client = DataverseRestClient(self.mock_config)
        self.assertEqual(client.token, self.mock_token)

    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_acquire_token_failure(self, mock_msal):
        """Test failed token acquisition"""
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = {}
        mock_msal.return_value = mock_app
        with self.assertRaises(ValueError):
            DataverseRestClient(self.mock_config)

    @patch("src.dataverse_client.rest_client.requests.get")
    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_get_entry_success(self, mock_msal, mock_get):
        """Test successful retrieval of a Dataverse entry"""
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = self.mock_token
        mock_msal.return_value = mock_app
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "ok"}
        mock_get.return_value = mock_response
        client = DataverseRestClient(self.mock_config)
        result = client.get_entry("table", "id")
        self.assertEqual(result, {"result": "ok"})

    @patch("src.dataverse_client.rest_client.requests.post")
    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_add_entry_success(self, mock_msal, mock_post):
        """Test successful addition of a Dataverse entry"""
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = self.mock_token
        mock_msal.return_value = mock_app
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"added": True}
        mock_post.return_value = mock_response
        client = DataverseRestClient(self.mock_config)
        result = client.add_entry("table", {"data": 1})
        self.assertEqual(result, {"added": True})

    @patch("src.dataverse_client.rest_client.requests.patch")
    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_update_entry_success(self, mock_msal, mock_patch):
        """Test successful update of a Dataverse entry"""
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = self.mock_token
        mock_msal.return_value = mock_app
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"updated": True}
        mock_patch.return_value = mock_response
        client = DataverseRestClient(self.mock_config)
        result = client.update_entry("table", "id", {"update": 1})
        self.assertEqual(result, {"updated": True})


if __name__ == "__main__":
    unittest.main()
