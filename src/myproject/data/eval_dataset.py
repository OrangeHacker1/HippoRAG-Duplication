# Multi-hop evaluation corpus and questions.
# Each question requires connecting facts across at least 2 documents.

import json
from pathlib import Path


def load_eval_json(path, limit=None):
    """Load eval questions from the official HippoRAG JSON format.

    Supports musique.json, hotpotqa.json, 2wikimultihopqa.json, sample.json.
    Returns a list of {question, gold_docs, gold_answers} dicts compatible
    with the eval pipeline.
    """
    data = json.loads(Path(path).read_text())
    questions = []
    for item in data[:limit] if limit else data:
        gold_docs = [
            p["paragraph_text"]
            for p in item.get("paragraphs", [])
            if p.get("is_supporting")
        ]
        gold_answers = [item["answer"]] + item.get("answer_aliases", [])
        questions.append({
            "question": item["question"],
            "gold_docs": gold_docs,
            "gold_answers": [a for a in gold_answers if a],
        })
    return questions


def load_corpus_json(path, limit=None):
    """Load corpus passages from the official HippoRAG corpus JSON format.

    Supports musique_corpus.json, hotpotqa_corpus.json, etc.
    Returns a list of passage strings (title + text) for KGBuilder.build().
    """
    data = json.loads(Path(path).read_text())
    entries = data[:limit] if limit else data
    return [f"{item['title']}: {item['text']}" for item in entries]

CORPUS = [
    "Marie Curie was born in Warsaw.",
    "Warsaw is the capital of Poland.",
    "Marie Curie won the Nobel Prize in Chemistry.",
    "Albert Einstein developed the theory of relativity.",
    "The theory of relativity revolutionized modern physics.",
    "Albert Einstein was awarded the Nobel Prize in Physics in 1921.",
    "Isaac Newton formulated the laws of classical mechanics.",
    "Classical mechanics describes the motion of everyday objects.",
    "Isaac Newton was born in Woolsthorpe, England.",
    "Woolsthorpe is a village in Lincolnshire.",
]

QUESTIONS = [
    {
        "question": "What country was Marie Curie born in?",
        "gold_docs": [
            "Marie Curie was born in Warsaw.",
            "Warsaw is the capital of Poland.",
        ],
        "gold_answers": ["Poland"],
    },
    {
        "question": "What scientific field did the developer of the theory of relativity receive a Nobel Prize in?",
        "gold_docs": [
            "Albert Einstein developed the theory of relativity.",
            "Albert Einstein was awarded the Nobel Prize in Physics in 1921.",
        ],
        "gold_answers": ["Physics"],
    },
    {
        "question": "What does the branch of science that Newton formulated describe?",
        "gold_docs": [
            "Isaac Newton formulated the laws of classical mechanics.",
            "Classical mechanics describes the motion of everyday objects.",
        ],
        "gold_answers": ["the motion of everyday objects"],
    },
    {
        "question": "What county is the birthplace of the scientist who formulated classical mechanics in?",
        "gold_docs": [
            "Isaac Newton formulated the laws of classical mechanics.",
            "Isaac Newton was born in Woolsthorpe, England.",
            "Woolsthorpe is a village in Lincolnshire.",
        ],
        "gold_answers": ["Lincolnshire"],
    },
]
