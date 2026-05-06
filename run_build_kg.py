# run_build_kg.py
from kg.builder import KGBuilder

docs = [
    "Albert Einstein developed the theory of relativity.",
    "The theory of relativity changed physics.",
    "Newton developed classical mechanics."
]

builder = KGBuilder()
#builder.build_from_docs(docs)
#builder.build(docs)

path = "C:/Users/Jordan/Documents/GitHub/HippoRAG-Duplication/Official-HippoRAG-Repo/reproduce/dataset/2wikimultihopqa_corpus.json"

builder = KGBuilder()
builder.build(path)

print("Knowledge Graph built.")