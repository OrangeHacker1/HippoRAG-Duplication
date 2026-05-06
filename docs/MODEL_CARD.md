# Model Card — HippoRAG

## Intended Use

HippoRAG is intended for educational and research use as a graph-based retrieval-augmented generation system. It is designed to answer multi-hop factual questions over a small document corpus by combining a knowledge graph with Personalized PageRank retrieval and LLM-based answer generation.

**Primary users:** Students and researchers exploring knowledge-graph-based RAG systems.
**Intended deployment:** Local or university compute environments with an OpenAI-compatible LLM endpoint.
**Supported tasks:** Multi-hop question answering over a user-provided document corpus.

---

## Limitations

- **Corpus size:** The system is designed for small corpora (tens to hundreds of documents). Performance degrades on large corpora due to quadratic embedding similarity computation during KG construction.
- **LLM dependence:** Triple extraction quality depends entirely on the configured LLM. Weak or poorly-instructed models produce noisy triples, which degrade retrieval.
- **Evaluation dataset:** The bundled evaluation dataset contains 4 questions over 10 documents. This is sufficient for functional testing but insufficient for robust performance measurement.
- **No coreference resolution:** The system treats entity strings as exact node identifiers. "Einstein" and "Albert Einstein" will be separate nodes unless linked by embedding similarity.
- **English only:** The embedding model (`all-MiniLM-L6-v2`) and prompts are optimized for English text.

---

## Risks

- **LLM prompt injection:** Triple extraction and filtering pass raw document text to the LLM. Adversarially crafted documents could attempt to hijack the extraction prompt.
- **Pickle deserialization:** The knowledge graph is stored as a Python pickle file (`kg/graph.pkl`). Loading a pickle from an untrusted source is a code execution risk. Only load graphs from trusted origins.
- **API key exposure:** The LLM API key is loaded from `.env`. Ensure `.env` is never committed to version control (enforced by `.gitignore`).
- **Hallucination:** The LLM may generate answers not grounded in the retrieved passages. Retrieved passages are shown alongside the answer to allow user verification.

---

## Out of Scope

- **Production deployment:** This system has no authentication, rate limiting, or input sanitization beyond empty-query rejection. It is not suitable for public-facing production use.
- **Large-scale retrieval:** The system is not designed to compete with production RAG systems on large corpora or low-latency requirements.
- **Real-time corpus updates:** The knowledge graph is built offline. Incremental document updates require a full rebuild.
- **Languages other than English:** Non-English documents may produce poor triple extraction and embedding similarity results.
