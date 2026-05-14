# GraphRAG/builder.py
"""
GraphRAG pipeline orchestrator.

Mirrors the structure of myproject/kg/builder.py (KGBuilder) so both can be
called identically from the FastAPI train endpoint.  Accepts the same
`progress_callback` signature so progress messages stream to the browser
via the existing SSE infrastructure in app.py.

Full pipeline
-------------
  1. Entity & relationship extraction   (one LLM call per document)
  2. Graph construction                 (NetworkX undirected Graph)
  3. Community detection                (Leiden → Louvain → components)
  4. Community summarisation            (one LLM call per community)

The output is a state dict:
    {
        "graph":       GraphRAGGraph,
        "communities": list[list[str]],
        "summaries":   dict[int, dict],
    }

This dict is passed directly to GraphRAG.persistence.save_graphrag().

Comparison with KGBuilder
--------------------------
KGBuilder:
  - extracts (s, r, o) triples
  - builds a directed graph
  - computes similarity edges between nodes
  - returns the NetworkX DiGraph

GraphRAGBuilder:
  - extracts entities + relationships
  - builds an undirected co-occurrence graph
  - detects communities
  - generates one LLM summary per community
  - returns a state dict (graph + communities + summaries)
"""

import logging
from typing import Callable, Dict, List, Optional

from myproject.GraphRAG.entity_extractor   import EntityExtractor
from myproject.GraphRAG.graph_builder      import GraphRAGGraph
from myproject.GraphRAG.community_detector import detect_communities
from myproject.GraphRAG.summarizer         import CommunitySummarizer

logger = logging.getLogger(__name__)


class GraphRAGBuilder:
    """
    Orchestrates the full GraphRAG build pipeline.

    Parameters
    ----------
    progress_callback : callable, optional
        Called with a single string argument after each major step.
        Signature: callback(message: str) -> None
        Matches KGBuilder's callback signature for drop-in compatibility
        with the SSE streaming infrastructure in app.py.
    """

    def __init__(self, progress_callback: Optional[Callable[[str], None]] = None):
        self.progress_callback = progress_callback
        self.extractor         = EntityExtractor()

    # ------------------------------------------------------------------
    # Private helper
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        """Forward a progress message to the callback (if any) and to the logger."""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, docs: List[str]) -> Dict:
        """
        Build a complete GraphRAG index from a list of document strings.

        Parameters
        ----------
        docs : list[str]
            Plain-text passages.  Same format as KGBuilder.build() — one
            string per passage (can be a sentence, paragraph, or article).

        Returns
        -------
        dict
            {
                "graph":       GraphRAGGraph instance,
                "communities": list[list[str]],
                "summaries":   dict[int, dict],
            }
        """
        graph_wrapper = GraphRAGGraph()
        total_docs    = len(docs)

        # ── Phase 1: Entity & relationship extraction ────────────────────────
        self._log(f"[GraphRAG] Phase 1/3: Extracting entities from {total_docs} documents ...")

        total_entities  = 0
        total_relations = 0

        for idx, doc in enumerate(docs):
            self._log(
                f"[GraphRAG] Processing document {idx + 1}/{total_docs} ..."
            )

            try:
                entities, relations = self.extractor.extract(doc)
            except Exception as exc:
                self._log(
                    f"[GraphRAG] Warning: extraction failed for doc {idx + 1}: {exc} — skipping."
                )
                entities, relations = [], []

            if entities or relations:
                graph_wrapper.add_entities_and_relations(entities, relations, doc)

            total_entities  += len(entities)
            total_relations += len(relations)

            self._log(
                f"[GraphRAG]   → {len(entities)} entities, "
                f"{len(relations)} relations extracted."
            )

        self._log(
            f"[GraphRAG] Phase 1 complete: "
            f"{total_entities} total entities, "
            f"{total_relations} total relations, "
            f"{graph_wrapper.node_count()} unique nodes, "
            f"{graph_wrapper.edge_count()} edges in graph."
        )

        # ── Phase 2: Community detection ─────────────────────────────────────
        self._log(
            f"[GraphRAG] Phase 2/3: Detecting communities in graph "
            f"({graph_wrapper.node_count()} nodes, {graph_wrapper.edge_count()} edges) ..."
        )

        if graph_wrapper.node_count() == 0:
            self._log("[GraphRAG] Warning: graph is empty — no communities to detect.")
            communities = []
        else:
            communities = detect_communities(graph_wrapper.graph)

        self._log(
            f"[GraphRAG] Phase 2 complete: {len(communities)} communities detected."
        )

        # ── Phase 3: Community summarisation ─────────────────────────────────
        self._log(
            f"[GraphRAG] Phase 3/3: Summarising {len(communities)} communities ..."
        )

        if not communities:
            self._log("[GraphRAG] No communities to summarise.")
            summaries: Dict = {}
        else:
            summarizer = CommunitySummarizer(
                graph_wrapper       = graph_wrapper,
                max_context_passages = 4,
            )
            summaries = summarizer.summarise_all(
                communities       = communities,
                progress_callback = self.progress_callback,
            )

        self._log(
            f"[GraphRAG] Build complete: "
            f"{graph_wrapper.node_count()} nodes, "
            f"{graph_wrapper.edge_count()} edges, "
            f"{len(communities)} communities, "
            f"{len(summaries)} community summaries."
        )

        return {
            "graph":       graph_wrapper,
            "communities": communities,
            "summaries":   summaries,
        }