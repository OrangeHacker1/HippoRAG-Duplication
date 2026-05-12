# kg/builder.py

from myproject.llm.llm_client import LLMClient
from myproject.kg.graph_store import KnowledgeGraph
from myproject.kg.embeddings import EmbeddingEngine
from myproject.config.config_loader import load_config


class KGBuilder:
    def __init__(self, progress_callback=None):
        self.llm = LLMClient()
        self.kg = KnowledgeGraph()
        self.embedder = EmbeddingEngine()
        self.config = load_config()

        # Optional callback for streaming progress updates
        self.progress_callback = progress_callback

    def _log(self, message: str):
        """
        Send progress updates to the callback if one exists.
        """
        if self.progress_callback:
            self.progress_callback(message)

    def build(self, docs):
        node_texts = []

        self._log(f"Starting build for {len(docs)} documents...")

        for idx, doc in enumerate(docs):
            self._log(f"Processing document {idx + 1}/{len(docs)}")

            triples = self.llm.extract_triples(doc)

            self._log(f"Extracted {len(triples)} triples")

            for s, r, o in triples:
                self.kg.add_triple(s, r, o, doc)
                node_texts.extend([s, o])

        self._log("Starting embedding generation...")

        # Embedding linking — vectorized cosine similarity
        if node_texts:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity as batch_cosine

            unique_texts = list(dict.fromkeys(node_texts))

            self._log(f"Encoding {len(unique_texts)} unique entities...")

            embeddings = self.embedder.encode(unique_texts)

            self._log("Computing similarity matrix...")

            emb_matrix = np.array(embeddings)
            sim_matrix = batch_cosine(emb_matrix)

            threshold = self.config["kg"]["similarity_threshold"]

            self._log(
                f"Linking similar nodes with threshold={threshold}"
            )

            n = len(unique_texts)
            links_added = 0

            for i in range(n):
                for j in range(i + 1, n):
                    if sim_matrix[i, j] > threshold:
                        self.kg.graph.add_edge(
                            unique_texts[i],
                            unique_texts[j],
                            relation="similar"
                        )
                        links_added += 1

            self._log(f"Added {links_added} similarity edges")

        self._log("Finalizing graph...")

        graph = self.kg.graph

        self._log(
            f"Build complete: "
            f"{graph.number_of_nodes()} nodes, "
            f"{graph.number_of_edges()} edges"
        )

        return graph


"""from myproject.llm.llm_client import LLMClient
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

        self.kg.save(self.config["kg"]["save_path"])"""