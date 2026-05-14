# GraphRAG/community_detector.py
"""
Community detection for GraphRAG.

The original Microsoft GraphRAG paper uses the Leiden algorithm (Traag et al.,
2019) via the `leidenalg` Python package.  Because `leidenalg` requires
`igraph` and is not in the project's requirements.txt, we provide a two-level
fallback chain so the system always works even in environments where the
optional package is not installed:

  Level 1 — Leiden via `leidenalg`   (best quality, matches the paper)
  Level 2 — Louvain via `networkx-community` greedy modularity
             (good quality, pure Python, always available)
  Level 3 — Connected components     (last resort, very coarse)

The result of any level is the same data structure: a list of communities,
each community being a list of entity names.  The downstream summariser and
persistence layer are identical regardless of which level was used.

The detector also assigns a numeric community_id to each node in the graph
so the retriever can look up which community an entity belongs to in O(1).
"""

import logging
from typing import List

import networkx as nx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_communities(graph: nx.Graph) -> List[List[str]]:
    """
    Partition the nodes of *graph* into communities.

    Parameters
    ----------
    graph : nx.Graph
        The entity graph produced by GraphRAGGraph.

    Returns
    -------
    communities : list[list[str]]
        Each inner list is one community — a list of entity name strings.
        Communities are sorted by size (largest first) so the summariser
        processes the most important ones first.

    Side-effects
    ------------
    Sets the ``community_id`` attribute on every node in *graph* so the
    retriever can answer "which community does entity X belong to?" in O(1).
    """
    if graph.number_of_nodes() == 0:
        logger.warning("Community detector: graph is empty — returning no communities.")
        return []

    # Remove self-loops before detection (they confuse some algorithms)
    graph_clean = graph.copy()
    graph_clean.remove_edges_from(nx.selfloop_edges(graph_clean))

    # ── Level 1: Leiden ──────────────────────────────────────────────────────
    communities = _try_leiden(graph_clean)

    # ── Level 2: Louvain / greedy modularity ────────────────────────────────
    if communities is None:
        communities = _try_louvain(graph_clean)

    # ── Level 3: Connected components (last resort) ──────────────────────────
    if communities is None:
        logger.warning(
            "Community detector: falling back to connected components. "
            "Install 'leidenalg' or 'python-louvain' for better results."
        )
        communities = [list(c) for c in nx.connected_components(graph_clean)]

    # Sort communities: largest first
    communities.sort(key=len, reverse=True)

    # Annotate each node with its community ID
    for cid, community in enumerate(communities):
        for node in community:
            if node in graph.nodes:
                graph.nodes[node]["community_id"] = cid

    logger.info(
        f"Community detection complete: {len(communities)} communities, "
        f"{graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges."
    )
    return communities


# ---------------------------------------------------------------------------
# Level 1: Leiden
# ---------------------------------------------------------------------------

def _try_leiden(graph: nx.Graph):
    """
    Attempt community detection using the Leiden algorithm via `leidenalg`.

    Returns None if the package is not installed.
    """
    try:
        import leidenalg
        import igraph as ig
    except ImportError:
        logger.info("leidenalg/igraph not installed — skipping Leiden.")
        return None

    try:
        # Convert NetworkX graph to igraph
        # We use the edge list + node list approach to preserve node names.
        nodes = list(graph.nodes())
        node_index = {n: i for i, n in enumerate(nodes)}

        edges = [
            (node_index[u], node_index[v])
            for u, v in graph.edges()
        ]
        weights = [
            float(graph[u][v].get("weight", 1.0))
            for u, v in graph.edges()
        ]

        ig_graph = ig.Graph(n=len(nodes), edges=edges, directed=False)
        ig_graph.es["weight"] = weights

        partition = leidenalg.find_partition(
            ig_graph,
            leidenalg.ModularityVertexPartition,
            weights="weight",
        )

        communities = []
        for cluster in partition:
            communities.append([nodes[i] for i in cluster])

        logger.info(f"Leiden: found {len(communities)} communities.")
        return communities

    except Exception as exc:
        logger.warning(f"Leiden detection failed: {exc} — falling back.")
        return None


# ---------------------------------------------------------------------------
# Level 2: Louvain / greedy modularity
# ---------------------------------------------------------------------------

def _try_louvain(graph: nx.Graph):
    """
    Attempt community detection using networkx's greedy modularity algorithm.

    This is always available (pure NetworkX, no extra packages).
    The greedy modularity algorithm is an approximation of Louvain and gives
    reasonable results for graphs with a few hundred to a few thousand nodes.
    """
    try:
        from networkx.algorithms.community import greedy_modularity_communities

        result = greedy_modularity_communities(
            graph, weight="weight"
        )
        communities = [list(c) for c in result]
        logger.info(f"Greedy modularity: found {len(communities)} communities.")
        return communities

    except Exception as exc:
        logger.warning(f"Greedy modularity failed: {exc} — falling back.")
        return None