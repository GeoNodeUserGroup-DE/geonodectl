# Attributes

Inspect and update dataset attribute (field) metadata.

**Aliases:** `attributes`, `attr`, `attribute`

Attributes represent the columns of a vector dataset. Metadata such as labels, descriptions, and display settings can be managed here without re-uploading the dataset.

---

## Describe

List all attributes for a dataset.

```bash
# Tabular output
geonodectl attributes describe 36

# Full JSON (includes all fields, useful before patching)
geonodectl --raw attributes describe 36
```

Example JSON output (`--raw`):

```json
{
  "attributes": [
    {
      "pk": 101,
      "attribute": "site_id",
      "attribute_label": "site_id",
      "description": "",
      "attribute_type": "xsd:string",
      "visible": true,
      "display_order": 0
    },
    {
      "pk": 102,
      "attribute": "soil_type",
      "attribute_label": "soil_type",
      "description": "",
      "attribute_type": "xsd:string",
      "visible": true,
      "display_order": 1
    },
    {
      "pk": 103,
      "attribute": "ph_value",
      "attribute_label": "ph_value",
      "description": "",
      "attribute_type": "xsd:double",
      "visible": true,
      "display_order": 2
    },
    {
      "pk": 104,
      "attribute": "organic_matter",
      "attribute_label": "organic_matter",
      "description": "",
      "attribute_type": "xsd:double",
      "visible": true,
      "display_order": 3
    },
    {
      "pk": 105,
      "attribute": "geometry",
      "attribute_label": "geometry",
      "description": "",
      "attribute_type": "gml:PointPropertyType",
      "visible": false,
      "display_order": 4
    }
  ]
}
```

---

## Patch

Update metadata for dataset attributes. Use `attribute_set` in your JSON with the full list of attributes you want to update.

```bash
# Patch using an inline JSON string
geonodectl attributes patch 36 \
  --set '{"attribute_set": [{"pk": 102, "attribute_label": "Soil Type", "description": "FAO soil classification"}]}'

# Patch using a JSON file (recommended for larger updates)
geonodectl attributes patch 36 --json_path ./attributes.json
```

### Example patch file (`attributes.json`)

Include only the fields you want to change alongside the `pk` to identify each attribute:

```json
{
  "attribute_set": [
    {
      "pk": 101,
      "attribute_label": "Site ID",
      "description": "Unique identifier for the sampling site",
      "display_order": 0,
      "visible": true
    },
    {
      "pk": 102,
      "attribute_label": "Soil Type",
      "description": "FAO soil classification",
      "display_order": 1,
      "visible": true
    },
    {
      "pk": 103,
      "attribute_label": "pH Value",
      "description": "Soil pH measured in CaCl₂ solution",
      "display_order": 2,
      "visible": true
    },
    {
      "pk": 104,
      "attribute_label": "Organic Matter (%)",
      "description": "Organic matter content as percentage of dry weight",
      "display_order": 3,
      "visible": true
    },
    {
      "pk": 105,
      "attribute_label": "geometry",
      "description": "",
      "display_order": 4,
      "visible": false
    }
  ]
}
```

Use `geonodectl --raw attributes describe 36` first to get the current `pk` values before patching.
