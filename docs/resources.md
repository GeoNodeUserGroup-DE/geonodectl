# Resources

Generic resource operations that apply across all GeoNode resource types (datasets, documents, maps, geoapps).

**Aliases:** `resources`, `resource`

---

## List

```bash
geonodectl resources list
geonodectl resources list --search "soil"
geonodectl resources list --ordering date_updated
```

---

## Delete

```bash
geonodectl resources delete 36
geonodectl resources delete 36,37,38
```

---

## metadata

Download ISO 19139 / Dublin Core / other metadata for a resource.

```bash
# Download in the default format
geonodectl resources metadata 36

# Download in a specific format
geonodectl resources metadata 36 --metadata-type ISO
```

The `--metadata-type` option accepts the formats supported by your GeoNode instance (e.g. `ISO`, `Dublin Core`).
