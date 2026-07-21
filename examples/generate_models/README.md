Small utility to read dataverse table definitions and generate pydantic models to help interpret dataverse table reads.

1. Switch to this subdirectory
    - `cd examples/generate_models`
2. Install dataverse-client and codegen dependency:
    - `uv sync`
3. Run codegen:
    - `uv run generate-models`

4. `tables.json` and `models.py` will be created.

> [!NOTE]
> Run unit test with `uv run pytest`

The models are generated with the help of the `models.py.jinja2` template, and can capture the formatted values of lookup/picklist fields. They look something like this:


```python
class AibsFactMouseWaterRestriction(BaseModel):
    _table_name: ClassVar[str] = "aibs_fact_mouse_water_restrictions"
    _table_display_name: ClassVar[str] = "aibs_fact_mouse_water_restriction"
    aibs_active_record: Optional[bool] = None
    aibs_baseline_weight: Optional[float] = None
    aibs_behavior_training_record_guid: Optional[Any] = Field(
        None, alias="_aibs_behavior_training_record_value"
    )
    aibs_behavior_training_record_formatted: Optional[str] = Field(
        None, alias="_aibs_behavior_training_record_value@OData.Community.Display.V1.FormattedValue"
    )
    aibs_fact_mouse_water_restrictionid: str
    aibs_last_watered_datetime: Optional[datetime] = None
    aibs_low_weight_threshold: Optional[float] = None
    aibs_mouse_id_guid: Optional[Any] = Field(None, alias="_aibs_mouse_id_value")
    aibs_mouse_id_formatted: Optional[str] = Field(
        None, alias="_aibs_mouse_id_value@OData.Community.Display.V1.FormattedValue"
    )
    aibs_notes: Optional[str] = None
    aibs_operational_team_guid: Optional[Any] = Field(None, alias="_aibs_operational_team_value")
    aibs_operational_team_formatted: Optional[str] = Field(
        None, alias="_aibs_operational_team_value@OData.Community.Display.V1.FormattedValue"
    )
    aibs_record_name: Optional[str] = None
    aibs_target_weight: Optional[float] = None
    aibs_targeted_weight_percentage: Optional[float] = None
    aibs_water_restriction_status: Optional[int] = None
    aibs_water_restriction_status_formatted: Optional[str] = Field(
        None, alias="aibs_water_restriction_status@OData.Community.Display.V1.FormattedValue"
    )
    aibs_watered_today: Optional[bool] = None
    aibs_watering_shift: Optional[int] = None
    aibs_watering_shift_formatted: Optional[str] = Field(
        None, alias="aibs_watering_shift@OData.Community.Display.V1.FormattedValue"
    )

```

When used to deserialize a dataverse record (see example in example_use_models.py), you get something like the following:

```python
AibsFactMouseWaterRestriction(
    aibs_active_record=False,
    aibs_baseline_weight=27.07,
    aibs_behavior_training_record_guid='118e7fc6-9a28-f111-8341-000d3a4ded72',
    aibs_behavior_training_record_formatted='793289_2025-06-20T21:07:25.008236',
    aibs_fact_mouse_water_restrictionid='85518479-e92e-f111-88b4-000d3a4ded72',
    aibs_last_watered_datetime=None,
    aibs_low_weight_threshold=19.51,
    aibs_mouse_id_guid='6a35228c-8d28-f111-8342-6045bdd3c87e',
    aibs_mouse_id_formatted='793289',
    aibs_notes=None,
    aibs_operational_team_guid='3ac065fa-092e-f111-88b4-7c1e521c04a0',
    aibs_operational_team_formatted='Behavior Training',
    aibs_record_name='793289_2025-06-20T21:07:25.008236',
    aibs_target_weight=23.01,
    aibs_targeted_weight_percentage=0.85,
    aibs_water_restriction_status=252080003,
    aibs_water_restriction_status_formatted='adlib: water restriction complete',
    aibs_watered_today=False,
    aibs_watering_shift=None,
    aibs_watering_shift_formatted=None,
)
```