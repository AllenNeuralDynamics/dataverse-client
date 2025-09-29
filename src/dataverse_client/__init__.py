"""Init package"""

from importlib.metadata import version

__version__ = version("dataverse_client")

from .rest_client import DataverseConfig, DataverseRestClient


__all__ = ["DataverseConfig", "DataverseRestClient"]
