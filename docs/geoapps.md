# GeoApps

Manage GeoNode GeoApps (MapStore applications).

**Aliases:** `geoapps`, `apps`

---

## List

```bash
geonodectl geoapps list
geonodectl geoapps list --search "dashboard"
geonodectl geoapps list --filter owner.username=admin
geonodectl geoapps list --ordering title
```

---

## Describe

```bash
geonodectl geoapps describe 7
```

---

## Patch

```bash
geonodectl geoapps patch 7 --set '{"title": "Updated App"}'
geonodectl geoapps patch 7 --json_path ./geoapp_patch.json
```

---

## Delete

```bash
geonodectl geoapps delete 7
geonodectl geoapps delete 7,8,9
```
