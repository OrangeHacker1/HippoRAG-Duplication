# kg/builder.py

import json
from pathlib import Path

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

    # -------------------------
    # NEW: JSON LOADER
    # -------------------------
    def load_documents(self, path):
        path = Path(path)

        docs = []

        if path.suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

                for item in data:
                    if isinstance(item, dict):
                        docs.append(
                            item.get("text")
                            or item.get("content")
                            or str(item)
                        )
                    else:
                        docs.append(str(item))

        elif path.suffix == ".jsonl":
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    item = json.loads(line)

                    docs.append(
                        item.get("text")
                        or item.get("content")
                        or str(item)
                    )

        else:
            raise ValueError("Unsupported file format. Use .json or .jsonl")

        return docs

    # -------------------------
    # UPDATED BUILD FUNCTION
    # -------------------------
    def build(self, input_data):
        """
        input_data can be:
        - list of strings
        - path to JSON / JSONL file
        """

        # 🔹 Step 1: Load data
        if isinstance(input_data, str):
            docs = self.load_documents(input_data)
        else:
            docs = input_data

        node_texts = []

        # 🔹 Step 2: Triple extraction
        for doc in docs:
            if not doc or not isinstance(doc, str):
                continue

            triples = self.llm.extract_triples(doc)

            for t in triples:
                if len(t) != 3:
                    continue

                s, r, o = t

                self.kg.add_triple(s, r, o, doc)
                node_texts.extend([s, o])

        # 🔹 Step 3: Remove duplicates (IMPORTANT FIX)
        node_texts = list(set(node_texts))

        if len(node_texts) == 0:
            print("⚠️ No nodes extracted. KG is empty.")
            return

        # 🔹 Step 4: Embeddings
        embeddings = self.embedder.encode(node_texts)

        # 🔹 Step 5: Similarity linking
        for i, a in enumerate(node_texts):
            for j in range(i + 1, len(node_texts)):
                b = node_texts[j]

                sim = self.embedder.similarity(
                    embeddings[i],
                    embeddings[j]
                )

                if sim > self.config["kg"]["similarity_threshold"]:
                    self.kg.graph.add_edge(a, b, relation="similar")

        # 🔹 Step 6: Save KG
        self.kg.save(self.config["kg"]["save_path"])

        print(f"✅ KG built with {len(self.kg.graph.nodes)} nodes and {len(self.kg.graph.edges)} edges.")