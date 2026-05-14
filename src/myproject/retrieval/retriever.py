# retrieval/retriever.py
from myproject.kg.graph_store import KnowledgeGraph
from myproject.kg.embeddings import EmbeddingEngine
from myproject.retrieval.triple_matcher import TripleMatcher
from myproject.retrieval.filter import TripleFilter
from myproject.retrieval.query_processor import QueryProcessor
from myproject.retrieval.ppr import run_ppr
from myproject.llm.llm_client import LLMClient
from myproject.config.config_loader import load_config



def _extract_triples_from_graph(graph) -> list:
    """
    Reconstruct the triples list from a loaded NetworkX DiGraph.
 
    During KG construction, KnowledgeGraph.add_triple() builds two things:
      1. The NetworkX graph (nodes + edges with a 'relation' attribute).
      2. A flat list of (subject, relation, object, source_text) tuples
         stored in KnowledgeGraph.triples — this is what TripleMatcher reads.
 
    When we load a graph from disk via persistence.load_kg(), only the
    NetworkX DiGraph is restored from the pickle.  The triples list must be
    rebuilt from the graph edges so TripleMatcher has something to embed.
 
    We only include edges between entity nodes (skipping "similar" and
    "contains" structural edges), which are the true knowledge triples.
    The source_text is recovered from the first passage node that the
    subject entity links to via a "contains" edge, or None if not found.
    """
    triples = []
    for s, o, data in graph.edges(data=True):
        relation = data.get("relation", "")
 
        # Skip structural edges — only entity-to-entity knowledge triples
        if relation in ("similar", "contains"):
            continue
 
        s_type = graph.nodes[s].get("type")
        o_type = graph.nodes[o].get("type")
 
        if s_type == "entity" and o_type == "entity":
            # Try to recover source text from a passage linked to the subject
            source_text = None
            for neighbor in graph.successors(s):
                if graph.nodes[neighbor].get("type") == "passage":
                    source_text = graph.nodes[neighbor].get("text")
                    break
            triples.append((s, relation, o, source_text))
 
    return triples


class HippoRAG:
    def __init__(self, graph=None):
        """
        Initialise HippoRAG.

        Parameters
        ----------
        graph : networkx.DiGraph, optional
            A pre-loaded knowledge graph (e.g. loaded from the models volume
            by persistence.load_kg).  When supplied, the constructor skips the
            disk-load step and uses this graph directly.

            If None (default), the graph is loaded from the path specified in
            config.yaml under kg.save_path — this is the original behaviour
            and remains fully supported.
        """
        self.config = load_config()
        self.kg = KnowledgeGraph()

        if graph is not None:
            # ── Fast path: graph was already loaded by the caller ────────────
            # Assign the NetworkX DiGraph directly into the KnowledgeGraph
            # wrapper.  We also need to rebuild the triples list from the graph
            # edges, because KnowledgeGraph.triples is what TripleMatcher reads.
            self.kg.graph = graph
            self.kg.triples = _extract_triples_from_graph(graph)
        else:
            # ── Default path: load from config save_path ─────────────────────
            self.kg.load(self.config["kg"]["save_path"])

        self.matcher = TripleMatcher(self.kg.triples)
        self.filter = TripleFilter()
        self.processor = QueryProcessor()
        self.embedder = EmbeddingEngine()
        self.llm = LLMClient()

        self.entity_nodes = [
            n for n, d in self.kg.graph.nodes(data=True)
            if d.get("type") == "entity"
        ]
        self.entity_embeddings = (
            self.embedder.encode(self.entity_nodes) if self.entity_nodes else []
        )

        self.passage_nodes = [
            n for n, d in self.kg.graph.nodes(data=True)
            if d.get("type") == "passage"
        ]
        self.passage_texts = [
            self.kg.graph.nodes[n].get("text", "") for n in self.passage_nodes
        ]
        self.passage_embeddings = (
            self.embedder.encode(self.passage_texts) if self.passage_texts else []
        )

    def _match_query_entities(self, entities, threshold=0.75):
        if not entities or not self.entity_nodes:
            return []

        matched = []
        query_embs = self.embedder.encode(entities)

        for qe in query_embs:
            best_score, best_node = -1, None
            for i, ne in enumerate(self.entity_embeddings):
                sim = self.embedder.similarity(qe, ne)
                if sim > best_score:
                    best_score, best_node = sim, self.entity_nodes[i]
            if best_score >= threshold and best_node:
                matched.append(best_node)

        return matched

    def retrieve(self, query):
        mode  = self.config["retrieval"].get("mode", "hipporag")
        top_k = self.config["retrieval"]["top_k"]

        if mode == "dense":
            return self._retrieve_dense(query, top_k)
        return self._retrieve_hipporag(query, top_k)

    def _retrieve_dense(self, query, top_k):
        if not self.passage_texts:
            return []
        query_emb = self.embedder.encode([query])[0]
        scored = [
            (self.embedder.similarity(query_emb, pe), text)
            for pe, text in zip(self.passage_embeddings, self.passage_texts)
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in scored[:top_k]]

    def _retrieve_hipporag(self, query, top_k):
        # Step 1: triple matching
        triples = self.matcher.match(query)

        # Step 2: filtering
        filtered = self.filter.filter(query, triples)

        # Step 3: seeds from triple subjects + query entity extraction
        triple_seeds = list(set([s for s, _, _, _ in filtered]))
        query_entities = self.processor.extract_entities(query)
        entity_seeds = self._match_query_entities(query_entities)
        seeds = list(set(triple_seeds + entity_seeds))

        # Step 4: PPR
        scores = run_ppr(
            self.kg.graph,
            seeds,
            self.config["retrieval"]["ppr_alpha"],
            self.config["retrieval"]["max_iter"]
        )

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        passages = []
        for node, _ in ranked:
            if len(passages) >= top_k:
                break
            node_data = self.kg.graph.nodes[node]
            if node_data.get("type") == "passage":
                passages.append(node_data["text"])

        return passages

    def query(self, query):
        passages = self.retrieve(query)
        context = "\n".join(passages)

        return self.llm.generate(f"""
Answer using context:

{context}

Question:
{query}
""")