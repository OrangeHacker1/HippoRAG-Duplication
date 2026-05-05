# retrieval/retriever.py
from retrieval.query_processor import QueryProcessor
from retrieval.ppr import PPR
from llm.llm_client import LLMClient
from kg.graph_store import KnowledgeGraph

class HippoRetriever:
    def __init__(self, graph_path="kg.pkl"):
        self.kg = KnowledgeGraph()
        self.kg.load(graph_path)

        self.query_processor = QueryProcessor()
        self.llm = LLMClient()
        self.ppr = PPR(self.kg.graph)

    def retrieve(self, query, top_k=5):
        # Step 1: query → nodes
        seeds = self.query_processor.extract_entities(query)

        # Step 2: PPR traversal
        ranked = self.ppr.run(seeds)

        top_nodes = [n for n, _ in ranked[:top_k]]

        # Step 3: build context
        context = "\n".join(top_nodes)

        # Step 4: answer generation
        prompt = f"""
Answer the question using the context.

Context:
{context}

Question:
{query}
"""
        return self.llm.generate(prompt)