# HippoRAG Implementation Cross-Reference

## Project Requirements vs. Current State

### 1. Knowledge Graph Construction from Raw Text

| What's needed | Skeleton status | Official repo reference |
|---|---|---|
| Extract triples (subject, relation, object) from docs | Done — but `eval()` parsing is fragile | `openie_openai.py` — uses JSON-format prompts, structured parsing |
| NER before triple extraction | Missing — skeleton skips NER entirely | Two-step: NER first → triples conditioned on entities |
| Embed entity nodes | Done | `embedding_store.py` — parquet-backed |
| Link similar nodes via embedding similarity | Done | Synonymy edges with KNN + threshold |
| Store passage nodes linked to entities | Done | Same pattern |

---

### 2. Concept Extraction from Queries (Seed Identification)

| What's needed | Skeleton status | Official repo reference |
|---|---|---|
| Extract key entities from query | `query_processor.py` exists but never called | Extracts entities from top-K matched facts |
| Use those entities as PPR seeds | Not wired in — seeds come from triple subjects only | `entity_embedding_store` used to find seed nodes |

---

### 3. Graph-Based Passage Retrieval via PPR

| What's needed | Skeleton status | Official repo reference |
|---|---|---|
| Personalized PageRank from seeds | Done — NetworkX | Uses `igraph` with `damping=0.5` |
| Weight seeds by query relevance score | Missing — seeds all get weight=1 | `phrase_weights = avg_fact_score / occurrences` |
| Retrieve passage *text* from top nodes | Missing — returns raw node names | Filters for passage-type nodes, returns `.text` attribute |

---

### 4. Final Answer Generation

| What's needed | Skeleton status | Official repo reference |
|---|---|---|
| LLM generates answer from retrieved context | Done — but context is node names, not passage text | `rag_qa_musique.py` prompt template |

---

### 5. Evaluation on Multi-Hop Questions

| What's needed | Skeleton status | Official repo reference |
|---|---|---|
| Test questions requiring multi-hop reasoning | Entirely missing | HotpotQA, MuSiQue, 2WikiMultiHopQA datasets |
| Recall@k metric | Missing | `retrieval_eval.py` |
| Exact Match / F1 score | Missing | `qa_eval.py` |

---

## Prioritized TODO List

- [x] Gap 1 — Fix `retrieval/filter.py` stub — LLM now parses and returns relevant triple indices
- [ ] Gap 2 — Wire `query_processor.py` into `retriever.py` to extract seeds from the query
- [ ] Gap 3 — Fix `llm/llm_client.py` — replace `eval()` with JSON-format prompt and structured parsing
- [ ] Gap 4 — Fix context in `retrieval/retriever.py` — pull actual passage text from graph nodes instead of node names
- [ ] Gap 5 — Add evaluation
  - [ ] Gap 5a — Build a multi-hop test corpus (documents with facts intentionally scattered across separate docs)
  - [ ] Gap 5b — Write test questions with gold answers that require connecting facts from 2+ documents
  - [ ] Gap 5c — Implement Recall@k metric — did the right passages get retrieved? (reference: `Official-HippoRAG-Repo/src/hipporag/evaluation/retrieval_eval.py`)
  - [ ] Gap 5d — Implement Exact Match and F1 score metrics (reference: `Official-HippoRAG-Repo/src/hipporag/evaluation/qa_eval.py`)
  - [ ] Gap 5e — Write an evaluation runner script that feeds all questions through the pipeline and computes aggregate scores

> NER before triple extraction is the one thing from the official repo that the skeleton intentionally simplifies — add later if needed.
