"""Examples for using the Dataverse client"""

import logging
from random import randint

from dataverse_client import DataverseConfig, DataverseRestClient

logging.basicConfig(level=logging.INFO)


def example_using_dataverse_client():
    """Example usage of the DataverseRestClient with mice table"""
    client = DataverseRestClient()

    mouse_table = "crb81_dim_mice_bases"

    # Add mouse (fails if mouse already exists)
    # mouse = client.add_entry(mouse_table, {"crb81_mouse_id": "614175"})
    # print(mouse)
    mouse_id = "614174"
    mouse_guid = "fe057d74-8683-f011-b4cb-6045bd03524b"
    mouse = client.get_entry(mouse_table, {"crb81_mouse_id": mouse_id})
    print(mouse)
    mouse = client.get_entry(mouse_table, mouse_guid)
    print(mouse)

    mice = client.query(
        mouse_table,
        filter="crb81_mouse_id ne '614174'",
        order_by="crb81_mouse_id",
        top=5,
        select=["crb81_mouse_id", "crb81_date_of_birth"],
    )
    print(mice)

    updated_mouse = client.update_entry(
        mouse_table,
        {"crb81_mouse_id": mouse_id},
        {"crb81_full_genotype": "UpdatedGenotype_" + str(randint(1, 100))},
    )
    print(updated_mouse)


if __name__ == "__main__":
    print("Loading configuration from " + str(DataverseConfig.model_config["yaml_file"]))
    example_using_dataverse_client()
