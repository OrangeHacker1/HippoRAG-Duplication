# kg/builder.py
from llm.llm_client import LLMClient
from kg.graph_store import KnowledgeGraph
from kg.embeddings import EmbeddingEngine
from config.config_loader import load_config


class KGBuilder:
    def __init__(self):
        self.llm = LLMClient()
        self.kg = KnowledgeGraph()
        self.embedder = EmbeddingEngine()
        self.config = load_config()

    def build(self, docs):
        node_texts = []

        for doc in docs:
            triples = self.llm.extract_triples(doc)

            for s, r, o in triples:
                self.kg.add_triple(s, r, o, doc)
                node_texts.extend([s, o])

        # Embedding linking
        embeddings = self.embedder.encode(node_texts)

        for i, a in enumerate(node_texts):
            for j, b in enumerate(node_texts):
                if i >= j:
                    continue

                sim = self.embedder.similarity(embeddings[i], embeddings[j])

                if sim > self.config["kg"]["similarity_threshold"]:
                    self.kg.graph.add_edge(a, b, relation="similar")

        self.kg.save(self.config["kg"]["save_path"])