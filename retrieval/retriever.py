# retrieval/retriever.py
from kg.graph_store import KnowledgeGraph
from kg.embeddings import EmbeddingEngine
from retrieval.triple_matcher import TripleMatcher
from retrieval.filter import TripleFilter
from retrieval.query_processor import QueryProcessor
from retrieval.ppr import run_ppr_weighted
from llm.llm_client import LLMClient
from config.config_loader import load_config


class HippoRAG:
    def __init__(self):
        self.config = load_config()
        self.kg = KnowledgeGraph()
        self.kg.load(self.config["kg"]["save_path"])

        self.matcher = TripleMatcher(self.kg.triples)
        self.filter = TripleFilter()
        self.processor = QueryProcessor()
        self.embedder = EmbeddingEngine()
        self.llm = LLMClient()

        self.entity_nodes = [
            n for n, d in self.kg.graph.nodes(data=True)
            if d.get("type") == "entity"
        ]
        self.entity_embeddings = self.embedder.encode(self.entity_nodes) if self.entity_nodes else []

        self.passage_nodes = [
            n for n, d in self.kg.graph.nodes(data=True)
            if d.get("type") == "passage"
        ]
        self.passage_texts = [self.kg.graph.nodes[n]["text"] for n in self.passage_nodes]
        self.passage_embeddings = self.embedder.encode(self.passage_texts) if self.passage_nodes else []

    def _match_query_entities(self, entities, threshold=0.75):
        if not entities or not self.entity_nodes:
            return []

        matched = []
        query_embs = self.embedder.encode(entities)

        for qe in query_embs:
            best_score, best_node = -1, None
            for i, ne in enumerate(self.entity_embeddings):
                sim = self.embedder.similarity(qe, ne)
                if sim > best_score:
                    best_score, best_node = sim, self.entity_nodes[i]
            if best_score >= threshold and best_node:
                matched.append(best_node)

        return matched

    def _match_query_to_nodes(self, query, top_k=5):
        if not self.entity_nodes:
            return []
        q_emb = self.embedder.encode([query])[0]
        scores = [
            (self.entity_nodes[i], float(self.embedder.similarity(q_emb, ne)))
            for i, ne in enumerate(self.entity_embeddings)
        ]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _embedding_fallback(self, query, top_k):
        if not self.passage_nodes:
            return []
        q_emb = self.embedder.encode([query])[0]
        scores = [
            (self.passage_nodes[i], self.passage_texts[i], float(self.embedder.similarity(q_emb, e)))
            for i, e in enumerate(self.passage_embeddings)
        ]
        scores.sort(key=lambda x: x[2], reverse=True)
        return [text for _, text, _ in scores[:top_k]]

    def retrieve(
        self,
        query,
        linking_method="query_to_triple",
        use_passage_nodes=True,
        use_filter=True,
        passage_weight=None,
    ):
        top_k = self.config["retrieval"]["top_k"]
        if passage_weight is None:
            passage_weight = self.config["retrieval"].get("passage_weight", 0.05)

        phrase_scores = {}

        if linking_method == "query_to_triple":
            all_triples, all_scores = self.matcher.match_with_scores(query)
            triple_to_score = {
                (s, r, o): sc for (s, r, o, _), sc in zip(all_triples, all_scores)
            }

            active_triples = all_triples
            if use_filter:
                try:
                    filtered = self.filter.filter(query, all_triples)
                    if filtered:
                        active_triples = filtered
                except Exception:
                    pass

            if not active_triples:
                return self._embedding_fallback(query, top_k)

            sums, counts = {}, {}
            for s, r, o, _ in active_triples:
                sc = triple_to_score.get((s, r, o), 0.5)
                for phrase in [s, o]:
                    sums[phrase] = sums.get(phrase, 0.0) + sc
                    counts[phrase] = counts.get(phrase, 0) + 1
            phrase_scores = {p: sums[p] / counts[p] for p in sums}

        elif linking_method == "ner_to_node":
            query_entities = self.processor.extract_entities(query)
            matched = self._match_query_entities(query_entities)
            phrase_scores = {n: 1.0 for n in matched}

        elif linking_method == "query_to_node":
            matched = self._match_query_to_nodes(query)
            phrase_scores = {n: sc for n, sc in matched}

        if not phrase_scores:
            return self._embedding_fallback(query, top_k)

        personalization = {
            phrase: score
            for phrase, score in phrase_scores.items()
            if phrase in self.kg.graph.nodes
        }

        if use_passage_nodes and self.passage_nodes:
            q_emb = self.embedder.encode([query])[0]
            for i, node in enumerate(self.passage_nodes):
                sim = float(self.embedder.similarity(q_emb, self.passage_embeddings[i]))
                personalization[node] = sim * passage_weight

        scores = run_ppr_weighted(
            self.kg.graph,
            personalization,
            self.config["retrieval"]["ppr_alpha"],
            self.config["retrieval"]["max_iter"],
        )

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        passages = []
        for node, _ in ranked:
            if len(passages) >= top_k:
                break
            if self.kg.graph.nodes[node].get("type") == "passage":
                passages.append(self.kg.graph.nodes[node]["text"])

        return passages

    def query(self, query):
        passages = self.retrieve(query)
        context = "\n".join(passages)

        return self.llm.generate(f"""
Answer using context:

{context}

Question:
{query}
""")
