# retrieval/ppr.py
import networkx as nx


def run_ppr(graph, seeds, alpha=0.85, max_iter=30):
    personalization = {n: 0 for n in graph.nodes}

    for s in seeds:
        if s in personalization:
            personalization[s] = 1

    return nx.pagerank(
        graph,
        alpha=alpha,
        personalization=personalization,
        max_iter=max_iter
    )