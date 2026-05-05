# retrieval/filter.py
from llm.llm_client import LLMClient


class TripleFilter:
    def __init__(self):
        self.llm = LLMClient()

    def filter(self, query, triples):
        prompt = f"""
Select relevant triples for answering the query.

Query:
{query}

Triples:
{triples}

Return ONLY relevant triples.
"""
        output = self.llm.generate(prompt)

        return triples  # simplified (can parse later)