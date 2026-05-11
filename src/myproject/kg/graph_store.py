import networkx as nx
import pickle


class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.triples = []

    def add_triple(self, s, r, o, source_text=None):
        self.graph.add_node(s, type="entity")
        self.graph.add_node(o, type="entity")

        self.graph.add_edge(s, o, relation=r)

        self.triples.append((s, r, o, source_text))

        # Add passage node
        if source_text:
            passage_id = f"passage_{hash(source_text)}"
            self.graph.add_node(passage_id, type="passage", text=source_text)

            self.graph.add_edge(s, passage_id, relation="contains")
            self.graph.add_edge(o, passage_id, relation="contains")

    def save(self, path):
        with open(path, "wb") as f:
            pickle.dump((self.graph, self.triples), f)

    def load(self, path):
        with open(path, "rb") as f:
            self.graph, self.triples = pickle.load(f)