"""
run_tables.py
Replicates Tables 1-5, 10, and 12 from HippoRAG 2 (arXiv:2502.14802) on the
bundled eval dataset. Run from the project root after `make build-kg`.

Tables produced:
  Table 1  — Dataset statistics
  Table 2  — QA performance F1  (requires LLM; prints N/A if unreachable)
  Table 3  — Retrieval Recall@2 / @5
  Table 4  — Ablation study (Recall@5)
  Table 5  — Reset probability (passage_weight) sweep
  Table 10 — Knowledge graph statistics
  Table 12 — Indexing / query timing
"""

import os
import sys
import time

# ── helpers ──────────────────────────────────────────────────────────────────

def _row(cells, widths):
    return "  ".join(str(c).ljust(w) for c, w in zip(cells, widths))

def _table(header, rows, title=""):
    widths = [max(len(str(x)) for x in [h] + [r[i] for r in rows]) for i, h in enumerate(header)]
    sep = "  ".join("-" * w for w in widths)
    if title:
        print(title)
    print(_row(header, widths))
    print(sep)
    for row in rows:
        print(_row(row, widths))
    print()

NA = "N/A"

# ── LLM probe ────────────────────────────────────────────────────────────────

def llm_available():
    try:
        from llm.llm_client import LLMClient
        LLMClient().generate("ping")
        return True
    except Exception:
        return False

# ── dataset ──────────────────────────────────────────────────────────────────

from data.eval_dataset import CORPUS, QUESTIONS
from eval.metrics import recall_at_k, exact_match, f1_score

# ── retrieval helpers ────────────────────────────────────────────────────────

def eval_recall(retrieve_fn, questions, top_k_list=(2, 5)):
    totals = {k: 0.0 for k in top_k_list}
    for item in questions:
        passages = retrieve_fn(item["question"])
        for k in top_k_list:
            totals[k] += recall_at_k(passages, item["gold_docs"], k)
    n = len(questions)
    return {k: round(totals[k] / n, 4) for k in top_k_list}

def eval_qa(retrieve_fn, questions, llm_generate):
    em_total, f1_total = 0.0, 0.0
    for item in questions:
        passages = retrieve_fn(item["question"])
        context = "\n".join(passages)
        answer = llm_generate(
            f"Answer using context:\n\n{context}\n\nQuestion:\n{item['question']}"
        )
        em_total += exact_match(answer, item["gold_answers"])
        f1_total += f1_score(answer, item["gold_answers"])
    n = len(questions)
    return round(em_total / n, 4), round(f1_total / n, 4)

# ── KG loading ───────────────────────────────────────────────────────────────

def load_kg():
    from kg.graph_store import KnowledgeGraph
    from config.config_loader import load_config
    cfg = load_config()
    path = cfg["kg"]["save_path"]
    if not os.path.exists(path):
        print(f"[ERROR] KG not found at {path}. Run 'make build-kg' first.")
        sys.exit(1)
    kg = KnowledgeGraph()
    kg.load(path)
    return kg

# ══════════════════════════════════════════════════════════════════════════════
# Table 1 — Dataset statistics
# ══════════════════════════════════════════════════════════════════════════════

def table1():
    print("=" * 60)
    _table(
        ["Dataset", "Num queries", "Num passages"],
        [["eval (multi-hop)", len(QUESTIONS), len(CORPUS)]],
        title="Table 1. Dataset statistics.",
    )

# ══════════════════════════════════════════════════════════════════════════════
# Tables 2 & 3 — QA performance and Retrieval performance
# ══════════════════════════════════════════════════════════════════════════════

def tables2_and_3(rag, bm25, dense, has_llm):
    from config.config_loader import load_config
    cfg = load_config()
    top_k = cfg["retrieval"]["top_k"]

    methods = []

    # BM25
    t0 = time.perf_counter()
    bm25_recall = eval_recall(lambda q: bm25.retrieve(q, top_k), QUESTIONS)
    bm25_time = time.perf_counter() - t0
    if has_llm:
        bm25_em, bm25_f1 = eval_qa(lambda q: bm25.retrieve(q, top_k), QUESTIONS, rag.llm.generate)
    else:
        bm25_em, bm25_f1 = NA, NA
    methods.append(("BM25", bm25_recall, bm25_em, bm25_f1, bm25_time))

    # Dense embedding
    t0 = time.perf_counter()
    dense_recall = eval_recall(lambda q: dense.retrieve(q, top_k), QUESTIONS)
    dense_time = time.perf_counter() - t0
    if has_llm:
        dense_em, dense_f1 = eval_qa(lambda q: dense.retrieve(q, top_k), QUESTIONS, rag.llm.generate)
    else:
        dense_em, dense_f1 = NA, NA
    methods.append(("Dense (MiniLM)", dense_recall, dense_em, dense_f1, dense_time))

    # HippoRAG v1-style: NER-to-node, no passage nodes, no filter
    if has_llm:
        t0 = time.perf_counter()
        v1_recall = eval_recall(
            lambda q: rag.retrieve(q, linking_method="ner_to_node", use_passage_nodes=False, use_filter=False),
            QUESTIONS,
        )
        v1_time = time.perf_counter() - t0
        v1_em, v1_f1 = eval_qa(
            lambda q: rag.retrieve(q, linking_method="ner_to_node", use_passage_nodes=False, use_filter=False),
            QUESTIONS,
            rag.llm.generate,
        )
    else:
        v1_recall = {2: NA, 5: NA}
        v1_em, v1_f1 = NA, NA
        v1_time = None
    methods.append(("HippoRAG (v1-style)", v1_recall, v1_em, v1_f1, v1_time))

    # HippoRAG 2, no filter (runnable without LLM)
    t0 = time.perf_counter()
    h2nf_recall = eval_recall(
        lambda q: rag.retrieve(q, linking_method="query_to_triple", use_passage_nodes=True, use_filter=False),
        QUESTIONS,
    )
    h2nf_time = time.perf_counter() - t0
    if has_llm:
        h2nf_em, h2nf_f1 = eval_qa(
            lambda q: rag.retrieve(q, linking_method="query_to_triple", use_passage_nodes=True, use_filter=False),
            QUESTIONS,
            rag.llm.generate,
        )
    else:
        h2nf_em, h2nf_f1 = NA, NA
    methods.append(("HippoRAG 2 (w/o filter)", h2nf_recall, h2nf_em, h2nf_f1, h2nf_time))

    # HippoRAG 2 full
    if has_llm:
        t0 = time.perf_counter()
        h2_recall = eval_recall(
            lambda q: rag.retrieve(q, linking_method="query_to_triple", use_passage_nodes=True, use_filter=True),
            QUESTIONS,
        )
        h2_time = time.perf_counter() - t0
        h2_em, h2_f1 = eval_qa(
            lambda q: rag.retrieve(q, linking_method="query_to_triple", use_passage_nodes=True, use_filter=True),
            QUESTIONS,
            rag.llm.generate,
        )
    else:
        h2_recall = {2: NA, 5: NA}
        h2_em, h2_f1 = NA, NA
        h2_time = None
    methods.append(("HippoRAG 2 (full)", h2_recall, h2_em, h2_f1, h2_time))

    print("=" * 60)
    print(
        "Table 2. QA performance (F1 scores) on eval dataset.\n"
        "  N/A = LLM endpoint unreachable (connect to VPN first)."
    )
    _table(
        ["Method", "EM", "F1"],
        [(name, em, f1) for name, _, em, f1, _ in methods],
    )

    print("=" * 60)
    print("Table 3. Retrieval performance (Recall@2 / @5) on eval dataset.")
    _table(
        ["Method", "Recall@2", "Recall@5"],
        [
            (name, recall.get(2, NA), recall.get(5, NA))
            for name, recall, _, _, _ in methods
        ],
    )

    return methods

# ══════════════════════════════════════════════════════════════════════════════
# Table 4 — Ablation
# ══════════════════════════════════════════════════════════════════════════════

def table4(rag, has_llm):
    print("=" * 60)
    print("Table 4. Ablation. Recall@5 on eval dataset (multi-hop questions).")

    rows = []

    # Full HippoRAG 2 (best variant — query_to_triple w/ filter w/ passage nodes)
    h2_r = eval_recall(
        lambda q: rag.retrieve(q, linking_method="query_to_triple", use_passage_nodes=True, use_filter=False),
        QUESTIONS,
    )
    rows.append(["HippoRAG 2 (w/o filter, query_to_triple)", h2_r[5]])

    if has_llm:
        h2f_r = eval_recall(
            lambda q: rag.retrieve(q, linking_method="query_to_triple", use_passage_nodes=True, use_filter=True),
            QUESTIONS,
        )
        rows.append(["HippoRAG 2 (full)", h2f_r[5]])

        ner_r = eval_recall(
            lambda q: rag.retrieve(q, linking_method="ner_to_node", use_passage_nodes=True, use_filter=False),
            QUESTIONS,
        )
        rows.append(["w/ NER to node", ner_r[5]])
    else:
        rows.append(["HippoRAG 2 (full)", NA + " (needs LLM)"])
        rows.append(["w/ NER to node", NA + " (needs LLM)"])

    qtn_r = eval_recall(
        lambda q: rag.retrieve(q, linking_method="query_to_node", use_passage_nodes=True, use_filter=False),
        QUESTIONS,
    )
    rows.append(["w/ Query to node", qtn_r[5]])

    no_pass_r = eval_recall(
        lambda q: rag.retrieve(q, linking_method="query_to_triple", use_passage_nodes=False, use_filter=False),
        QUESTIONS,
    )
    rows.append(["w/o Passage Node", no_pass_r[5]])

    _table(["Method", "Recall@5"], rows)

# ══════════════════════════════════════════════════════════════════════════════
# Table 5 — Reset probability (passage_weight) sweep
# ══════════════════════════════════════════════════════════════════════════════

def table5(rag):
    print("=" * 60)
    print(
        "Table 5. Reset probability factor. Recall@5 on eval dataset\n"
        "  with different passage_weight values (query_to_triple, w/o filter)."
    )
    weights = [0.01, 0.05, 0.1, 0.3, 0.5]
    rows = []
    for w in weights:
        r = eval_recall(
            lambda q, w=w: rag.retrieve(
                q,
                linking_method="query_to_triple",
                use_passage_nodes=True,
                use_filter=False,
                passage_weight=w,
            ),
            QUESTIONS,
        )
        rows.append([w, r[5]])
    _table(["passage_weight", "Recall@5"], rows)

# ══════════════════════════════════════════════════════════════════════════════
# Table 10 — Knowledge graph statistics
# ══════════════════════════════════════════════════════════════════════════════

def table10(kg):
    print("=" * 60)
    g = kg.graph
    phrase_nodes = [n for n, d in g.nodes(data=True) if d.get("type") == "entity"]
    passage_nodes = [n for n, d in g.nodes(data=True) if d.get("type") == "passage"]
    extracted_edges = [(u, v) for u, v, d in g.edges(data=True) if d.get("relation") not in ("similar", "contains")]
    synonym_edges = [(u, v) for u, v, d in g.edges(data=True) if d.get("relation") == "similar"]
    context_edges = [(u, v) for u, v, d in g.edges(data=True) if d.get("relation") == "contains"]

    _table(
        ["Statistic", "Count"],
        [
            ["# phrase nodes (entities)", len(phrase_nodes)],
            ["# passage nodes", len(passage_nodes)],
            ["# total nodes", g.number_of_nodes()],
            ["# extracted (relation) edges", len(extracted_edges)],
            ["# synonym edges", len(synonym_edges)],
            ["# context (contains) edges", len(context_edges)],
            ["# total edges", g.number_of_edges()],
        ],
        title="Table 10. Knowledge graph statistics (eval corpus).",
    )

# ══════════════════════════════════════════════════════════════════════════════
# Table 12 — Efficiency
# ══════════════════════════════════════════════════════════════════════════════

def table12(has_llm):
    print("=" * 60)
    print(
        "Table 12. Computational resource requirements on eval corpus\n"
        "  (10 passages). Indexing time includes KG build; query time per question."
    )

    import pickle
    from config.config_loader import load_config
    cfg = load_config()

    rows = []

    # BM25 indexing time
    t0 = time.perf_counter()
    from retrieval.bm25_retriever import BM25Retriever
    bm25 = BM25Retriever(CORPUS)
    bm25_idx = round(time.perf_counter() - t0, 4)
    t0 = time.perf_counter()
    for item in QUESTIONS:
        bm25.retrieve(item["question"])
    bm25_qry = round((time.perf_counter() - t0) / len(QUESTIONS), 4)
    rows.append(["BM25", f"{bm25_idx}s", f"{bm25_qry}s"])

    # Dense indexing time
    t0 = time.perf_counter()
    from retrieval.dense_retriever import DenseRetriever
    dense = DenseRetriever(CORPUS)
    dense_idx = round(time.perf_counter() - t0, 4)
    t0 = time.perf_counter()
    for item in QUESTIONS:
        dense.retrieve(item["question"])
    dense_qry = round((time.perf_counter() - t0) / len(QUESTIONS), 4)
    rows.append(["Dense (MiniLM)", f"{dense_idx}s", f"{dense_qry}s"])

    # HippoRAG 2 indexing: loading pre-built KG + building retriever
    t0 = time.perf_counter()
    from retrieval.retriever import HippoRAG
    rag = HippoRAG()
    h2_idx = round(time.perf_counter() - t0, 4)
    t0 = time.perf_counter()
    for item in QUESTIONS:
        rag.retrieve(item["question"], use_filter=False)
    h2_qry = round((time.perf_counter() - t0) / len(QUESTIONS), 4)
    rows.append(["HippoRAG 2 (w/o filter)", f"{h2_idx}s", f"{h2_qry}s"])

    if has_llm:
        t0 = time.perf_counter()
        for item in QUESTIONS:
            rag.retrieve(item["question"], use_filter=True)
        h2f_qry = round((time.perf_counter() - t0) / len(QUESTIONS), 4)
        rows.append(["HippoRAG 2 (full, w/ filter)", f"{h2_idx}s", f"{h2f_qry}s"])

    _table(["Method", "Index Time", "Query Time/question"], rows)

# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("HippoRAG 2 — Table Replication Script")
    print("Dataset: bundled eval_dataset.py (10 passages, 4 multi-hop Qs)")
    print("=" * 60 + "\n")

    print("Checking LLM endpoint...", end=" ", flush=True)
    HAS_LLM = llm_available()
    print("available" if HAS_LLM else "unreachable (VPN needed) — retrieval-only tables will run")
    print()

    print("Loading knowledge graph...", end=" ", flush=True)
    kg = load_kg()
    print("done.\n")

    # Instantiate retrievers (embedding model loads once here)
    from retrieval.bm25_retriever import BM25Retriever
    from retrieval.dense_retriever import DenseRetriever
    from retrieval.retriever import HippoRAG

    print("Initialising retrievers (embedding model)...", end=" ", flush=True)
    bm25 = BM25Retriever(CORPUS)
    dense = DenseRetriever(CORPUS)
    rag = HippoRAG()
    print("done.\n")

    table1()
    tables2_and_3(rag, bm25, dense, HAS_LLM)
    table4(rag, HAS_LLM)
    table5(rag)
    table10(kg)
    table12(HAS_LLM)

    print("=" * 60)
    print("Done. Connect to VPN and re-run for N/A cells (LLM-dependent).")
