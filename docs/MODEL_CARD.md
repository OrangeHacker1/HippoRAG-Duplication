# Model Card

> Required for any system that calls an LLM. The grading script checks for the
> four sections below by name. Each section needs substantive content; a one-line
> placeholder will not count.

## Intended Use

HippoRAG is intended for educational and research use as a graph-based retrieval-augmented generation system. It is designed to answer multi-hop factual questions over a small document corpus by combining a knowledge graph with Personalized PageRank retrieval and LLM-based answer generation.    

**Primary users:** Students and researchers exploring knowledge-graph-based RAG systems.    
**Intended deployment:** Local or university compute environments with an OpenAI-compatible LLM endpoint.   
**Supported tasks:** Multi-hop question answering over a user-provided document corpus.    

[Describe who should use the system, in what context, for what purpose. Be
specific. "Researchers querying a public NIST cybersecurity corpus to find
relevant standards" is good. "AI assistant" is not.]

## Limitations

- **Corpus size:** The system is designed for small corpora (tens to hundreds of documents). Performance degrades on large corpora due to quadratic embedding similarity computation during KG construction.   
- **LLM dependence:** Triple extraction quality depends entirely on the configured LLM. Weak or poorly-instructed models produce noisy triples, which degrade retrieval.    
- **Evaluation dataset:** The bundled evaluation dataset contains 4 questions over 10 documents. This is sufficient for functional testing but insufficient for robust performance measurement.   
- **No coreference resolution:** The system treats entity strings as exact node identifiers. "Einstein" and "Albert Einstein" will be separate nodes unless linked by embedding similarity.   
- **English only:** The embedding model (`all-MiniLM-L6-v2`) and prompts are optimized for English text.   

[Document what the system does poorly or cannot do. Examples to consider:
the model's knowledge cutoff date; languages other than English; queries
outside the indexed corpus; questions requiring real-time data; long
multi-hop reasoning; numerical computation; etc.]

## Risks

- **LLM prompt injection:** Triple extraction and filtering pass raw document text to the LLM. Adversarially crafted documents could attempt to hijack the extraction prompt.
- **Pickle deserialization:** The knowledge graph is stored as a Python pickle file (`kg/graph.pkl`). Loading a pickle from an untrusted source is a code execution risk. Only load graphs from trusted origins.
- **API key exposure:** The LLM API key is loaded from `.env`. Ensure `.env` is never committed to version control (enforced by `.gitignore`).
- **Hallucination:** The LLM may generate answers not grounded in the retrieved passages. Retrieved passages are shown alongside the answer to allow user verification.

[Document risks and mitigations. Required topics:
- Hallucination: how the system mitigates fabricated citations
- Prompt injection: how user input is bounded before being passed to the LLM
- Bias: known biases in the model or corpus that could skew outputs
- Privacy: what user input is logged and for how long
- Cost: rate limiting and per-request budget controls]

## Out of Scope

- **Production deployment:** This system has no authentication, rate limiting, or input sanitization beyond empty-query rejection. It is not suitable for public-facing production use.
- **Large-scale retrieval:** The system is not designed to compete with production RAG systems on large corpora or low-latency requirements.
- **Real-time corpus updates:** The knowledge graph is built offline. Incremental document updates require a full rebuild.
- **Languages other than English:** Non-English documents may produce poor triple extraction and embedding similarity results.

[Document explicit non-goals. Examples: medical advice, legal advice,
real-time conversation, code execution, file uploads, multimedia, etc.
The system should refuse or redirect requests in these areas.]
