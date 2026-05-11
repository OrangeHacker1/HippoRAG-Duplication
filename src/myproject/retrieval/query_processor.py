# retrieval/query_processor.py
from myproject.llm.llm_client import LLMClient

class QueryProcessor:
    def __init__(self):
        self.llm = LLMClient()

    def extract_entities(self, query: str):
        prompt = f"""
Extract key entities from this query.
Return as comma-separated list.

Query: {query}
"""
        output = self.llm.generate(prompt)
        return [e.strip() for e in output.split(",")]