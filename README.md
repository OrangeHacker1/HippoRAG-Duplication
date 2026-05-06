# HippoRAG Duplication

## Usage

To install the dependencies, run:

        python -m pip install -r requirements.txt

To create the knowlage graph (KG), you will run:

        py run_build_kg.py

To run a prompt, you will run:

        py run_query.py



## Current Structure

                
        hipporag/
        │
        ├── config/
        │   ├── config.yaml
        │   ├── config_loader.py
        │   └── env_loader.py
        ├── kg/
        │   ├── builder.py
        │   ├── graph_store.py
        │   └── embeddings.py
        │
        ├── retrieval/
        │   ├── query_processor.py
        │   ├── triple_matcher.py
        │   ├── filter.py
        │   ├── ppr.py
        │   └── retriever.py
        │
        ├── llm/
        │   └── llm_client.py
        │
        ├── run_build_kg.py
        ├── run_query.py
        └── requirements.txt

## HippoRAG Qualities

| Component | HippoRAG Concept |
|-----------|------------------|
|Triples |	hippocampal encoding|
|Graph |	memory index |
|PPR |	associative recall |
|Query seeds |	cue-triggered recall |
|LLM |	neocortex reasoning |
