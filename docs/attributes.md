# Attributes

Inspect and update dataset attribute (field) metadata.

**Aliases:** `attributes`, `attr`, `attribute`

Attributes represent the columns of a vector dataset. Metadata such as labels, descriptions, and display settings can be managed here without re-uploading the dataset.

---

## Describe

List all attributes for a dataset.

```bash
# Describe attributes of dataset pk=36
geonodectl attributes describe 36
```

Returns a table of attribute names, types, labels, and visibility settings.

---

## Patch

Update metadata for dataset attributes.

```bash
# Patch using an inline JSON string
geonodectl attributes patch 36 --set '{"attribute_set": [{"attribute": "name", "label": "Name"}]}'

# Patch using a JSON file
geonodectl attributes patch 36 --json_path ./attributes.json
```

A typical use case is updating human-readable labels or toggling attribute visibility for the feature info popup.
