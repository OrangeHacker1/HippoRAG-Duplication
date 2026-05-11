# retrieval/triple_matcher.py
from myproject.kg.embeddings import EmbeddingEngine


class TripleMatcher:
    def __init__(self, triples):
        self.triples = triples
        self.embedder = EmbeddingEngine()

        self.triple_texts = [
            f"{s} {r} {o}" for s, r, o, _ in triples
        ]
        self.triple_embeddings = self.embedder.encode(self.triple_texts)

    def match(self, query, top_k=10):
        q_emb = self.embedder.encode([query])[0]

        scores = []
        for i, emb in enumerate(self.triple_embeddings):
            sim = self.embedder.similarity(q_emb, emb)
            scores.append((i, sim))

        scores.sort(key=lambda x: x[1], reverse=True)

        return [self.triples[i] for i, _ in scores[:top_k]]