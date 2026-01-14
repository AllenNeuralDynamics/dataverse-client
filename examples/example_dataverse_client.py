"""Examples for using the Dataverse client"""

import logging
from random import randint

from dataverse_client import DataverseConfig, DataverseRestClient

logging.basicConfig(level=logging.INFO)


def example_using_dataverse_client():
    """Example usage of the DataverseRestClient with mice table"""
    client = DataverseRestClient(DataverseConfig())

    mouse_table = "aibs_dim_mices"

    mouse = client.get_entry(mouse_table, {"aibs_mouse_id": "TestMouse_111111"})

    # Add mouse (fails if mouse already exists)
    try:
        mouse = client.add_entry(mouse_table, {"aibs_mouse_id": "614174"})
        print(mouse)
    except Exception as e:
        print(f"Failed to add mouse: {e}")
    mouse_id = "614174"
    mouse = client.get_entry(mouse_table, {"aibs_mouse_id": mouse_id})
    print(mouse)
    mouse_guid = mouse["aibs_dim_miceid"]
    mouse = client.get_entry(mouse_table, mouse_guid)
    print(mouse)

    mice = client.query(
        mouse_table,
        filter="aibs_mouse_id ne '614174'",
        order_by="aibs_mouse_id",
        top=5,
        select=["aibs_mouse_id", "aibs_date_of_birth"],
    )
    print(mice)

    updated_mouse = client.update_entry(
        mouse_table,
        {"aibs_mouse_id": mouse_id},
        {"aibs_genotype": "UpdatedGenotype_" + str(randint(1, 100))},
    )
    print(updated_mouse)


if __name__ == "__main__":
    print("Loading configuration from " + str(DataverseConfig.model_config["yaml_file"]))
    example_using_dataverse_client()
