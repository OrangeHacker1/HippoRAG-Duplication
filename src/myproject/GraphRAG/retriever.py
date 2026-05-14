# GraphRAG/retriever.py
"""
Query-time retrieval for GraphRAG.

GraphRAG supports two query modes (from the Microsoft paper):

  LOCAL  search — anchor to specific entities mentioned in the query, then
                  retrieve the communities those entities belong to.
                  Best for: specific factual questions ("Who is X?", "When did Y happen?")

  GLOBAL search — score ALL community summaries against the query and return
                  the top-k by embedding similarity.
                  Best for: thematic / broad questions ("What are the main themes?")

We implement both and expose a unified retrieve() method that:
  1. Tries LOCAL first (if query entities match graph entities).
  2. Falls back to GLOBAL if no local matches are found.

This mirrors the HippoRAG retriever's interface so the evaluate endpoint
can call either pipeline interchangeably.

Reuses:
  - myproject.kg.embeddings.EmbeddingEngine  (same sentence-transformers model)
  - myproject.llm.llm_client.LLMClient       (for entity extraction from query)
  - myproject.config.config_loader            (top_k, etc.)
"""

import logging
from typing import Dict, List, Optional, Tuple

from myproject.kg.embeddings import EmbeddingEngine
from myproject.llm.llm_client import LLMClient
from myproject.config.config_loader import load_config

logger = logging.getLogger(__name__)


class GraphRAGRetriever:
    """
    Retriever that uses GraphRAG community summaries.

    Parameters
    ----------
    state : dict
        The loaded GraphRAG state dict from persistence.load_graphrag().
        Keys: "graph" (GraphRAGGraph), "communities" (list[list[str]]),
              "summaries" (dict[int, dict]).
    """

    def __init__(self, state: Dict):
        self.graph_wrapper = state["graph"]          # GraphRAGGraph
        self.communities   = state["communities"]    # list[list[str]]
        self.summaries     = state["summaries"]      # dict[int, dict]
        self.config        = load_config()
        self.embedder      = EmbeddingEngine()
        self.llm           = LLMClient()
        self.top_k         = self.config["retrieval"]["top_k"]

        # Pre-compute embeddings for all community summaries (done once at load)
        self._summary_texts: List[str] = []
        self._summary_ids:   List[int] = []
        self._summary_embeddings       = None
        self._build_summary_index()

    # ------------------------------------------------------------------
    # Index construction (called once at init)
    # ------------------------------------------------------------------

    def _build_summary_index(self) -> None:
        """Pre-embed all community summaries for fast cosine retrieval."""
        if not self.summaries:
            logger.warning("GraphRAGRetriever: no community summaries to index.")
            return

        texts = []
        ids   = []
        for cid, summary_data in self.summaries.items():
            summary_text = summary_data.get("summary", "")
            if summary_text.strip():
                # Prepend entity names to the text being embedded so the
                # embedding captures both the thematic summary AND the entity names.
                entities_prefix = ", ".join(summary_data.get("entities", [])[:10])
                combined = f"{entities_prefix}. {summary_text}" if entities_prefix else summary_text
                texts.append(combined)
                ids.append(cid)

        if texts:
            self._summary_texts      = texts
            self._summary_ids        = ids
            self._summary_embeddings = self.embedder.encode(texts)
            logger.info(
                f"GraphRAGRetriever: indexed {len(texts)} community summaries."
            )

    # ------------------------------------------------------------------
    # Public API — matches HippoRAG.retrieve() signature
    # ------------------------------------------------------------------

    def retrieve(self, query: str) -> List[str]:
        """
        Retrieve relevant community summaries for *query*.

        Returns a list of strings (community summaries) in ranked order.
        The caller (evaluate endpoint) treats these like passages from HippoRAG.
        """
        if not self.summaries:
            return ["No community summaries available. Build the GraphRAG index first."]

        # ── Try local search first ───────────────────────────────────────────
        local_results = self._local_search(query)
        if local_results:
            return local_results[:self.top_k]

        # ── Fall back to global search ───────────────────────────────────────
        return self._global_search(query)[:self.top_k]

    def query(self, query: str) -> str:
        """
        Retrieve relevant summaries and generate an answer via the LLM.
        Mirrors HippoRAG.query() so the two are interchangeable.
        """
        summaries = self.retrieve(query)
        context   = "\n\n".join(summaries)
        return self.llm.generate(
            f"Answer using the following knowledge graph community summaries as context:\n\n"
            f"{context}\n\nQuestion:\n{query}"
        )

    # ------------------------------------------------------------------
    # Local search
    # ------------------------------------------------------------------

    def _local_search(self, query: str) -> List[str]:
        """
        Find entities in the query → look up their community → return summary.
        """
        graph = self.graph_wrapper.graph
        if graph.number_of_nodes() == 0:
            return []

        # Embed the query and find the most similar entity nodes
        q_emb       = self.embedder.encode([query])[0]
        entity_nodes = list(graph.nodes())
        if not entity_nodes:
            return []

        entity_embeddings = self.embedder.encode(entity_nodes)

        # Rank entities by similarity to the query
        scores: List[Tuple[float, str]] = []
        for i, e_emb in enumerate(entity_embeddings):
            sim = float(self.embedder.similarity(q_emb, e_emb))
            scores.append((sim, entity_nodes[i]))
        scores.sort(reverse=True)

        # Collect the communities of the top-matching entities
        seen_communities: set = set()
        result_summaries: List[str] = []

        threshold = 0.5  # similarity threshold for "local" match
        for sim, entity in scores[:20]:  # check top-20 entities
            if sim < threshold:
                break
            cid = graph.nodes[entity].get("community_id")
            if cid is not None and cid not in seen_communities:
                seen_communities.add(cid)
                summary_data = self.summaries.get(cid, {})
                summary_text = summary_data.get("summary", "")
                if summary_text:
                    result_summaries.append(summary_text)
            if len(result_summaries) >= self.top_k:
                break

        return result_summaries

    # ------------------------------------------------------------------
    # Global search
    # ------------------------------------------------------------------

    def _global_search(self, query: str) -> List[str]:
        """
        Score all community summaries against the query by embedding similarity.
        """
        if self._summary_embeddings is None or len(self._summary_texts) == 0:
            return []

        q_emb = self.embedder.encode([query])[0]

        scores: List[Tuple[float, int]] = []
        for i, s_emb in enumerate(self._summary_embeddings):
            sim = float(self.embedder.similarity(q_emb, s_emb))
            scores.append((sim, i))
        scores.sort(reverse=True)

        results: List[str] = []
        for sim, idx in scores[:self.top_k]:
            cid          = self._summary_ids[idx]
            summary_data = self.summaries.get(cid, {})
            summary_text = summary_data.get("summary", "")
            if summary_text:
                results.append(summary_text)

        return results