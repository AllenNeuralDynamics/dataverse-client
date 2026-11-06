"""Init package"""

from importlib.metadata import version

__version__ = version("dataverse_client")

from .auth_utils import (
    ClientSecretTokenHandler,
    TokenHandler,
    TokenHandlerNoMsal,
    UserPasswordTokenHandler,
    get_token_handler,
)
from .config import DataverseConfig
from .rest_client import ColumnMetadata, DataverseRestClient, TableMetadata

__all__ = [
    "ClientSecretTokenHandler",
    "ColumnMetadata",
    "DataverseConfig",
    "DataverseRestClient",
    "TableMetadata",
    "TokenHandler",
    "TokenHandlerNoMsal",
    "UserPasswordTokenHandler",
    "get_token_handler",
]
