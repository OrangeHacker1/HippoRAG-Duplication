# GraphRAG/summarizer.py
"""
Community summarisation for GraphRAG.

After community detection, each community is a list of related entity names.
The summariser generates a natural-language summary for each community by:

  1. Collecting all source passages that mention any entity in the community
     (via GraphRAGGraph.get_community_context).
  2. Calling the LLM with those passages + the entity list to produce a
     concise thematic summary.

These summaries become the retrieval units at query time: instead of returning
raw passages (as HippoRAG does), GraphRAG returns community summaries and uses
the LLM to synthesise a final answer from them.

Prompt design
-------------
The prompt follows the structure from the Microsoft GraphRAG paper (Edge et al.,
2024 — "From Local to Global: A Graph RAG Approach to Query-Focused Summarization"):
  - Give the LLM the list of entities in the community.
  - Give it the supporting source passages.
  - Ask for a concise thematic summary that captures the main ideas and relationships.

We keep max_tokens at 256 per summary (configurable) to stay within LLM limits
even for large corpora.
"""

import logging
from typing import Dict, List

from myproject.llm.llm_client import LLMClient
from myproject.config.config_loader import load_config

logger = logging.getLogger(__name__)


class CommunitySummarizer:
    """
    Generate natural-language summaries for GraphRAG communities.

    Parameters
    ----------
    graph_wrapper : GraphRAGGraph
        The populated entity graph (used to fetch passage context).
    max_context_passages : int
        Maximum number of source passages to include per community when
        building the summarisation prompt.  Larger = more context but higher
        latency and token cost.
    """

    _SUMMARY_PROMPT = """\
You are summarising a thematic cluster from a knowledge graph.

The following entities are closely related and appear together across multiple documents:
{entity_list}

Source passages that mention these entities:
{context}

Write a concise summary (3-5 sentences) describing:
- What these entities have in common
- The key facts and relationships between them
- Why they form a coherent topic or theme

Summary:"""

    def __init__(self, graph_wrapper, max_context_passages: int = 6):
        self.graph_wrapper       = graph_wrapper
        self.max_context_passages = max_context_passages
        self.llm                 = LLMClient()
        self.config              = load_config()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def summarise_all(
        self, communities: List[List[str]], progress_callback=None
    ) -> Dict[int, Dict]:
        """
        Generate summaries for all communities.

        Parameters
        ----------
        communities : list[list[str]]
            Output of community_detector.detect_communities().
            Each inner list is one community (list of entity names).
        progress_callback : callable, optional
            Called with a string message after each community is summarised.
            Matches the KGBuilder progress_callback signature.

        Returns
        -------
        dict[int, dict]
            community_id → {
                "entities":  list[str],   entity names in this community
                "summary":   str,         LLM-generated summary text
                "size":      int,         number of entities
            }
        """
        results: Dict[int, Dict] = {}

        total = len(communities)
        for cid, community_entities in enumerate(communities):
            if not community_entities:
                continue

            if progress_callback:
                progress_callback(
                    f"Summarising community {cid + 1}/{total} "
                    f"({len(community_entities)} entities) ..."
                )

            summary = self._summarise_one(community_entities)

            results[cid] = {
                "entities": community_entities,
                "summary":  summary,
                "size":     len(community_entities),
            }

        if progress_callback:
            progress_callback(f"Summarisation complete: {len(results)} community summaries generated.")

        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _summarise_one(self, community_entities: List[str]) -> str:
        """
        Generate a summary for a single community.

        Falls back to a minimal summary if the LLM call fails, so a single
        bad community never aborts the whole build.
        """
        # Build context from source passages mentioning any entity in the community
        context = self.graph_wrapper.get_community_context(
            community_entities, max_passages_per_entity=3
        )

        # If we have no context at all, return a minimal stub
        if not context.strip():
            return (
                f"A cluster of related entities: "
                f"{', '.join(community_entities[:10])}."
            )

        # Trim context to avoid exceeding LLM context window
        # Rough heuristic: ~4 chars per token, aim for ~1500 tokens of context
        max_context_chars = 6000
        if len(context) > max_context_chars:
            context = context[:max_context_chars] + " [truncated]"

        entity_list = "\n".join(f"- {e}" for e in community_entities[:30])

        prompt = self._SUMMARY_PROMPT.format(
            entity_list=entity_list,
            context=context,
        )

        try:
            summary = self.llm.generate(prompt)
            return summary.strip()
        except Exception as exc:
            logger.warning(
                f"CommunitySummarizer: LLM call failed for community of size "
                f"{len(community_entities)}: {exc} — using fallback summary."
            )
            return (
                f"A cluster containing: "
                f"{', '.join(community_entities[:10])}. "
                "(Summary generation failed.)"
            )