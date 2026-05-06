import pytest
import tempfile
import os
from kg.graph_store import KnowledgeGraph


@pytest.mark.unit
class TestKnowledgeGraph:
    def setup_method(self):
        self.kg = KnowledgeGraph()

    def test_add_triple_creates_nodes(self):
        self.kg.add_triple("Einstein", "developed", "relativity", "Einstein developed relativity.")
        assert "Einstein" in self.kg.graph.nodes
        assert "relativity" in self.kg.graph.nodes

    def test_add_triple_creates_edge(self):
        self.kg.add_triple("Einstein", "developed", "relativity", "Einstein developed relativity.")
        assert self.kg.graph.has_edge("Einstein", "relativity")

    def test_add_triple_creates_passage_node(self):
        text = "Einstein developed relativity."
        self.kg.add_triple("Einstein", "developed", "relativity", text)
        passage_nodes = [
            n for n, d in self.kg.graph.nodes(data=True) if d.get("type") == "passage"
        ]
        assert len(passage_nodes) == 1
        assert self.kg.graph.nodes[passage_nodes[0]]["text"] == text

    def test_entity_nodes_have_correct_type(self):
        self.kg.add_triple("Einstein", "developed", "relativity", "doc")
        assert self.kg.graph.nodes["Einstein"]["type"] == "entity"
        assert self.kg.graph.nodes["relativity"]["type"] == "entity"

    def test_triples_list_populated(self):
        self.kg.add_triple("Einstein", "developed", "relativity", "doc")
        assert len(self.kg.triples) == 1
        assert self.kg.triples[0][:3] == ("Einstein", "developed", "relativity")

    def test_save_and_load(self):
        self.kg.add_triple("Newton", "formulated", "mechanics", "Newton formulated mechanics.")
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            path = f.name
        try:
            self.kg.save(path)
            kg2 = KnowledgeGraph()
            kg2.load(path)
            assert "Newton" in kg2.graph.nodes
            assert len(kg2.triples) == 1
        finally:
            os.unlink(path)
