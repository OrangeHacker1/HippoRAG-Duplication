# retrieval/retriever.py
from myproject.kg.graph_store import KnowledgeGraph
from myproject.kg.embeddings import EmbeddingEngine
from myproject.retrieval.triple_matcher import TripleMatcher
from myproject.retrieval.filter import TripleFilter
from myproject.retrieval.query_processor import QueryProcessor
from myproject.retrieval.ppr import run_ppr
from myproject.llm.llm_client import LLMClient
from myproject.config.config_loader import load_config


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

    def retrieve(self, query):
        # Step 1: triple matching
        triples = self.matcher.match(query)

        # Step 2: filtering
        filtered = self.filter.filter(query, triples)

        # Step 3: seeds from triple subjects + query entity extraction
        triple_seeds = list(set([s for s, _, _, _ in filtered]))
        query_entities = self.processor.extract_entities(query)
        entity_seeds = self._match_query_entities(query_entities)
        seeds = list(set(triple_seeds + entity_seeds))

        # Step 4: PPR
        scores = run_ppr(
            self.kg.graph,
            seeds,
            self.config["retrieval"]["ppr_alpha"],
            self.config["retrieval"]["max_iter"]
        )

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        passages = []
        for node, _ in ranked:
            if len(passages) >= self.config["retrieval"]["top_k"]:
                break
            node_data = self.kg.graph.nodes[node]
            if node_data.get("type") == "passage":
                passages.append(node_data["text"])

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
