from pprint import pprint

from dataverse_client import DataverseConfig, DataverseRestClient
from dataverse_models import models


def check_all_tables(client: DataverseRestClient):
    for table, model in models.TABLE_MODEL_MAP.items():
        raw_data = client.query(table, top=5)
        data = [model(**entry) for entry in raw_data]
        print(f"###########     Data for table {table}:      ###########")
        pprint(data[0] if len(data) else "No data")


def check_one_table(client: DataverseRestClient, table: str):
    raw_data = client.query(table, top=5)
    model = models.TABLE_MODEL_MAP[table]
    data = [model(**entry) for entry in raw_data]
    print(f"###########     Raw data for table {table}:      ###########")
    pprint(raw_data[0])
    print(f"###########     Model data for table {table}:      ###########")
    pprint(data[0].model_dump())


if __name__ == "__main__":
    client = DataverseRestClient(DataverseConfig())

    table = "aibs_fact_mouse_water_restrictions"
    check_one_table(client, table)
