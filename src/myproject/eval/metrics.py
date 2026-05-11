import string
from collections import Counter


def _normalize(text):
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return text.split()


def recall_at_k(retrieved_docs, gold_docs, k):
    top_k = retrieved_docs[:k]
    hits = sum(1 for doc in gold_docs if doc in top_k)
    return hits / len(gold_docs) if gold_docs else 0.0


def exact_match(predicted, gold_answers):
    pred_tokens = set(_normalize(predicted))
    for gold in gold_answers:
        gold_tokens = set(_normalize(gold))
        if gold_tokens and gold_tokens.issubset(pred_tokens):
            return 1.0
    return 0.0


def f1_score(predicted, gold_answers):
    pred_tokens = _normalize(predicted)
    best_f1 = 0.0
    for gold in gold_answers:
        gold_tokens = _normalize(gold)
        common = Counter(pred_tokens) & Counter(gold_tokens)
        num_common = sum(common.values())
        if num_common == 0:
            continue
        precision = num_common / len(pred_tokens) if pred_tokens else 0
        recall = num_common / len(gold_tokens) if gold_tokens else 0
        if precision + recall > 0:
            best_f1 = max(best_f1, 2 * precision * recall / (precision + recall))
    return best_f1
