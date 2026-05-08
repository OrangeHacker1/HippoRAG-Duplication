# HippoRAG System Specification

## Purpose

HippoRAG is a graph-based retrieval-augmented generation (RAG) system inspired by the hippocampal memory indexing theory from neuroscience. Instead of flat vector search, the system builds a knowledge graph from a document corpus and uses it as an explicit memory index. At query time, seed concepts are identified from the query, and a Personalized PageRank (PPR) walk over the graph retrieves relevant passages across multiple hops in a single step. A large language model then generates a final answer from the retrieved passages.

The system is designed to answer multi-hop questions that require connecting facts scattered across separate documents — a task where flat vector search consistently underperforms graph-based retrieval.

---

## Component Inventory

| Component | Module Path | Responsibility |
|---|---|---|
| KG Builder | `kg/builder.py` | Orchestrates knowledge graph construction from raw documents |
| Knowledge Graph | `kg/graph_store.py` | NetworkX DiGraph storing entity nodes, passage nodes, and edges |
| Embedding Engine | `kg/embeddings.py` | Encodes text using sentence-transformers; computes cosine similarity |
| LLM Client | `llm/llm_client.py` | HTTP calls to OpenAI-compatible LLM for triple extraction and answer generation |
| Triple Matcher | `retrieval/triple_matcher.py` | Finds triples semantically similar to a query via embedding similarity |
| Triple Filter | `retrieval/filter.py` | Uses LLM to select only relevant triples from candidates |
| Query Processor | `retrieval/query_processor.py` | Extracts named entities from a query string using the LLM |
| PPR Engine | `retrieval/ppr.py` | Runs Personalized PageRank over the knowledge graph from seed nodes |
| Retriever | `retrieval/retriever.py` | Ties the full retrieval pipeline together; exposes `retrieve()` and `query()` |
| Eval Metrics | `eval/metrics.py` | Computes Recall@k, Exact Match, and F1 score |
| Eval Dataset | `data/eval_dataset.py` | Multi-hop test corpus, questions, gold documents, and gold answers |
| Config Loader | `config/config_loader.py` | Loads `config/config.yaml` |
| Env Loader | `config/env_loader.py` | Loads `.env` file; validates required environment variables |
| API Server | `api/app.py` | FastAPI application exposing `/query` and `/health` endpoints |
| KG Build Script | `run_build_kg.py` | CLI entry point for building the knowledge graph |
| Query Script | `run_query.py` | CLI entry point for a single query |
| Eval Script | `run_eval.py` | CLI entry point for the full evaluation pipeline |

---

## Data Flow

### Indexing (Knowledge Graph Construction)

```
Raw documents (List[str])
    │
    ▼
LLMClient.extract_triples(doc)
    │  Prompt: extract JSON array of [subject, relation, object] triples
    ▼
KnowledgeGraph.add_triple(s, r, o, source_text)
    │  Adds entity nodes (type="entity")
    │  Adds passage node (type="passage", text=source_text)
    │  Adds directed edge s → o (relation=r)
    │  Adds edges s → passage, o → passage (relation="contains")
    ▼
EmbeddingEngine.encode(all_entity_node_names)
    │
    ▼
Pairwise cosine similarity → add undirected "similar" edges
    where similarity > config["kg"]["similarity_threshold"] (default 0.75)
    │
    ▼
KnowledgeGraph.save(path)  →  kg/graph.pkl
```

### Retrieval and Answer Generation

```
Query string
    │
    ├──► TripleMatcher.match(query)
    │        Embeds query; scores all stored triples by cosine similarity
    │        Returns top-K triples
    │
    ├──► TripleFilter.filter(query, triples)
    │        LLM selects relevant triple indices from numbered list
    │        Returns filtered subset
    │
    ├──► [triple subjects]  ──┐
    │                         ├──► seeds (union)
    ├──► QueryProcessor        │
    │    .extract_entities()  ─┤
    │    + _match_query_       │
    │      entities()         ─┘
    │        LLM extracts entity strings from query
    │        Embedding similarity maps them to graph nodes
    │
    ▼
run_ppr(graph, seeds, alpha, max_iter)
    │  NetworkX personalized_pagerank
    │  Seeds receive weight=1, all others 0
    ▼
Ranked nodes sorted by PPR score (descending)
    │
    ▼
Filter for type="passage" nodes → extract .text attribute
    Top-K passages collected
    │
    ▼
LLMClient.generate(prompt with passages + question)
    │
    ▼
Answer string
```

---

## Public Interfaces

### `kg/builder.py` — `KGBuilder`

```python
class KGBuilder:
    def __init__(self) -> None: ...
    def build(self, docs: List[str]) -> None:
        """
        Extract triples from each document, build the knowledge graph,
        link similar entity nodes by embedding, and save to disk.

        Args:
            docs: List of raw document strings.
        """
```

### `kg/graph_store.py` — `KnowledgeGraph`

```python
class KnowledgeGraph:
    def __init__(self) -> None: ...
    def add_triple(self, s: str, r: str, o: str, source_text: str = None) -> None:
        """Add a (subject, relation, object) triple and link to its source passage."""
    def save(self, path: str) -> None:
        """Serialize graph and triples to a pickle file."""
    def load(self, path: str) -> None:
        """Deserialize graph and triples from a pickle file."""
```

### `retrieval/retriever.py` — `HippoRAG`

```python
class HippoRAG:
    def __init__(self) -> None:
        """Load graph from disk, initialize all retrieval components."""

    def retrieve(self, query: str) -> List[str]:
        """
        Run the full retrieval pipeline.

        Args:
            query: Natural language question string.

        Returns:
            Ordered list of passage strings ranked by PPR score.
            Length <= config["retrieval"]["top_k"].
        """

    def query(self, query: str) -> str:
        """
        Retrieve relevant passages and generate an answer using the LLM.

        Args:
            query: Natural language question string.

        Returns:
            Generated answer string.
        """
```

### `eval/metrics.py`

```python
def recall_at_k(retrieved_docs: List[str], gold_docs: List[str], k: int) -> float:
    """Fraction of gold documents found in the top-k retrieved documents."""

def exact_match(predicted: str, gold_answers: List[str]) -> float:
    """1.0 if any gold answer token set is a subset of the predicted answer tokens."""

def f1_score(predicted: str, gold_answers: List[str]) -> float:
    """Best token-level F1 score across all gold answers."""
```

### `api/app.py` — FastAPI endpoints

#### `GET /health`
Returns HTTP 200 with body:
```json
{"status": "ok"}
```

#### `GET /`
Returns HTTP 200 with an HTML page containing:
- A `<textarea>` or `<input>` for the question
- A Submit button
- A section for displaying the answer (id or label "Answer")
- A section for displaying retrieved passages (id or label "Retrieved Passages")

#### `GET /evaluate`
Returns HTTP 200 with an HTML page containing a "Run Evaluation" button that triggers `POST /api/evaluate`.

#### `POST /api/query`
Request body (JSON):
```json
{"question": "string"}
```

Success response HTTP 200:
```json
{
  "answer": "string",
  "passages": ["string", "..."],
  "request_id": "string"
}
```

Error — empty or whitespace-only question, HTTP 422:
```json
{"detail": "Query must not be empty."}
```

Error — LLM endpoint unreachable (`requests.exceptions.ConnectionError` or `ConnectTimeout`), HTTP 503:
```json
{"detail": "The language model is currently unavailable. Please try again later."}
```

Error — knowledge graph not loaded, HTTP 503:
```json
{"detail": "Knowledge graph not loaded. Run python run_build_kg.py first."}
```

#### `POST /api/evaluate`
No request body required.

Success response HTTP 200:
```json
{
  "aggregate": {
    "Recall@1": 0.0,
    "Recall@2": 0.0,
    "Recall@5": 0.0,
    "ExactMatch": 0.0,
    "F1": 0.0
  },
  "results": [
    {
      "question": "string",
      "answer": "string",
      "passages": ["string"],
      "em": 0.0,
      "f1": 0.0,
      "Recall@1": 0.0,
      "Recall@2": 0.0,
      "Recall@5": 0.0
    }
  ],
  "request_id": "string"
}
```

All aggregate metric values are floats in [0.0, 1.0]. The `results` list contains one entry per question in `data/eval_dataset.QUESTIONS`.

#### Logging
Every request to `POST /api/query` and `POST /api/evaluate` must:
1. Generate a UUID `request_id` at the start of the request
2. Emit a structured JSON log line on arrival: `{"timestamp": ..., "level": "INFO", "module": "app", "message": "Query received: <question>", "request_id": "<uuid>"}`
3. Emit a structured JSON log line on completion or error
4. Include `request_id` in the response body

---

## Model and Prompt Selection

### Embedding Model

- **Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Source:** HuggingFace Hub (downloaded automatically on first run)
- **Use:** Encoding entity nodes, triple texts, and query strings for cosine similarity
- **Config key:** `embedding.model` in `config/config.yaml`

### LLM

- **Default model:** Configurable via `TEACHER_MODEL` environment variable (e.g. `llama-3.3-70b-instruct-awq` or `gpt-4o-mini`)
- **Endpoint:** `TEACHER_BASE_URL` — any OpenAI-compatible `/v1/chat/completions` endpoint
- **Temperature:** `0.0` (deterministic output)
- **Max tokens:** `512`
- **Config keys:** `llm.temperature`, `llm.max_tokens` in `config/config.yaml`

### Prompts

| Prompt | Location | Purpose |
|---|---|---|
| Triple extraction | `llm/llm_client.py:extract_triples()` | Extract `[[s, r, o]]` JSON from a document |
| Triple filtering | `retrieval/filter.py:filter()` | Select relevant triple indices from a numbered list |
| Entity extraction | `retrieval/query_processor.py:extract_entities()` | Extract key entities from a query string |
| Answer generation | `retrieval/retriever.py:query()` | Generate an answer given retrieved passages and the question |

### PPR Parameters

- **Alpha (damping):** `0.85` — probability of following a graph edge vs. teleporting to a seed
- **Max iterations:** `30`
- **Similarity threshold for synonymy edges:** `0.75`
- **Config keys:** `retrieval.ppr_alpha`, `retrieval.max_iter`, `kg.similarity_threshold`

---

## Configuration

### `config/config.yaml` — full structure

```yaml
llm:
  temperature: 0.0
  max_tokens: 512
  retries: 3

kg:
  save_path: kg/graph.pkl
  similarity_threshold: 0.75
  max_passages: 1000

retrieval:
  top_k: 5
  ppr_alpha: 0.85
  max_iter: 30

embedding:
  model: sentence-transformers/all-MiniLM-L6-v2

logging:
  verbose: true
```

Loaded by `config/config_loader.py`:
```python
def load_config(path="config/config.yaml") -> dict:
    """Load and return the YAML config as a dict."""
```

### Environment Variables (`.env`)

Required variables loaded by `config/env_loader.py`:

| Variable | Description |
|---|---|
| `TEACHER_BASE_URL` | Base URL of the OpenAI-compatible LLM endpoint (e.g. `http://host/v1`) |
| `TEACHER_MODEL` | Model name served at the endpoint (e.g. `gpt-4o-mini`) |
| `TEACHER_API_KEY` | API key for the endpoint |

`env_loader.py` raises `ValueError` if any required variable is missing.

```python
def load_environment() -> dict:
    """
    Load .env and return dict with keys: teacher_base, teacher_model, teacher_key.
    Raises ValueError if any key is missing.
    """
```

### `data/eval_dataset.py` — structure

```python
CORPUS: List[str]  # raw document strings for building the KG

QUESTIONS: List[dict]  # each dict has:
# {
#   "question": str,
#   "gold_docs": List[str],    # exact corpus strings needed to answer
#   "gold_answers": List[str]  # acceptable answer strings
# }
```
