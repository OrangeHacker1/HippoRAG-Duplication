# kg/embeddings.py
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from config.config_loader import load_config


class EmbeddingEngine:
    def __init__(self):
        config = load_config()
        self.model = SentenceTransformer(config["embedding"]["model"])

    def encode(self, texts):
        return self.model.encode(texts)

    def similarity(self, a, b):
        return cosine_similarity([a], [b])[0][0]