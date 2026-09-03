# Linked Resources

Manage relationships between GeoNode resources (e.g. link a document to a dataset).

**Aliases:** `linked-resources`, `linkedresources`

---

## Describe

List all resources linked to a given resource.

```bash
geonodectl linked-resources describe 36
```

---

## Add

Link one or more resources to a target resource.

```bash
# Link resources 10 and 11 to resource 36
geonodectl linked-resources add 36 --linked-to 10 11
```

| Argument | Description |
|---|---|
| `pk` (positional) | PK of the resource to link from |
| `--linked-to PK …` | Space-separated PKs of resources to link to (required) |

---

## Delete

Remove one or more linked-resource relationships.

```bash
# Unlink resources 10 and 11 from resource 36
geonodectl linked-resources delete 36 --linked-to 10 11
```
