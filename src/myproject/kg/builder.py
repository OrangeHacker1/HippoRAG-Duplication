# kg/builder.py
from myproject.llm.llm_client import LLMClient
from myproject.kg.graph_store import KnowledgeGraph
from myproject.kg.embeddings import EmbeddingEngine
from myproject.config.config_loader import load_config


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

        # Embedding linking — vectorized cosine similarity (avoids O(n²) loop)
        if node_texts:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity as batch_cosine

            unique_texts = list(dict.fromkeys(node_texts))  # deduplicate, preserve order
            embeddings = self.embedder.encode(unique_texts)
            emb_matrix = np.array(embeddings)
            sim_matrix = batch_cosine(emb_matrix)
            threshold = self.config["kg"]["similarity_threshold"]

            n = len(unique_texts)
            for i in range(n):
                for j in range(i + 1, n):
                    if sim_matrix[i, j] > threshold:
                        self.kg.graph.add_edge(unique_texts[i], unique_texts[j], relation="similar")

        self.kg.save(self.config["kg"]["save_path"])
