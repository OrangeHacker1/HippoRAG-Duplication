"""
Partial replication of HippoRAG v2 Table 2 (F1) and Table 3 (Recall@5)
on a MuSiQue subset.

Usage (connect to UTSA VPN first):
    python EXTRA/scripts/run_musique_eval.py --questions 50

Outputs results to reports/musique_results.json and prints a summary
table comparable to Tables 2 and 3 in the v2 paper.
"""
import argparse
import json
import os

from myproject.kg.builder import KGBuilder
from myproject.kg.embeddings import EmbeddingEngine
from myproject.retrieval.triple_matcher import TripleMatcher
from myproject.retrieval.filter import TripleFilter
from myproject.retrieval.query_processor import QueryProcessor
from myproject.retrieval.ppr import run_ppr
from myproject.llm.llm_client import LLMClient
from myproject.config.config_loader import load_config
from myproject.eval.metrics import f1_score as token_f1


def load_musique_subset(questions_path, n_questions=50):
    with open(questions_path) as f:
        data = json.load(f)
    answerable = [q for q in data if q["answerable"]]
    return answerable[:n_questions]


def build_corpus_from_questions(questions):
    """Collect unique passages with their titles from question paragraphs."""
    seen = set()
    corpus = []  # list of (title, text)
    for q in questions:
        for p in q["paragraphs"]:
            key = p["title"] + "||" + p["paragraph_text"]
            if key not in seen:
                seen.add(key)
                corpus.append((p["title"], p["paragraph_text"]))
    return corpus


def recall_at_k_titles(retrieved_passages, gold_titles, k):
    """Check if any gold title appears as substring in top-k retrieved passages."""
    top_k = retrieved_passages[:k]
    hits = sum(
        1 for title in gold_titles
        if any(title.lower() in p.lower() for p in top_k)
    )
    return hits / len(gold_titles) if gold_titles else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=int, default=50)
    parser.add_argument("--musique-path",
                        default="Official-HippoRAG-Repo/reproduce/dataset/musique.json")
    parser.add_argument("--output", default="reports/musique_results.json")
    args = parser.parse_args()

    config = load_config()
    llm = LLMClient()

    print(f"Loading {args.questions} MuSiQue questions...")
    questions = load_musique_subset(args.musique_path, args.questions)
    print(f"Loaded {len(questions)} answerable questions")

    print("Building corpus from question paragraphs...")
    corpus_with_titles = build_corpus_from_questions(questions)
    corpus_texts = [text for _, text in corpus_with_titles]
    print(f"Corpus: {len(corpus_texts)} unique passages")

    print("Building knowledge graph (this will take a while — one LLM call per passage)...")
    builder = KGBuilder()
    builder.build(corpus_texts)
    kg = builder.kg
    print(f"KG: {kg.graph.number_of_nodes()} nodes, {kg.graph.number_of_edges()} edges")

    # Set up retrieval components
    matcher = TripleMatcher(kg.triples)
    triple_filter = TripleFilter()
    processor = QueryProcessor()
    embedder = EmbeddingEngine()

    entity_nodes = [
        n for n, d in kg.graph.nodes(data=True)
        if d.get("type") == "entity"
    ]
    entity_embeddings = embedder.encode(entity_nodes) if entity_nodes else []

    def retrieve(query):
        triples = matcher.match(query)
        filtered = triple_filter.filter(query, triples)
        triple_seeds = list(set([s for s, _, _, _ in filtered]))

        query_entities = processor.extract_entities(query)
        entity_seeds = []
        if query_entities and entity_nodes:
            query_embs = embedder.encode(query_entities)
            for qe in query_embs:
                best_score, best_node = -1, None
                for i, ne in enumerate(entity_embeddings):
                    sim = embedder.similarity(qe, ne)
                    if sim > best_score:
                        best_score, best_node = sim, entity_nodes[i]
                if best_score >= 0.75 and best_node:
                    entity_seeds.append(best_node)

        seeds = list(set(triple_seeds + entity_seeds))
        scores = run_ppr(kg.graph, seeds,
                         config["retrieval"]["ppr_alpha"],
                         config["retrieval"]["max_iter"])
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        passages = []
        for node, _ in ranked:
            if len(passages) >= config["retrieval"]["top_k"]:
                break
            node_data = kg.graph.nodes[node]
            if node_data.get("type") == "passage":
                passages.append(node_data["text"])
        return passages

    print("\nRunning evaluation...")
    results = []
    f1_scores, r1_scores, r2_scores, r5_scores = [], [], [], []

    for i, q in enumerate(questions):
        question_text = q["question"]
        gold_answer = q["answer"]
        gold_aliases = q.get("answer_aliases", [])
        gold_titles = [p["title"] for p in q["paragraphs"] if p["is_supporting"]]

        try:
            passages = retrieve(question_text)
            context = "\n\n".join(passages[:5])
            answer = llm.generate(
                f"Answer in one short phrase using only the context below.\n\n"
                f"Context:\n{context}\n\nQuestion: {question_text}\nAnswer:"
            )

            r1 = recall_at_k_titles(passages, gold_titles, k=1)
            r2 = recall_at_k_titles(passages, gold_titles, k=2)
            r5 = recall_at_k_titles(passages, gold_titles, k=5)
            f1 = token_f1(answer, [gold_answer] + gold_aliases)

            r1_scores.append(r1)
            r2_scores.append(r2)
            r5_scores.append(r5)
            f1_scores.append(f1)

            results.append({
                "id": q["id"],
                "question": question_text,
                "gold_answer": gold_answer,
                "predicted_answer": answer,
                "gold_titles": gold_titles,
                "recall@1": r1,
                "recall@2": r2,
                "recall@5": r5,
                "f1": f1,
            })
            print(f"[{i+1}/{len(questions)}] R@5={r5:.2f} F1={f1:.2f} | {question_text[:60]}")

        except Exception as e:
            print(f"[{i+1}/{len(questions)}] ERROR: {e}")
            results.append({"id": q["id"], "question": question_text, "error": str(e)})

    n = len(f1_scores)
    aggregate = {
        "num_questions": len(questions),
        "num_evaluated": n,
        "Recall@1": round(sum(r1_scores) / n, 4) if n else 0,
        "Recall@2": round(sum(r2_scores) / n, 4) if n else 0,
        "Recall@5": round(sum(r5_scores) / n, 4) if n else 0,
        "F1": round(sum(f1_scores) / n, 4) if n else 0,
    }

    os.makedirs("reports", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"aggregate": aggregate, "results": results}, f, indent=2)

    print("\n" + "=" * 60)
    print("RESULTS — MuSiQue subset (partial replication of v2 Tables 2 & 3)")
    print("=" * 60)
    print(f"{'Metric':<20} {'Ours':>10} {'v2 Paper (full)':>16}")
    print("-" * 60)
    print(f"{'Recall@1':<20} {aggregate['Recall@1']:>10.4f} {'—':>16}")
    print(f"{'Recall@2':<20} {aggregate['Recall@2']:>10.4f} {'—':>16}")
    print(f"{'Recall@5':<20} {aggregate['Recall@5']:>10.4f} {'0.9450':>16}")
    print(f"{'F1':<20} {aggregate['F1']:>10.4f} {'0.7820':>16}")
    print("-" * 60)
    print(f"Evaluated: {n}/{len(questions)} questions")
    print(f"Saved: {args.output}")
    print()
    print("Differences vs v2 paper:")
    print("  - Embedder: all-MiniLM-L6-v2 (vs NV-Embed-v2 7B)")
    print("  - LLM: UTSA endpoint (vs Llama-3.3-70B-Instruct)")
    print(f"  - Scale: {n} questions (vs 1,000)")


if __name__ == "__main__":
    main()
