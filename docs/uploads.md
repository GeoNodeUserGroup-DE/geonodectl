# Uploads

Inspect upload jobs in GeoNode.

> Uploads are created implicitly when you use `dataset upload`. Use these commands to check the status of in-progress or past uploads. `documents upload` is synchronous and does not create an upload job.

---

## List

```bash
geonodectl uploads list
geonodectl uploads list --page 2 --page-size 20
```

---

## Describe

```bash
geonodectl uploads describe 12
```

Returns full metadata for the upload including its state, error message (if any), and linked resource.
