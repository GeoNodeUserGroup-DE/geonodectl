# Users

Manage GeoNode users.

**Aliases:** `users`, `user`

---

## List

```bash
geonodectl users list
geonodectl users list --search "alice"
geonodectl users list --filter is_staff=true
geonodectl users list --ordering pk
```

---

## Describe

```bash
# Show user details
geonodectl users describe 5

# Show groups the user belongs to
geonodectl users describe 5 --groups

# Show resources owned by the user
geonodectl users describe 5 --resources
```

---

## Create

```bash
# Create with explicit fields
geonodectl users create \
  --username alice \
  --email alice@example.com \
  --first_name Alice \
  --last_name Smith

# Create a superuser
geonodectl users create --username alice --is_superuser

# Create from a JSON file
geonodectl users create --json_path ./user.json
```

---

## Patch

```bash
geonodectl users patch 5 --set '{"email": "new@example.com"}'
geonodectl users patch 5 --json_path ./user_patch.json
```

---

## Delete

```bash
geonodectl users delete 5
geonodectl users delete 5,6,7
```

---

## transfer_resources

Transfer all resources owned by one user to another.

```bash
# Transfer all resources from user 5 to user 8
geonodectl users transfer_resources 5 --new_owner 8

# Transfer specific resources (by pk)
geonodectl users transfer_resources 5 --new_owner 8 --resources 36 42 55
```

| Argument | Description |
|---|---|
| `pk` (positional) | PK of the user currently owning the resources |
| `--new_owner PK` | PK of the user to receive the resources (required) |
| `--resources PK …` | Space-separated PKs of specific resources to transfer (optional; transfers all if omitted) |
