# Execution Requests

Inspect asynchronous execution requests in GeoNode (used internally for uploads, deletions, and other long-running operations).

**Aliases:** `executionrequest`, `execrequest`

---

## List

```bash
geonodectl executionrequest list
geonodectl executionrequest list --page-size 50
```

---

## Describe

```bash
geonodectl executionrequest describe <exec-id>
```

The `exec-id` is the UUID returned by operations that run asynchronously (e.g. dataset upload with `--wait`).

Useful for checking the status (`ready`, `running`, `failed`) and error messages of background jobs.
