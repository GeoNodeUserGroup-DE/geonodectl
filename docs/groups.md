# Groups

Manage GeoNode user groups.

---

## List

```bash
geonodectl groups list
geonodectl groups list --search "editors"
```

---

## Describe

```bash
geonodectl groups describe 3
```

---

## Create

```bash
geonodectl groups create --title "Data Editors" --set '{"description": "Can edit datasets"}'
geonodectl groups create --json_path ./group.json
```

---

## Patch

```bash
geonodectl groups patch 3 --set '{"description": "Updated description"}'
geonodectl groups patch 3 --json_path ./group_patch.json
```

---

## Delete

```bash
geonodectl groups delete 3
geonodectl groups delete 3,4,5
```
