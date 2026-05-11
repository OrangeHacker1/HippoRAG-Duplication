# run_eval.py
import random
from myproject.kg.builder import KGBuilder
from myproject.retrieval.retriever import HippoRAG
from myproject.eval.metrics import recall_at_k, exact_match, f1_score
from myproject.data.eval_dataset import CORPUS, QUESTIONS

print("Building knowledge graph from eval corpus...")
builder = KGBuilder()
builder.build(CORPUS)
print("Knowledge graph built.\n")

rag = HippoRAG()

questions = random.sample(QUESTIONS, 3)

recall_ks = [1, 2, 5]
recall_totals = {k: 0.0 for k in recall_ks}
em_total = 0.0
f1_total = 0.0

print(f"Running {len(questions)} queries...\n")
print("=" * 60)

for i, item in enumerate(questions):
    question = item["question"]
    gold_docs = item["gold_docs"]
    gold_answers = item["gold_answers"]

    passages = rag.retrieve(question)
    answer = rag.llm.generate(f"""
Answer using context:

{chr(10).join(passages)}

Question:
{question}
""")

    em = exact_match(answer, gold_answers)
    f1 = f1_score(answer, gold_answers)
    em_total += em
    f1_total += f1

    print(f"Q{i+1}: {question}")
    print(f"  Retrieved: {passages}")
    print(f"  Answer:    {answer.strip()}")
    print(f"  Gold:      {gold_answers}")
    print(f"  EM: {em:.2f}  F1: {f1:.2f}")

    for k in recall_ks:
        r = recall_at_k(passages, gold_docs, k)
        recall_totals[k] += r
        print(f"  Recall@{k}: {r:.2f}")

    print()

n = len(QUESTIONS)
print("=" * 60)
print("AGGREGATE RESULTS")
print("=" * 60)
for k in recall_ks:
    print(f"  Recall@{k}: {recall_totals[k] / n:.4f}")
print(f"  ExactMatch: {em_total / n:.4f}")
print(f"  F1:         {f1_total / n:.4f}")
