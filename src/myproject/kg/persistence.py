"""
src/myproject/kg/persistence.py
================================
Save, load, and list HippoRAG knowledge graph models.

All KG models are stored on the `kg_data` Docker named volume, which is
mounted inside the container at the path specified by `kg.models_dir` in
config.yaml (default: /app/models).  Named volumes survive
`docker compose down/up` indefinitely — they are only deleted by:

    docker volume rm <project>_kg_data                    (entire volume)
    docker exec myproject_app rm -rf /app/models/<name>   (one model)

Directory layout
----------------
    {models_dir}/
        {name}/
            graph.pkl   <- the NetworkX DiGraph (pickled)
            meta.json   <- build metadata (timestamp, node/edge/doc counts)

Using a subdirectory per model (rather than {name}.pkl) leaves room to store
future companion files (embedding cache, build log) without naming conflicts.

os.makedirs is used throughout instead of Path.mkdir so that the directory
is always created even if it was not pre-created by the Docker volume mount
or by a git-tracked folder.  All calls use exist_ok=True so they are
idempotent — safe to call multiple times.

Public API
----------
    save_kg(graph, name, models_dir, metadata=None) -> Path
    load_kg(name, models_dir)                       -> graph
    list_saved_kgs(models_dir)                      -> list[dict]
"""

import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _model_dir(models_dir: str, name: str) -> str:
    """
    Return the absolute path of the directory for a named model and
    guarantee the directory exists on disk.

    Uses os.makedirs so the call is safe whether or not the parent
    directories were created by Docker, git, or a previous run.
    """
    path = os.path.join(models_dir, name)
    os.makedirs(path, exist_ok=True)
    return path


def _validate_name(name: str) -> None:
    """
    Reject model names that could cause path-traversal or filesystem issues.

    Valid names: non-empty, no forward/back slashes, no leading dot.
    Examples of valid names: "eval_corpus", "latest", "musique-50".
    """
    if not name:
        raise ValueError("Model name must not be empty.")
    if "/" in name or "\\" in name:
        raise ValueError(
            f"Model name {name!r} must not contain path separators (/ or \\)."
        )
    if name.startswith("."):
        raise ValueError(
            f"Model name {name!r} must not start with a dot."
        )


# ── Public API ───────────────────────────────────────────────────────────────

def save_kg(
    graph: Any,
    name: str,
    models_dir: str,
    metadata: dict | None = None,
) -> Path:
    """
    Persist a NetworkX knowledge graph to the models directory.

    Parameters
    ----------
    graph :
        The NetworkX DiGraph produced by KGBuilder.build().
    name :
        Slug used as the folder name, e.g. "eval_corpus" or "musique_50".
        Must be a simple filesystem-safe string (no slashes, no leading dot).
    models_dir :
        Root directory for saved models.  Inside Docker this is /app/models,
        which is mounted from the `kg_data` named volume.
    metadata :
        Optional extra key/value pairs to store in meta.json alongside the
        graph, e.g. {"doc_count": 10, "dataset": "eval_corpus"}.
        Always merged with auto-computed fields (saved_at, node_count, etc.).

    Returns
    -------
    Path
        Absolute path to the written graph.pkl file.

    Raises
    ------
    ValueError
        If `name` is invalid (empty, contains slashes, starts with dot).
    OSError
        If the write fails (disk full, permission denied, etc.).
    """
    _validate_name(name)

    # Ensure the model directory exists (idempotent).
    model_dir  = _model_dir(models_dir, name)
    graph_path = os.path.join(model_dir, "graph.pkl")
    meta_path  = os.path.join(model_dir, "meta.json")

    # ── Write the graph pickle ───────────────────────────────────────────────
    logger.info(f"Saving KG '{name}' -> {graph_path} ...")
    with open(graph_path, "wb") as f:
        pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)

    size_kb = os.path.getsize(graph_path) / 1024
    logger.info(f"KG '{name}' saved ({size_kb:.1f} KB).")

    # ── Write metadata ───────────────────────────────────────────────────────
    # Always compute node/edge counts from the graph itself so meta.json
    # is always accurate even if the caller does not pass metadata.
    node_count = graph.number_of_nodes() if hasattr(graph, "number_of_nodes") else None
    edge_count = graph.number_of_edges() if hasattr(graph, "number_of_edges") else None

    meta: dict = {
        "name":       name,
        "saved_at":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "node_count": node_count,
        "edge_count": edge_count,
    }
    if metadata:
        # Caller-supplied fields are merged in; they can override auto fields
        # if needed (e.g. to record doc_count, dataset name, build duration).
        meta.update(metadata)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"Metadata written -> {meta_path}")
    return Path(graph_path)


def load_kg(name: str, models_dir: str) -> Any:
    """
    Load a previously saved knowledge graph from disk.

    Parameters
    ----------
    name :
        The model slug used when save_kg() was called.
    models_dir :
        Root directory for saved models (from config.yaml kg.models_dir).

    Returns
    -------
    Any
        The deserialized NetworkX DiGraph.

    Raises
    ------
    FileNotFoundError
        If no model with that name exists under models_dir.
    RuntimeError
        If the pickle exists but cannot be deserialized (corrupt file,
        incompatible Python/pickle version, etc.).
    """
    # Build the expected path without creating any directories — we are
    # reading, not writing.
    graph_path = os.path.join(models_dir, name, "graph.pkl")

    if not os.path.isfile(graph_path):
        # Give a helpful message that includes what models ARE available.
        available = [m["name"] for m in list_saved_kgs(models_dir)]
        raise FileNotFoundError(
            f"No saved KG named '{name}' found at '{graph_path}'. "
            f"Available models: {available or ['(none)']}"
        )

    logger.info(f"Loading KG '{name}' from '{graph_path}' ...")
    try:
        with open(graph_path, "rb") as f:
            graph = pickle.load(f)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to deserialize KG '{name}' from '{graph_path}': {exc}"
        ) from exc

    logger.info(
        f"KG '{name}' loaded: "
        f"{graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges."
    )
    return graph


def list_saved_kgs(models_dir: str) -> list[dict]:
    """
    Return metadata for every valid saved KG in models_dir.

    A directory is considered a valid saved model if it contains graph.pkl.
    Directories without graph.pkl are silently skipped (could be temp files,
    partial writes, or unrelated directories).

    Parameters
    ----------
    models_dir :
        Root directory for saved models (from config.yaml kg.models_dir).

    Returns
    -------
    list[dict]
        Sorted (alphabetically by name) list of dicts, each with keys:
            name        : str
            saved_at    : str   (ISO timestamp or "unknown")
            node_count  : int | None
            edge_count  : int | None
            doc_count   : int | None

        Returns an empty list if models_dir does not exist or is empty.
    """
    # Ensure the directory exists so callers never crash on a fresh volume.
    # os.makedirs with exist_ok=True is a no-op if it already exists.
    os.makedirs(models_dir, exist_ok=True)

    models = []

    # os.scandir is more efficient than iterdir() for large directories and
    # gives us DirEntry objects with .is_dir() without extra stat calls.
    try:
        entries = sorted(os.scandir(models_dir), key=lambda e: e.name)
    except PermissionError as exc:
        logger.warning(f"Cannot read models_dir '{models_dir}': {exc}")
        return []

    for entry in entries:
        # Only consider subdirectories (each model lives in its own folder)
        if not entry.is_dir():
            continue

        graph_pkl = os.path.join(entry.path, "graph.pkl")
        if not os.path.isfile(graph_pkl):
            # Not a model directory — skip silently
            continue

        # Read metadata; fall back to minimal info if meta.json is absent
        # or corrupt (e.g. a model saved by an older version of this code).
        meta_path = os.path.join(entry.path, "meta.json")
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception as exc:
                logger.warning(
                    f"Could not read meta.json for model '{entry.name}': {exc}. "
                    "Falling back to minimal info."
                )
                meta = {}
        else:
            meta = {}

        models.append({
            "name":       entry.name,
            "saved_at":   meta.get("saved_at",   "unknown"),
            "node_count": meta.get("node_count"),
            "edge_count": meta.get("edge_count"),
            "doc_count":  meta.get("doc_count"),
        })

    return models