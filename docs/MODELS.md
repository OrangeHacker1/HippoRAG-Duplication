# Model Documentation

## Embedding Model

| Field | Value |
|---|---|
| Model ID | `sentence-transformers/all-MiniLM-L6-v2` |
| Source | HuggingFace Hub |
| Version | via `sentence-transformers==3.0.1` |
| License | Apache 2.0 |
| Size | ~90 MB |
| Downloaded automatically | Yes — on first run via `SentenceTransformer()` |

### Use

Used to encode entity node names, triple texts, and query strings for cosine similarity matching. Downloaded automatically to `~/.cache/huggingface/` on first run.

To pre-download: `make download-models`

---

## Language Model (LLM)

| Field | Value |
|---|---|
| Model ID | Configurable via `TEACHER_MODEL` in `.env` |
| Endpoint | Configurable via `TEACHER_BASE_URL` in `.env` |
| Protocol | OpenAI-compatible `/v1/chat/completions` |
| Default | `llama-3.3-70b-instruct-awq` on local GPUStack |
| License | Depends on configured model |

### Use

Used for three tasks:
1. **Triple extraction** — extract `[[subject, relation, object]]` JSON from documents
2. **Triple filtering** — select relevant triples for a query
3. **Entity extraction** — extract named entities from a query string
4. **Answer generation** — generate a natural language answer from retrieved passages

### Configuration

Set the following in `.env` (see `.env.example`):
```
TEACHER_BASE_URL=http://<host>/v1
TEACHER_MODEL=<model-name>
TEACHER_API_KEY=<api-key>
```
