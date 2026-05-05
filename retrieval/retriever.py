# retrieval/retriever.py
from kg.graph_store import KnowledgeGraph
from retrieval.triple_matcher import TripleMatcher
from retrieval.filter import TripleFilter
from retrieval.ppr import run_ppr
from llm.llm_client import LLMClient
from config.config_loader import load_config


class HippoRAG:
    def __init__(self):
        self.config = load_config()
        self.kg = KnowledgeGraph()
        self.kg.load(self.config["kg"]["save_path"])

        self.matcher = TripleMatcher(self.kg.triples)
        self.filter = TripleFilter()
        self.llm = LLMClient()

    def query(self, query):
        # Step 1: triple matching
        triples = self.matcher.match(query)

        # Step 2: filtering
        filtered = self.filter.filter(query, triples)

        # Step 3: seeds
        seeds = list(set([s for s, _, _, _ in filtered]))

        # Step 4: PPR
        scores = run_ppr(
            self.kg.graph,
            seeds,
            self.config["retrieval"]["ppr_alpha"],
            self.config["retrieval"]["max_iter"]
        )

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        top_nodes = [n for n, _ in ranked[:self.config["retrieval"]["top_k"]]]

        context = "\n".join(top_nodes)

        return self.llm.generate(f"""
Answer using context:

{context}

Question:
{query}
""")