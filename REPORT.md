
# Current Structure

        hipporag_rebuild/
        │
        ├── data/
        │   └── documents/
        │
        ├── kg/
        │   ├── builder.py
        │   ├── graph_store.py
        │   └── extractor.py
        │
        ├── retrieval/
        │   ├── query_processor.py
        │   ├── ppr.py
        │   └── retriever.py
        │
        ├── llm/
        │   └── llm_client.py
        │
        ├── run_build_kg.py
        ├── run_query.py
        └── requirements.txt

# HippoRAG Qualities

| Component | HippoRAG Concept |
|-----------|------------------|
|Triples |	hippocampal encoding|
|Graph |	memory index |
|PPR |	associative recall |
|Query seeds |	cue-triggered recall |
|LLM |	neocortex reasoning |

