# kg/builder.py
from llm.llm_client import LLMClient
from kg.graph_store import KnowledgeGraph

class KGBuilder:
    def __init__(self):
        self.llm = LLMClient()
        self.kg = KnowledgeGraph()

    def build_from_docs(self, docs: list):
        for doc in docs:
            triples = self.llm.extract_triples(doc)

            for t in triples:
                if len(t) == 3:
                    s, r, o = t
                    self.kg.add_triple(s, r, o)

        self.kg.save()
        return self.kg