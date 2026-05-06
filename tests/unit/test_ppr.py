import pytest
import networkx as nx
from retrieval.ppr import run_ppr


@pytest.mark.unit
class TestPPR:
    def setup_method(self):
        self.graph = nx.DiGraph()
        self.graph.add_nodes_from(["A", "B", "C", "D"])
        self.graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "D")])

    def test_returns_scores_for_all_nodes(self):
        scores = run_ppr(self.graph, ["A"])
        assert set(scores.keys()) == {"A", "B", "C", "D"}

    def test_seed_node_has_highest_score(self):
        scores = run_ppr(self.graph, ["A"])
        assert scores["A"] == max(scores.values())

    def test_empty_seeds_returns_uniform(self):
        scores = run_ppr(self.graph, [])
        assert len(scores) == 4

    def test_scores_sum_to_one(self):
        scores = run_ppr(self.graph, ["A"])
        assert abs(sum(scores.values()) - 1.0) < 1e-6

    def test_unknown_seed_ignored(self):
        scores = run_ppr(self.graph, ["Z"])
        assert len(scores) == 4
