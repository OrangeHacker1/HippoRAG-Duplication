# run_query.py
from retrieval.retriever import HippoRAG

rag = HippoRAG()

answer =rag.query("Who influenced physics through relativity?")

print("\nANSWER:\n", answer)