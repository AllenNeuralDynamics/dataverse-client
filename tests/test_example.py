import unittest
from unittest.mock import patch, MagicMock
from src.dataverse_client.rest_client import (
    DataverseRestClient,
    DataverseConfig,
)


class TestDataverseRestClient(unittest.TestCase):
    def test_construct_url_parametrized(self):
        """
        Parametrized test for _construct_url using subTest.
        """
        client = DataverseRestClient.__new__(DataverseRestClient)
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
        ]
        for case in test_cases:
            with self.subTest(table=case["table"], entry_id=case["entry_id"]):
                result = client._construct_url(case["table"], case["entry_id"])
                self.assertEqual(result, case["expected"])

    def setUp(self):
        self.mock_token = {"access_token": "fake-token"}
        self.mock_config = MagicMock(spec=DataverseConfig)
        self.mock_config.client_id = "client_id"
        self.mock_config.authority = "authority"
        self.mock_config.username = "user"
        self.mock_config.password = MagicMock()
        self.mock_config.password.get_secret_value.return_value = "pass"
        self.mock_config.scope = "scope"
        self.mock_config.api_url = "https://api/"

    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_acquire_token_success(self, mock_msal):
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = (
            self.mock_token
        )
        mock_msal.return_value = mock_app
        client = DataverseRestClient(self.mock_config)
        self.assertEqual(client.token, self.mock_token)

    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_acquire_token_failure(self, mock_msal):
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = {}
        mock_msal.return_value = mock_app
        with self.assertRaises(ValueError):
            DataverseRestClient(self.mock_config)

    @patch("src.dataverse_client.rest_client.requests.get")
    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_get_entry_success(self, mock_msal, mock_get):
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = (
            self.mock_token
        )
        mock_msal.return_value = mock_app
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "ok"}
        mock_get.return_value = mock_response
        client = DataverseRestClient(self.mock_config)
        result = client.get_entry("table", "id")
        self.assertEqual(result, {"result": "ok"})

    @patch("src.dataverse_client.rest_client.requests.get")
    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_get_entry_failure(self, mock_msal, mock_get):
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = (
            self.mock_token
        )
        mock_msal.return_value = mock_app
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_get.return_value = mock_response
        client = DataverseRestClient(self.mock_config)
        with self.assertRaises(ValueError):
            client.get_entry("table", "id")

    @patch("src.dataverse_client.rest_client.requests.post")
    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_add_entry_success(self, mock_msal, mock_post):
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = (
            self.mock_token
        )
        mock_msal.return_value = mock_app
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"added": True}
        mock_post.return_value = mock_response
        client = DataverseRestClient(self.mock_config)
        result = client.add_entry("table", {"data": 1})
        self.assertEqual(result, {"added": True})

    @patch("src.dataverse_client.rest_client.requests.post")
    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_add_entry_failure(self, mock_msal, mock_post):
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = (
            self.mock_token
        )
        mock_msal.return_value = mock_app
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response
        client = DataverseRestClient(self.mock_config)
        with self.assertRaises(ValueError):
            client.add_entry("table", {"data": 1})

    @patch("src.dataverse_client.rest_client.requests.patch")
    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_update_entry_success(self, mock_msal, mock_patch):
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = (
            self.mock_token
        )
        mock_msal.return_value = mock_app
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"updated": True}
        mock_patch.return_value = mock_response
        client = DataverseRestClient(self.mock_config)
        result = client.update_entry("table", "id", {"update": 1})
        self.assertEqual(result, {"updated": True})

    @patch("src.dataverse_client.rest_client.requests.patch")
    @patch("src.dataverse_client.rest_client.msal.PublicClientApplication")
    def test_update_entry_failure(self, mock_msal, mock_patch):
        mock_app = MagicMock()
        mock_app.acquire_token_by_username_password.return_value = (
            self.mock_token
        )
        mock_msal.return_value = mock_app
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_patch.return_value = mock_response
        client = DataverseRestClient(self.mock_config)
        with self.assertRaises(ValueError):
            client.update_entry("table", "id", {"update": 1})


if __name__ == "__main__":
    unittest.main()
