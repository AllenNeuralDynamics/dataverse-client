from datetime import datetime
from pathlib import Path
import subprocess
from typing import Optional

from pydantic import BaseModel
import jinja2

from dataverse_client import DataverseConfig, DataverseRestClient, TableMetadata

# Mapping of Odata (EDM) types to Python types
simple_types = {
    "Boolean": bool,
    "String": str,
    "Memo": str,
    "DateTime": datetime,
    "Decimal": float,
    "Integer": int,
    "Double": float,
    "BigInt": int,
    # "Virtual": str,  # virtuals aren't actual columns, they're calculated
}


### Models to parametrize our code generation
class AttributeModel(BaseModel):
    """Model to represent an attribute of a Pydantic model for code generation"""

    name: str
    type_hint: str
    value: Optional[str] = None

    def to_code(self):
        if self.value is None:
            return f"{self.name}: {self.type_hint}"
        else:
            return f"{self.name}: {self.type_hint} = {self.value}"


class ModelModel(BaseModel):
    """Model to represent a Pydantic model for code generation"""

    name: str
    parent_class: str = "BaseModel"
    docstring: Optional[str] = None
    attributes: list[AttributeModel] = []


def make_model_from_table_metadata(table_metadata: TableMetadata) -> ModelModel:
    """Turn OData table metadata into a ModelModel that can be used to generate a Pydantic model for that table.

    Handles simple types, UniqueIdentifiers, lookups and picklists.
    For lookups and picklists, add additional fields to capture the formatted values as well as the ids.
    """
    # Make CapWords class name from SchemaName, e.g. "aibs_dim_mices" -> "AibsDimMices"
    model_name = "".join(word.capitalize() for word in table_metadata.SchemaName.split("_"))

    model = ModelModel(
        name=model_name,
        attributes=[
            AttributeModel(
                name="_table_name",
                type_hint="ClassVar[str]",
                value=f'"{table_metadata.LogicalCollectionName}"',
            ),
            AttributeModel(
                name="_table_display_name",
                type_hint="ClassVar[str]",
                value=f'"{table_metadata.SchemaName}"',
            ),
        ],
    )

    lookup_fields = []
    for col in table_metadata.Attributes:
        if col.AttributeType in simple_types:
            model.attributes.append(
                AttributeModel(
                    name=col.LogicalName,
                    type_hint=f"Optional[{simple_types[col.AttributeType].__name__}]",
                    value="None",
                )
            )
        elif col.AttributeType == "Uniqueidentifier":
            model.attributes.append(
                AttributeModel(
                    name=col.LogicalName,
                    type_hint="str",  # consider changing to "Optional[str]" to use the models for create requests (before GUID is set)
                )
            )
        elif col.AttributeType == "Lookup":
            # lookup fields have the following weirdnesses:
            # For a field named "example_field":
            #   The table metadata contains attributes like:
            #     - example_field (type: Lookup)
            #     - example_fieldname (type: String) - shadow field
            #   When you query the table, the API returns:
            #     - _example_field_value: "<GUID value as string>"
            #     - _example_field_value@OData.Community.Display.V1.FormattedValue: "<Formatted value>"

            # So the plan is, ignore the shadow field, and have the following in the model:
            # - example_field_guid: Optional[str] = Field(None, alias="_example_field_value")
            # - example_field_formatted: Optional[str] = Field(None, alias="_example_field_value@OData.Community.Display.V1.FormattedValue")

            # Keep track of lookup fields so we can remove the shadow field later
            lookup_fields.append(col.LogicalName)
            fieldname = f"_{col.LogicalName}_value"
            formatted_field_name = (
                f"_{col.LogicalName}_value@OData.Community.Display.V1.FormattedValue"
            )

            model.attributes.append(
                AttributeModel(
                    name=f"{col.LogicalName}_guid",
                    type_hint="Optional[Any]",
                    value=f"Field(None, alias='{fieldname}')",
                )
            )
            model.attributes.append(
                AttributeModel(
                    name=f"{col.LogicalName}_formatted",
                    type_hint="Optional[str]",
                    value=f"Field(None, alias='{formatted_field_name}')",
                ),
            )
        elif col.AttributeType == "Picklist":
            # Picklists have the following weirdnesses:
            # For a field named "example_picklist":
            #   The table metadata contains attributes like:
            #     - example_picklist (type: Picklist)
            #     - example_picklistname (type: Virtual) - shadow field
            #   When you query the table, the API returns:
            #     - example_picklist: <picklist enum value int>
            #     - example_picklist@OData.Community.Display.V1.FormattedValue: "<Formatted value>"

            # So the plan is, ignore the virtual field, and have the following in the model:
            # - example_picklist: Optional[int] = Field(None, alias="_example_picklist_value")
            # - example_picklist_formatted: Optional[str] = Field(None, alias="_example_picklist_value@OData.Community.Display.V1.FormattedValue")

            formatted_field_name = f"{col.LogicalName}@OData.Community.Display.V1.FormattedValue"
            model.attributes.append(
                AttributeModel(
                    name=col.LogicalName,
                    type_hint="Optional[int]",
                    value="None",
                )
            )
            model.attributes.append(
                AttributeModel(
                    name=f"{col.LogicalName}_formatted",
                    type_hint="Optional[str]",
                    value=f"Field(None, alias='{formatted_field_name}')",
                ),
            )
        elif col.AttributeType == "Virtual":
            # Ignore redundant legacy virtual fields that accompany picklists
            pass
        else:
            print(f"Unfamiliar attribute type {col.AttributeType} for column {col.LogicalName}")

    # Remove redundant legacy "shadow" fields that accompany lookups
    for field in lookup_fields:
        shadow_field = f"{field}name"
        try:
            idx = [i for i, attr in enumerate(model.attributes) if attr.name == shadow_field][0]
            model.attributes.pop(idx)
        except IndexError:
            pass

    return model


def codegen_models_from_tables(tables: list[TableMetadata], template_path: Path, output_file: Path):
    models = {
        table.LogicalCollectionName: make_model_from_table_metadata(table) for table in tables
    }
    template = template_path.read_text()
    content = jinja2.Template(template).render(models=models)

    output_file.write_text(content)
    subprocess.run(["uvx", "ruff", "format", str(output_file)], check=True)


def main_generate_models():
    models_dir = Path(__file__).parent
    client = DataverseRestClient(DataverseConfig())
    tables = client.list_table_info(
        table_filter_prefix="aibs_",
        column_filter_prefix="aibs_",
        output_file=models_dir / "tables.json",
    )
    codegen_models_from_tables(
        tables,
        template_path=models_dir / "models.py.jinja2",
        output_file=models_dir / "models.py",
    )


if __name__ == "__main__":
    main_generate_models()
