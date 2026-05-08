import re
from rank_bm25 import BM25Okapi


class BM25Retriever:
    def __init__(self, passages):
        self.passages = passages
        tokenized = [re.findall(r"\w+", p.lower()) for p in passages]
        self.bm25 = BM25Okapi(tokenized)

    def retrieve(self, query, top_k=5):
        tokens = re.findall(r"\w+", query.lower())
        scores = self.bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [self.passages[i] for i, _ in ranked[:top_k]]
