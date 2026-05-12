import networkx as nx
import pickle
from pathlib import Path


class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.triples = []

    def add_triple(self, s, r, o, source_text=None):
        self.graph.add_node(s, type="entity")
        self.graph.add_node(o, type="entity")

        self.graph.add_edge(s, o, relation=r)

        self.triples.append((s, r, o, source_text))

        if source_text:
            passage_id = f"passage_{hash(source_text)}"
            self.graph.add_node(passage_id, type="passage", text=source_text)

            self.graph.add_edge(s, passage_id, relation="contains")
            self.graph.add_edge(o, passage_id, relation="contains")

    def _resolve_path(self, path: str) -> Path:
        """
        Resolve both absolute Docker paths and relative local-dev paths.
        """

        p = Path(path)

        # Absolute path inside Docker/container
        if p.is_absolute():
            p.parent.mkdir(parents=True, exist_ok=True)
            return p

        # Relative local-dev path
        base = Path(__file__).parent.parent
        resolved = base / p
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    def save(self, path: str):
        resolved = self._resolve_path(path)
        with open(resolved, "wb") as f:
            pickle.dump((self.graph, self.triples), f)

    def load(self, path: str):
        resolved = self._resolve_path(path)
        with open(resolved, "rb") as f:
            self.graph, self.triples = pickle.load(f)