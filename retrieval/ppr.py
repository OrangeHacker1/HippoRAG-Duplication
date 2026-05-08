# retrieval/ppr.py
import networkx as nx


def run_ppr(graph, seeds, alpha=0.85, max_iter=100):
    valid_seeds = [s for s in seeds if s in graph.nodes]

    if valid_seeds:
        personalization = {n: 0 for n in graph.nodes}
        for s in valid_seeds:
            personalization[s] = 1
    else:
        personalization = None  # uniform distribution

    return nx.pagerank(
        graph,
        alpha=alpha,
        personalization=personalization,
        max_iter=max_iter
    )


def run_ppr_weighted(graph, personalization, alpha=0.85, max_iter=100):
    valid = {k: v for k, v in personalization.items() if k in graph.nodes and v > 0}
    if not valid:
        return nx.pagerank(graph, alpha=alpha, max_iter=max_iter)
    return nx.pagerank(graph, alpha=alpha, personalization=valid, max_iter=max_iter)