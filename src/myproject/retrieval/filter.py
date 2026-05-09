# retrieval/filter.py
from llm.llm_client import LLMClient
import re


class TripleFilter:
    def __init__(self):
        self.llm = LLMClient()

    def filter(self, query, triples):
        if not triples:
            return []

        numbered = "\n".join(
            f"{i}: ({s}, {r}, {o})" for i, (s, r, o, _) in enumerate(triples)
        )

        prompt = f"""You are given a query and a numbered list of knowledge graph triples.
Return ONLY the numbers of triples that are relevant to answering the query.
Format: a comma-separated list of integers, e.g. 0, 2, 5

Query: {query}

Triples:
{numbered}

Relevant triple numbers:"""

        output = self.llm.generate(prompt)

        indices = [int(x) for x in re.findall(r"\d+", output) if int(x) < len(triples)]

        return [triples[i] for i in indices] if indices else triples