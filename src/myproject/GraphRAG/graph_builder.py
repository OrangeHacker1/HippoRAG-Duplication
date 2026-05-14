# GraphRAG/graph_builder.py
"""
Graph construction for GraphRAG.

Builds a NetworkX undirected weighted graph where:
  - Nodes  = named entities (with metadata: type, frequency, source passages)
  - Edges  = relationships between entities (with metadata: label, weight, sources)

Edge weight reflects how many times two entities co-occur or are explicitly
related across the corpus.  The Leiden community detector uses these weights
to find densely-connected clusters (communities) that correspond to coherent
topics or sub-topics in the document set.

Design choices vs. HippoRAG's KnowledgeGraph
---------------------------------------------
- HippoRAG uses a DiGraph (directed) because relation direction matters for PPR.
- GraphRAG uses an undirected Graph because community detection algorithms
  (Leiden, Louvain, greedy modularity) work on undirected graphs.
- HippoRAG stores raw passage text on passage nodes.
- GraphRAG stores aggregated passage text on entity nodes so each entity
  carries all the context passages it appeared in — this feeds the community
  summariser without needing to walk the graph.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
Entity        = str
RelationLabel = str
RelationTriple = Tuple[Entity, RelationLabel, Entity]


class GraphRAGGraph:
    """
    Wrapper around a NetworkX undirected Graph for GraphRAG.

    Attributes
    ----------
    graph : nx.Graph
        The underlying NetworkX graph (undirected, weighted).
    entity_passages : dict[str, list[str]]
        Maps each entity name to the list of passage texts it appeared in.
        Used by the community summariser to build per-community context.
    """

    def __init__(self):
        self.graph: nx.Graph = nx.Graph()
        # entity → [passage_text, ...]
        self.entity_passages: Dict[str, List[str]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def add_entities_and_relations(
        self,
        entities: List[Entity],
        relations: List[RelationTriple],
        source_text: str,
    ) -> None:
        """
        Incorporate the output of EntityExtractor.extract() for one passage.

        For each entity:
          - Create the node if it does not exist.
          - Increment its frequency counter.
          - Append the source passage to entity_passages.

        For each relation (head, label, tail):
          - Create an edge if it does not exist (weight = 0).
          - Increment the edge weight by 1.
          - Accumulate relation labels on the edge (for the summariser).
        """
        # ── Nodes ───────────────────────────────────────────────────────
        for entity in entities:
            if entity not in self.graph:
                self.graph.add_node(
                    entity,
                    type="entity",
                    frequency=0,
                    passages=[],       # list of passage texts (stored on node)
                )
            # Increment frequency
            self.graph.nodes[entity]["frequency"] += 1
            # Append source passage (may duplicate if same passage hit twice)
            self.graph.nodes[entity]["passages"].append(source_text)
            # Also store in the separate dict for O(1) lookup
            self.entity_passages[entity].append(source_text)

        # ── Edges ────────────────────────────────────────────────────────
        for head, label, tail in relations:
            # Ensure both endpoints exist even if they were missed by NER
            for endpoint in (head, tail):
                if endpoint not in self.graph:
                    self.graph.add_node(
                        endpoint,
                        type="entity",
                        frequency=0,
                        passages=[],
                    )

            if self.graph.has_edge(head, tail):
                self.graph[head][tail]["weight"] += 1
                labels: list = self.graph[head][tail].get("labels", [])
                if label not in labels:
                    labels.append(label)
                self.graph[head][tail]["labels"] = labels
            else:
                self.graph.add_edge(
                    head,
                    tail,
                    weight=1,
                    labels=[label],
                )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    def edge_count(self) -> int:
        return self.graph.number_of_edges()

    def get_entity_context(self, entity: Entity, max_passages: int = 5) -> str:
        """
        Return up to *max_passages* source passages for *entity*, joined by newlines.
        Used by the community summariser to build the prompt context.
        """
        passages = self.entity_passages.get(entity, [])
        # Deduplicate while preserving order
        seen: set = set()
        unique: List[str] = []
        for p in passages:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        return "\n".join(unique[:max_passages])

    def get_community_context(
        self, community_entities: List[Entity], max_passages_per_entity: int = 3
    ) -> str:
        """
        Aggregate passage context for a whole community.
        Used to build the summarisation prompt for one community.
        """
        seen_passages: set = set()
        all_passages: List[str] = []
        for entity in community_entities:
            for passage in self.entity_passages.get(entity, [])[:max_passages_per_entity]:
                if passage not in seen_passages:
                    seen_passages.add(passage)
                    all_passages.append(passage)
        return "\n\n".join(all_passages)