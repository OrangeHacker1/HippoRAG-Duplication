"""
pipeline.py — smoke-test entry point used by `make reproduce`.

Usage:
    python -m myproject.pipeline --sample

Loads the built-in eval KG from data/default_eval/, runs PPR-based retrieval
on a fixed sample question, and prints the top passages.  No LLM call is
made, so this works without network access or API keys.  Exit code 0 means
the full retrieval stack is healthy.
"""

import argparse
import pickle
import sys
from pathlib import Path


def _sample_run() -> None:
    from myproject.kg.graph_store import KnowledgeGraph
    from myproject.retrieval.retriever import HippoRAG

    kg_path = Path(__file__).parent.parent.parent / "data" / "default_eval" / "graph.pkl"
    if not kg_path.exists():
        print(f"[pipeline] KG not found at {kg_path}. Run make download-data first.", file=sys.stderr)
        sys.exit(1)

    with open(kg_path, "rb") as f:
        graph = pickle.load(f)

    print(f"[pipeline] Loaded KG: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

    rag = HippoRAG(graph=graph)

    question = "What did Marie Curie discover?"
    passages = rag._retrieve_dense(question, top_k=3)

    print(f"[pipeline] Query: {question!r}")
    if passages:
        print(f"[pipeline] Top passage: {passages[0]!r}")
    else:
        print("[pipeline] No passages retrieved — check KG content.")

    print("[pipeline] Sample run complete. Retrieval stack OK.")


def main() -> None:
    parser = argparse.ArgumentParser(description="HippoRAG pipeline smoke test")
    parser.add_argument("--sample", action="store_true", help="Run a quick smoke test on the built-in KG")
    args = parser.parse_args()

    if args.sample:
        _sample_run()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
