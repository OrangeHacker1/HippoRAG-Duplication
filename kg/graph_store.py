# kg/graph_store.py
import networkx as nx
import pickle

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_triple(self, s, r, o):
        self.graph.add_node(s)
        self.graph.add_node(o)
        self.graph.add_edge(s, o, relation=r)

    def save(self, path="kg.pkl"):
        with open(path, "wb") as f:
            pickle.dump(self.graph, f)

    def load(self, path="kg.pkl"):
        with open(path, "rb") as f:
            self.graph = pickle.load(f)