# run_query.py
from retrieval.retriever import HippoRetriever

retriever = HippoRetriever()

query = "Who developed relativity and what did it impact?"
answer = retriever.retrieve(query)

print("\nANSWER:\n", answer)