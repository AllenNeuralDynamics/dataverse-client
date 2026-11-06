"""Token handlers for authenticating with the Dataverse API"""

import datetime

import msal
import requests

from .config import DataverseConfig


class TokenHandler:
    """Base class for Dataverse token handlers."""

    def __init__(self, config: DataverseConfig):
        """
        Initialize the token handler with configuration.

        Args:
            config: Config object with credentials and URLs
        """
        self.config = config

    @property
    def connected(self) -> bool:
        """Check if the handler can acquire an access token."""
        try:
            _ = self.access_token
            return True
        except ValueError:
            return False

    @property
    def access_token(self) -> str:
        """Get a valid access token.

        Raises:
            ValueError: If token acquisition fails
        """
        return self._get_access_token()

    def _get_access_token(self) -> str:
        """Acquire an access token. Implemented by subclasses."""
        raise NotImplementedError

    @staticmethod
    def _extract_token(result: dict) -> str:
        """Extract the access token from a token result, or raise ValueError."""
        if "access_token" in result:
            return result["access_token"]
        raise ValueError(
            f"Error acquiring token: {result.get('error')} : {result.get('error_description')}"
        )


class UserPasswordTokenHandler(TokenHandler):
    """Acquires tokens with username/password (delegated user flow)."""

    def __init__(self, config: DataverseConfig):
        super().__init__(config)
        self._msal_app = msal.PublicClientApplication(
            client_id=self.config.client_id,
            authority=self.config.authority,
            client_credential=None,
        )

    def _get_access_token(self) -> str:
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
        return self._extract_token(result)


class ClientSecretTokenHandler(TokenHandler):
    """Acquires tokens with a client secret (app-only client credentials flow)."""

    def __init__(self, config: DataverseConfig):
        super().__init__(config)
        self._msal_app = msal.ConfidentialClientApplication(
            client_id=self.config.client_id,
            authority=self.config.authority,
            client_credential=self.config.client_secret.get_secret_value(),
        )

    def _get_access_token(self) -> str:
        # MSAL checks its token cache internally
        result = self._msal_app.acquire_token_for_client(
            scopes=[self.config.client_credentials_scope]
        )
        return self._extract_token(result)


class TokenHandlerNoMsal(TokenHandler):
    """Acquires tokens with a client secret (app-only client credentials flow)
    by calling the Azure AD token endpoint directly, without MSAL.

    Tokens are cached and refreshed shortly before they expire.
    """

    _EXPIRY_MARGIN_S = 300  # refresh tokens this many seconds before expiry

    def __init__(self, config: DataverseConfig):
        super().__init__(config)
        if config.client_secret is None:
            raise ValueError("TokenHandlerNoMsal requires client_secret to be configured")
        self._token: str | None = None
        self._token_expiry = datetime.datetime.now(datetime.timezone.utc)

    def _get_access_token(self) -> str:
        if (
            self._token is None
            or datetime.datetime.now(datetime.timezone.utc) >= self._token_expiry
        ):
            self._token, self._token_expiry = self._request_token()
        return self._token

    def _request_token(self) -> tuple[str, datetime.datetime]:
        """Request a new token from the Azure AD token endpoint.

        Returns:
            tuple[str, datetime.datetime]: The access token and its refresh deadline

        Raises:
            ValueError: If token acquisition fails
        """
        token_url = f"{self.config.authority}/oauth2/v2.0/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret.get_secret_value(),
            "scope": self.config.client_credentials_scope,
        }
        response = requests.post(token_url, data=payload, timeout=self.config.request_timeout_s)
        result = response.json()
        token = self._extract_token(result)
        expires_in = int(result.get("expires_in", 3600))
        token_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            seconds=max(expires_in - self._EXPIRY_MARGIN_S, 0)
        )
        return token, token_expiry


def get_token_handler(config: DataverseConfig, use_msal: bool | None = None) -> TokenHandler:
    """
    Create the appropriate token handler for the given config.

    A configured client_secret takes precedence (app-only flow);
    otherwise username/password (delegated user flow) is used.

    Args:
        config: Config object with credentials and URLs
        use_msal: Use MSAL-based handlers. When False, the client credentials
            flow calls the Azure AD token endpoint directly (TokenHandlerNoMsal).
            Defaults to config.use_msal.

    Returns:
        TokenHandler: Handler that can acquire access tokens

    Raises:
        ValueError: If no credentials are configured, or if use_msal is False
            without a client_secret
    """
    if use_msal is None:
        use_msal = config.use_msal
    if config.client_secret is not None:
        if use_msal:
            return ClientSecretTokenHandler(config)
        return TokenHandlerNoMsal(config)
    if config.username is not None and config.password is not None:
        if not use_msal:
            raise ValueError(
                "use_msal=False requires client_secret; "
                "username/password authentication is only supported via MSAL"
            )
        return UserPasswordTokenHandler(config)
    raise ValueError(
        "No credentials configured: provide either username and password, or client_secret"
    )
