from kg.embeddings import EmbeddingEngine


class DenseRetriever:
    def __init__(self, passages):
        self.passages = passages
        self.embedder = EmbeddingEngine()
        self.passage_embs = self.embedder.encode(passages)

    def retrieve(self, query, top_k=5):
        q_emb = self.embedder.encode([query])[0]
        scores = [
            (i, float(self.embedder.similarity(q_emb, e)))
            for i, e in enumerate(self.passage_embs)
        ]
        scores.sort(key=lambda x: x[1], reverse=True)
        return [self.passages[i] for i, _ in scores[:top_k]]
