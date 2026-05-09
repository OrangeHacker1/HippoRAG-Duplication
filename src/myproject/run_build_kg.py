# run_build_kg.py
from kg.builder import KGBuilder

docs = [
    "Albert Einstein developed the theory of relativity.",
    "The theory of relativity changed physics.",
    "Newton developed classical mechanics."
]

builder = KGBuilder()
#builder.build_from_docs(docs)
builder.build(docs)

print("Knowledge Graph built.")