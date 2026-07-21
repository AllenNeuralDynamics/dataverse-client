import logging

from dataverse_client import DataverseConfig, DataverseRestClient
from dataverse_client.odata_filters import equal, logical_and, less_than

logging.basicConfig(level=logging.INFO)


def example_filters():
    client = DataverseRestClient(DataverseConfig())

    mouse = client.query(
        "aibs_dim_mices",
        filter=logical_and(
            equal("aibs_mouse_id", "614177"),
            less_than("aibs_date_of_birth", "2020-01-01"),
        ),
    )
    print(mouse)


if __name__ == "__main__":
    example_filters()
