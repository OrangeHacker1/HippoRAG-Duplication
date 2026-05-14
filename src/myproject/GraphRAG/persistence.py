# GraphRAG/persistence.py
"""
Persistence for GraphRAG models.

Saves the full GraphRAG state (graph + community summaries + metadata) to
a named model directory on the `kg_data` Docker volume.  The file is named
`base.pkl` to distinguish it from HippoRAG's `graph.pkl` — both can live
in the same model directory:

    /app/models/{name}/
        graph.pkl     ← HippoRAG NetworkX DiGraph
        base.pkl      ← GraphRAG state (this file)
        meta.json     ← shared metadata (written by HippoRAG's persistence.py;
                         we add graphrag_* keys to it)

This design lets a single model directory hold BOTH a HippoRAG index AND a
GraphRAG index built from the same corpus, which is exactly what we need so
the evaluate page can compare the two approaches side-by-side.

Public API
----------
    save_graphrag(state, name, models_dir, metadata=None) -> Path
    load_graphrag(name, models_dir)                        -> dict
    graphrag_exists(name, models_dir)                      -> bool

The `state` dict passed to save_graphrag must have at minimum:
    {
        "graph":       GraphRAGGraph instance,
        "communities": list[list[str]],
        "summaries":   dict[int, dict],   # from CommunitySummarizer
    }
"""

import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Filename inside the model directory — distinct from HippoRAG's graph.pkl
GRAPHRAG_FILENAME = "base.pkl"
META_FILENAME     = "meta.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _model_dir(models_dir: str, name: str) -> str:
    """Return (and guarantee existence of) the model subdirectory."""
    path = os.path.join(models_dir, name)
    os.makedirs(path, exist_ok=True)
    return path


def _validate_name(name: str) -> None:
    if not name:
        raise ValueError("Model name must not be empty.")
    if "/" in name or "\\" in name:
        raise ValueError(f"Model name {name!r} must not contain path separators.")
    if name.startswith("."):
        raise ValueError(f"Model name {name!r} must not start with a dot.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_graphrag(
    state: Dict[str, Any],
    name: str,
    models_dir: str,
    metadata: Optional[Dict] = None,
) -> Path:
    """
    Persist the GraphRAG state dict to ``{models_dir}/{name}/base.pkl``.

    Parameters
    ----------
    state : dict
        Must contain keys: "graph" (GraphRAGGraph), "communities" (list),
        "summaries" (dict).  Any additional keys are also pickled.
    name : str
        Model slug (e.g. "eval_corpus", "musique_50").
    models_dir : str
        Root models directory (from config.yaml kg.models_dir).
    metadata : dict, optional
        Extra fields to merge into meta.json alongside the graph stats.

    Returns
    -------
    Path
        Absolute path to the written base.pkl file.
    """
    _validate_name(name)

    model_dir  = _model_dir(models_dir, name)
    pkl_path   = os.path.join(model_dir, GRAPHRAG_FILENAME)
    meta_path  = os.path.join(model_dir, META_FILENAME)

    # ── Write the pickle ─────────────────────────────────────────────────────
    logger.info(f"Saving GraphRAG state '{name}' -> {pkl_path} ...")
    with open(pkl_path, "wb") as f:
        pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)

    size_kb = os.path.getsize(pkl_path) / 1024
    logger.info(f"GraphRAG '{name}' saved ({size_kb:.1f} KB).")

    # ── Update meta.json (merge with existing if present) ───────────────────
    # Read existing meta (written by HippoRAG's persistence.save_kg, if any)
    existing_meta: Dict = {}
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, encoding="utf-8") as f:
                existing_meta = json.load(f)
        except Exception:
            existing_meta = {}

    graph_wrapper   = state.get("graph")
    community_count = len(state.get("communities", []))
    summary_count   = len(state.get("summaries",   {}))

    graphrag_meta: Dict = {
        "graphrag_saved_at":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "graphrag_node_count":    graph_wrapper.node_count() if graph_wrapper else None,
        "graphrag_edge_count":    graph_wrapper.edge_count() if graph_wrapper else None,
        "graphrag_community_count": community_count,
        "graphrag_summary_count": summary_count,
    }
    if metadata:
        graphrag_meta.update(metadata)

    merged = {**existing_meta, **graphrag_meta}
    # Preserve existing top-level keys (name, saved_at from HippoRAG) if present
    if "name" not in merged:
        merged["name"] = name

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    logger.info(f"GraphRAG metadata written -> {meta_path}")
    return Path(pkl_path)


def load_graphrag(name: str, models_dir: str) -> Dict[str, Any]:
    """
    Load a previously saved GraphRAG state from disk.

    Returns
    -------
    dict
        The state dict that was passed to save_graphrag().

    Raises
    ------
    FileNotFoundError
        If no base.pkl exists under models_dir/name/.
    RuntimeError
        If the pickle cannot be deserialised.
    """
    pkl_path = os.path.join(models_dir, name, GRAPHRAG_FILENAME)

    if not os.path.isfile(pkl_path):
        raise FileNotFoundError(
            f"No GraphRAG model named '{name}' found at '{pkl_path}'. "
            "Build one using POST /api/graphrag/train."
        )

    logger.info(f"Loading GraphRAG '{name}' from '{pkl_path}' ...")
    try:
        with open(pkl_path, "rb") as f:
            state = pickle.load(f)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to deserialise GraphRAG '{name}' from '{pkl_path}': {exc}"
        ) from exc

    graph_wrapper = state.get("graph")
    if graph_wrapper:
        logger.info(
            f"GraphRAG '{name}' loaded: "
            f"{graph_wrapper.node_count()} nodes, "
            f"{graph_wrapper.edge_count()} edges, "
            f"{len(state.get('communities', []))} communities."
        )
    return state


def graphrag_exists(name: str, models_dir: str) -> bool:
    """Return True if a saved GraphRAG model exists for *name*."""
    pkl_path = os.path.join(models_dir, name, GRAPHRAG_FILENAME)
    return os.path.isfile(pkl_path)


def list_graphrag_models(models_dir: str) -> list:
    """
    Return metadata for every model directory that has a base.pkl.

    Returns
    -------
    list[dict]
        Sorted alphabetically by name. Each dict has keys:
            name, graphrag_saved_at, graphrag_node_count,
            graphrag_edge_count, graphrag_community_count, graphrag_summary_count
    """
    os.makedirs(models_dir, exist_ok=True)
    models = []

    try:
        entries = sorted(os.scandir(models_dir), key=lambda e: e.name)
    except PermissionError as exc:
        logger.warning(f"Cannot read models_dir '{models_dir}': {exc}")
        return []

    for entry in entries:
        if not entry.is_dir():
            continue
        pkl_path = os.path.join(entry.path, GRAPHRAG_FILENAME)
        if not os.path.isfile(pkl_path):
            continue

        meta_path = os.path.join(entry.path, META_FILENAME)
        meta: Dict = {}
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}

        models.append({
            "name":                       entry.name,
            "graphrag_saved_at":          meta.get("graphrag_saved_at",          "unknown"),
            "graphrag_node_count":        meta.get("graphrag_node_count"),
            "graphrag_edge_count":        meta.get("graphrag_edge_count"),
            "graphrag_community_count":   meta.get("graphrag_community_count"),
            "graphrag_summary_count":     meta.get("graphrag_summary_count"),
        })

    return models