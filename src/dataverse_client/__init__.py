"""Init package"""

from importlib.metadata import version

__version__ = version("dataverse_client")

from .rest_client import DataverseConfig, DataverseRestClient, ColumnMetadata, TableMetadata


__all__ = [
    "DataverseConfig",
    "DataverseRestClient",
    "ColumnMetadata",
    "TableMetadata",
]
