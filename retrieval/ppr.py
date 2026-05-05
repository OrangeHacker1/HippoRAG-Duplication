# retrieval/ppr.py
import networkx as nx

class PPR:
    def __init__(self, graph):
        self.graph = graph

    def run(self, seed_nodes, alpha=0.85, max_iter=50):
        scores = {n: 0 for n in self.graph.nodes}

        for seed in seed_nodes:
            if seed in scores:
                scores[seed] = 1.0

        for _ in range(max_iter):
            new_scores = scores.copy()

            for node in self.graph.nodes:
                neighbors = list(self.graph.predecessors(node))
                rank_sum = sum(scores[n] / len(list(self.graph.successors(n)))
                               for n in neighbors if len(list(self.graph.successors(n))) > 0)

                new_scores[node] = (1 - alpha) + alpha * rank_sum

            scores = new_scores

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)