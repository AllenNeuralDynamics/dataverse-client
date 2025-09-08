"""Examples for using the Dataverse client"""

from random import randint

from dataverse_client import DataverseConfig, DataverseRestClient


def example_using_dataverse_client():
    """Example usage of the DataverseRestClient with mice table"""
    config = DataverseConfig()
    client = DataverseRestClient(config)

    mouse_table = "crb81_dim_mice_bases"
    mouse_id = "614174"
    mouse_guid = "fe057d74-8683-f011-b4cb-6045bd03524b"
    mouse = client.get_entry(mouse_table, {"crb81_mouse_id": mouse_id})
    print(mouse)
    mouse = client.get_entry(mouse_table, mouse_guid)
    print(mouse)

    updated_mouse = client.update_entry(
        mouse_table,
        {"crb81_mouse_id": mouse_id},
        {"crb81_full_genotype": "UpdatedGenotype_" + str(randint(1, 100))},
    )
    print(updated_mouse)


if __name__ == "__main__":
    print(f'Loading configuration from {DataverseConfig.model_config["yaml_file"]}')
    example_using_dataverse_client()
