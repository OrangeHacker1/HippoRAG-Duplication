# Logging

## Format

All log entries are structured JSON with the following fields:

| Field | Type | Description |
|---|---|---|
| `timestamp` | string | UTC time in ISO 8601 format |
| `level` | string | `INFO`, `WARNING`, `ERROR` |
| `module` | string | Python module that emitted the log |
| `message` | string | Human-readable description |
| `request_id` | string or null | UUID propagated through all components for a single request |

Example log line:
```json
{"timestamp": "2026-05-06T18:32:01Z", "level": "INFO", "module": "app", "message": "Query received: Who developed relativity?", "request_id": "f3a2c1d0-9e8b-4f7a-b6c5-2d1e0f9a8b7c"}
```

---

## Tracing a Request End-to-End

Every request to `POST /api/query` or `POST /api/evaluate` generates a UUID `request_id` that is attached to every log line produced during that request's lifecycle.

### Example: Trace a query request

**Step 1.** Start the system:
```bash
docker compose up
```

**Step 2.** Submit a query:
```bash
curl -s -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Who influenced physics through relativity?"}'
```

**Step 3.** Note the `request_id` in the response:
```json
{
  "answer": "Albert Einstein influenced physics through relativity.",
  "passages": ["Albert Einstein developed the theory of relativity.", "..."],
  "request_id": "f3a2c1d0-9e8b-4f7a-b6c5-2d1e0f9a8b7c"
}
```

**Step 4.** Search the logs for that request ID:
```bash
docker compose logs app | grep "f3a2c1d0-9e8b-4f7a-b6c5-2d1e0f9a8b7c"
```

**Expected log lines (in order):**

```json
{"timestamp": "2026-05-06T18:32:01Z", "level": "INFO", "module": "app", "message": "Query received: Who influenced physics through relativity?", "request_id": "f3a2c1d0-9e8b-4f7a-b6c5-2d1e0f9a8b7c"}
{"timestamp": "2026-05-06T18:32:03Z", "level": "INFO", "module": "app", "message": "Query answered successfully.", "request_id": "f3a2c1d0-9e8b-4f7a-b6c5-2d1e0f9a8b7c"}
```

Each line covers a stage of the pipeline:
1. **Input arrival** — query received and logged before processing
2. **Output delivery** — answer generated and response returned

### Error trace example

If the LLM is unreachable, the log shows:
```json
{"timestamp": "2026-05-06T18:35:10Z", "level": "ERROR", "module": "app", "message": "LLM connection timed out.", "request_id": "a1b2c3d4-..."}
```

---

## Implementation

The logger is in `api/logger.py`. Import it in any module with:
```python
from api.logger import get_logger
logger = get_logger(__name__)
```

Pass `request_id` via the `extra` dict:
```python
logger.info("My message", extra={"request_id": request_id})
```
