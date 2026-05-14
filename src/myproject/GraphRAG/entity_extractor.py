# GraphRAG/entity_extractor.py
"""
Entity and relationship extraction for GraphRAG.

Unlike HippoRAG's triple extractor (which produces structured (s, r, o) triples),
GraphRAG's entity extractor focuses on:
  1. Named entities — people, places, organisations, concepts
  2. Co-occurrence relationships — which entities appear together in a passage
  3. Explicit relationships — directional edges with a short description label

This produces a richer, denser graph than the triple approach because every
pair of entities that share a passage gets a co-occurrence edge even without
an explicit syntactic relation.  Community detection then clusters these
densely-connected entity neighbourhoods into thematic groups.

Reuses:
  - myproject.llm.llm_client.LLMClient   (same teacher LLM as HippoRAG)
  - myproject.config.config_loader        (same config.yaml)
"""

import json
import logging
from typing import List, Tuple

from myproject.llm.llm_client import LLMClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
Entity = str                                      # e.g. "Marie Curie"
RelationTriple = Tuple[Entity, str, Entity]       # (head, label, tail)


class EntityExtractor:
    """
    Extracts entities and labelled relationships from a single passage of text.

    Two extraction modes are combined:
      1. LLM-based named-entity + relationship extraction  (rich but slow)
      2. Co-occurrence edge injection                       (free, from NER output)

    The LLM is prompted to return a JSON object with two keys:
      "entities"      — list of entity name strings
      "relationships" — list of [head, label, tail] arrays

    The co-occurrence edges are computed locally: for every pair of entities
    returned by the LLM, we add a "co-occurs" edge.  This densifies the graph
    and gives the Leiden algorithm more signal to form communities.
    """

    # Prompt engineering note: we ask for *both* entities and relationships in
    # one call to halve the number of LLM round-trips.  The JSON format is
    # strict — no prose preamble — which makes parsing reliable.
    _EXTRACTION_PROMPT = """\
You are a knowledge-graph builder.  Read the passage below and extract:

1. All named entities (people, places, organisations, events, concepts, works).
2. Explicit relationships between those entities.

Return ONLY a JSON object — no explanation, no markdown fences.
Schema:
{{
  "entities": ["Entity A", "Entity B", ...],
  "relationships": [
    ["Entity A", "short relation label", "Entity B"],
    ...
  ]
}}

Rules:
- Entity names must be exactly as they appear (proper nouns, title case).
- Relation labels should be 1-4 words, present-tense verb phrase.
- If no relationships are found, return an empty list for "relationships".
- Do not invent entities not present in the text.

Passage:
{text}
"""

    def __init__(self):
        self.llm = LLMClient()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def extract(
        self, text: str
    ) -> Tuple[List[Entity], List[RelationTriple]]:
        """
        Extract entities and relationships from *text*.

        Returns
        -------
        entities : list[str]
            Deduplicated entity names found in the passage.
        relations : list[(head, label, tail)]
            Explicit labelled edges extracted by the LLM **plus** implicit
            co-occurrence edges for every entity pair in the passage.
        """
        if not text or not text.strip():
            return [], []

        # ── Step 1: LLM extraction ───────────────────────────────────────
        prompt = self._EXTRACTION_PROMPT.format(text=text.strip())
        try:
            raw = self.llm.generate(prompt)
            llm_entities, llm_relations = self._parse_llm_output(raw)
        except Exception as exc:
            logger.warning(f"EntityExtractor LLM call failed: {exc} — falling back to empty.")
            llm_entities, llm_relations = [], []

        # ── Step 2: Co-occurrence edges ──────────────────────────────────
        # Every pair of entities that share a passage gets a "co-occurs" edge.
        # This is cheap and dramatically densifies the graph, giving the
        # community detector much more signal.
        co_occurrence_edges: List[RelationTriple] = []
        unique_entities = list(dict.fromkeys(llm_entities))  # preserve order, deduplicate
        n = len(unique_entities)
        for i in range(n):
            for j in range(i + 1, n):
                co_occurrence_edges.append(
                    (unique_entities[i], "co-occurs", unique_entities[j])
                )
                co_occurrence_edges.append(
                    (unique_entities[j], "co-occurs", unique_entities[i])
                )

        all_relations = llm_relations + co_occurrence_edges

        return unique_entities, all_relations

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_llm_output(
        self, raw: str
    ) -> Tuple[List[Entity], List[RelationTriple]]:
        """
        Parse the JSON object returned by the LLM.

        Tolerant of:
          - Leading/trailing prose around the JSON object
          - Single-quoted instead of double-quoted keys
          - Missing keys (falls back to empty lists)
        """
        # Locate the outermost { ... } block
        try:
            start = raw.index("{")
            end   = raw.rindex("}") + 1
            blob  = raw[start:end]
        except ValueError:
            logger.debug("EntityExtractor: no JSON object found in LLM output.")
            return [], []

        try:
            parsed = json.loads(blob)
        except json.JSONDecodeError:
            # Last-resort: try replacing single quotes (common LLM quirk)
            try:
                parsed = json.loads(blob.replace("'", '"'))
            except json.JSONDecodeError as exc:
                logger.debug(f"EntityExtractor: JSON parse failed: {exc}")
                return [], []

        # Entities
        raw_entities = parsed.get("entities", [])
        entities: List[Entity] = []
        for e in raw_entities:
            if isinstance(e, str) and e.strip():
                entities.append(e.strip())

        # Relationships
        raw_rels = parsed.get("relationships", [])
        relations: List[RelationTriple] = []
        for item in raw_rels:
            if (
                isinstance(item, (list, tuple))
                and len(item) == 3
                and all(isinstance(x, str) for x in item)
            ):
                head, label, tail = (x.strip() for x in item)
                if head and label and tail:
                    relations.append((head, label, tail))

        return entities, relations