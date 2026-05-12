"""
src/myproject/api/app.py
========================
FastAPI application for HippoRAG.
 
Endpoints
---------
GET  /                  → Query UI (index.html)
GET  /evaluate          → Evaluation UI (evaluate.html)
GET  /train             → Training & model-management UI (train.html)
 
GET  /health            → Liveness probe (used by Docker health check)
 
POST /api/query         → Answer a question using the loaded KG
POST /api/evaluate      → Run the full evaluation pipeline
 
GET  /api/kg/status     → Is a KG loaded? How many nodes/edges?
GET  /api/kg/list       → List all saved KGs on the Docker volume
POST /api/train         → Build a KG; stream progress via SSE
POST /api/kg/load       → Hot-load a saved KG (no server restart needed)
 
Startup / persistence
---------------------
On startup the lifespan function attempts to load a KG in this order:
 
  1. `active_model` key in config.yaml  → explicit override, always wins.
  2. `auto_save_name` key in config.yaml (default "latest") → loads whatever
     the last successful build saved, so a fresh `docker compose up` after
     a previous build is immediately ready.
  3. Graceful warning — app starts without a KG; the user can load or build
     one from the /train page.
 
Saved KGs live in the `kg_data` Docker named volume (mounted at models_dir,
typically /app/models inside the container).  They survive
`docker compose down/up`.  The only way to permanently delete a save is:
 
    docker exec myproject_app rm -rf /app/models/<name>
  or
    docker volume rm <project>_kg_data


Dataset formats supported by POST /api/train
--------------------------------------------
  "eval_corpus"  — the bundled 10-doc Python corpus (eval_dataset.CORPUS)
 
  "custom"       — caller sends a plain list of strings in the `documents`
                   field of the JSON body; one string = one passage
 
  "json_file"    — caller sends a `json_path` pointing to a JSON file that
                   is already on the container filesystem.  Two sub-formats
                   are auto-detected:
 
                   Format A — plain string array (original custom corpus):
                       ["passage one text", "passage two text", ...]
 
                   Format B — object array with title + text keys
                   (the external dataset format used by MuSiQue etc.):
                       [
                         {"title": "Teutberga", "text": "Teutberga ...", "idx": 0},
                         {"title": "Theodred II", "text": "Theodred II ...", "idx": 1},
                         ...
                       ]
 
                   For Format B the loader prepends the title to the text so
                   the LLM sees "Teutberga: Teutberga was a queen ..." — this
                   gives triple extraction more context and produces better
                   entity names in the knowledge graph.
 
                   Entries with empty or whitespace-only text are silently
                   skipped in both formats.
    
"""

# ── Standard library ────────────────────────────────────────────────────────
import uuid
import requests as http_requests
from contextlib import asynccontextmanager
from pathlib import Path
import queue
import json             # serialise SSE payloads
import os               # makedirs — ensure models_dir exists even if not pre-created
import asyncio          # run blocking KG build without blocking the event loop

# ── Third-party ─────────────────────────────────────────────────────────────
import requests as http_requests
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
#import asyncio                          # for running blocking build in thread
#from fastapi.responses import StreamingResponse  # for SSE progress stream

# ── Internal ─────────────────────────────────────────────────────────────────

from myproject.api.logger import get_logger
from myproject.retrieval.retriever import HippoRAG
from myproject.eval.metrics import recall_at_k, exact_match, f1_score
from myproject.data.eval_dataset import QUESTIONS, CORPUS

# ── New imports to add at the top of src/myproject/api/app.py ──────────────

from myproject.kg.persistence import save_kg, load_kg, list_saved_kgs
from myproject.kg.builder import KGBuilder       # triggers the actual build
from myproject.config.config_loader import load_config  # reads config.yaml
#from myproject.data.eval_dataset import CORPUS   # the bundled document list

# ---------------------------------------------------------------------------
logger = get_logger(__name__)


# Global RAG instance.  Set during lifespan startup and hot-swapped by
# /api/train and /api/kg/load.  None means no KG is loaded yet.
rag: HippoRAG | None = None


# ════════════════════════════════════════════════════════════════════════════
#  DATASET LOADING HELPER
# ════════════════════════════════════════════════════════════════════════════
 
def load_docs_from_json_file(json_path: str) -> list[str]:
    """
    Load a list of plain-text passages from a JSON file on disk.
 
    Supports two formats automatically — the format is detected at runtime
    by inspecting the type of the first element, with a try/except around
    every step so bad data never crashes the build.
 
    Format A — plain string array
    ------------------------------
    The simplest format: a JSON array where each element is already a string.
 
        ["Marie Curie was born in Warsaw.", "She won the Nobel Prize...", ...]
 
    Each non-empty string becomes one passage fed to KGBuilder.
 
    Format B — object array with "title" and "text" keys
    -----------------------------------------------------
    Used by external datasets (MuSiQue, 2WikiMultiHop, HotpotQA, etc.).
    The "idx" field is ignored — it is just an ordering artifact.
 
        [
          {"title": "Teutberga",  "text": "Teutberga was a queen ...", "idx": 0},
          {"title": "Theodred II","text": "Theodred II was a medieval ...", "idx": 1},
          ...
        ]
 
    The title is prepended to the text as "Title: text" so the LLM sees the
    full context during triple extraction.  This produces better entity names
    in the knowledge graph (e.g. "Teutberga" rather than "she").
 
    Entries whose "text" value is empty or whitespace-only are skipped in
    both formats.
 
    Parameters
    ----------
    json_path : str
        Absolute or relative path to the JSON file on the container
        filesystem.  Must be readable by the app process.
 
    Returns
    -------
    list[str]
        Non-empty passage strings ready to pass to KGBuilder.build().
 
    Raises
    ------
    FileNotFoundError
        If json_path does not exist on disk.
    ValueError
        If the file cannot be parsed as JSON, is not a list, or contains
        entries in an unrecognised format.
    """
    # ── Step 1: verify the file exists ──────────────────────────────────────
    # Give an explicit FileNotFoundError rather than letting open() raise a
    # confusing OSError with a long traceback.
    if not os.path.isfile(json_path):
        raise FileNotFoundError(
            f"Dataset file not found: '{json_path}'. "
            "Make sure the path is correct and the file is accessible inside "
            "the container (check your Docker volume mounts)."
        )
 
    # ── Step 2: parse the JSON ───────────────────────────────────────────────
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse '{json_path}' as JSON: {exc}. "
            "Make sure the file is valid JSON."
        ) from exc
 
    # ── Step 3: the top-level value must be a list ───────────────────────────
    if not isinstance(raw, list):
        raise ValueError(
            f"Expected a JSON array at the top level of '{json_path}', "
            f"but got {type(raw).__name__}. "
            "The file must be a list of strings or a list of objects "
            "with 'title' and 'text' fields."
        )
 
    if len(raw) == 0:
        raise ValueError(f"Dataset file '{json_path}' is an empty array.")
 
    # ── Step 4: detect the format from the first non-None element ───────────
    first = next((item for item in raw if item is not None), None)
    if first is None:
        raise ValueError(f"Dataset file '{json_path}' contains only null entries.")
 
    docs: list[str] = []
 
    # ── Format A: plain string array ────────────────────────────────────────
    if isinstance(first, str):
        for i, item in enumerate(raw):
            try:
                if not isinstance(item, str):
                    # Mixed-type array — skip non-strings with a warning logged
                    # rather than crashing the whole build.
                    logger.warning(
                        f"json_file loader: item {i} is {type(item).__name__}, "
                        "expected str — skipping."
                    )
                    continue
                text = item.strip()
                if text:
                    docs.append(text)
            except Exception as exc:
                logger.warning(f"json_file loader: error reading item {i}: {exc} — skipping.")
 
    # ── Format B: object array with title + text ─────────────────────────────
    elif isinstance(first, dict):
        for i, item in enumerate(raw):
            try:
                if not isinstance(item, dict):
                    logger.warning(
                        f"json_file loader: item {i} is {type(item).__name__}, "
                        "expected dict — skipping."
                    )
                    continue
 
                # "text" is required; "title" is optional but improves triples
                text = item.get("text", "")
                if not isinstance(text, str):
                    text = str(text) if text is not None else ""
                text = text.strip()
 
                if not text:
                    # Empty passage — nothing for the LLM to extract
                    continue
 
                title = item.get("title", "")
                if not isinstance(title, str):
                    title = str(title) if title is not None else ""
                title = title.strip()
 
                # Prepend title so the LLM sees "Teutberga: Teutberga was a queen ..."
                # This helps triple extraction produce named entities rather than
                # pronouns ("she") as subject nodes.
                if title:
                    passage = f"{title}: {text}"
                else:
                    passage = text
 
                docs.append(passage)
 
            except Exception as exc:
                logger.warning(f"json_file loader: error reading item {i}: {exc} — skipping.")
 
    # ── Unrecognised format ──────────────────────────────────────────────────
    else:
        raise ValueError(
            f"Unrecognised item type in '{json_path}': "
            f"first element is {type(first).__name__}. "
            "Expected either a list of strings (Format A) or a list of dicts "
            "with 'title' and 'text' keys (Format B)."
        )
 
    if not docs:
        raise ValueError(
            f"No non-empty passages found in '{json_path}'. "
            "Check that the file has content and is in the correct format."
        )
 
    return docs



# ════════════════════════════════════════════════════════════════════════════
#  LIFESPAN  (startup / shutdown)
# ════════════════════════════════════════════════════════════════════════════

# ── Lifespan (startup / shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup:
      1. Read config.yaml to see if an active_model is configured.
      2. If yes, load that saved KG from the models volume automatically.
      3. If no, try the default HippoRAG() constructor (builds from scratch or fails gracefully).

    This means the grader can set active_model: eval_corpus in config.yaml
    and the app will be immediately ready after `docker compose up` with no
    manual load step needed.
    """
    global rag
    try:
        #rag = HippoRAG()
        #logger.info("HippoRAG loaded successfully.")
        
        cfg = load_config()
        kg_cfg      = cfg.get("kg", {})
        models_dir  = kg_cfg.get("models_dir", "/app/models")
        active_model = kg_cfg.get("active_model")          # explicit override
        default_name = kg_cfg.get("auto_save_name", "latest")  # fallback


        # Ensure the models directory exists.
        # The Docker volume is created empty; os.makedirs is idempotent.
        os.makedirs(models_dir, exist_ok=True)


        # ── Level 1: explicit active_model ──────────────────────────────────
        if active_model:
            # Load the pre-trained KG specified in config.yaml
            logger.info(f"Config specifies active_model='{active_model}'. Loading ...")
            graph = load_kg(name=active_model, models_dir=models_dir)
            rag = HippoRAG(graph=graph)
            rag._active_model_name = active_model
            logger.info(f"Pre-trained KG '{active_model}' loaded on startup.")
        
         # ── Level 2: try auto_save_name ("latest" by default) ───────────────
        else:
            try:
                logger.info(
                    f"Startup: no active_model set; trying default '{default_name}' ..."
                )
                graph = load_kg(name=default_name, models_dir=models_dir)
                rag = HippoRAG(graph=graph)
                rag._active_model_name = default_name
                logger.info(
                    f"Startup: KG '{default_name}' loaded from previous build."
                )
            except FileNotFoundError:
                # ── Level 3: no KG at all — start empty ─────────────────────
                logger.warning(
                    f"Startup: no saved KG found (tried '{default_name}'). "
                    "Starting without a knowledge graph. "
                    "Open /train to build or load one."
                )

    except Exception as e:
        logger.warning(f"Could not load HippoRAG on startup: {e}. Build the KG first. Use /train to build or load one.")
    yield # <- app is live here; everything below runs on shutdown (nothing needed)

# ── App + templates ──────────────────────────────────────────────────────────

app = FastAPI(title="HippoRAG", lifespan=lifespan)

# Templates directory sits next to this file: src/myproject/api/templates/
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


class QueryRequest(BaseModel):
    question: str

class TrainRequest(BaseModel):
    """
    Body for POST /api/train.
 
    dataset_name : str
        Which dataset to build from.  One of:
          "eval_corpus" — use the bundled 10-doc corpus (eval_dataset.CORPUS)
          "custom"      — caller supplies plain strings in `documents`
          "json_file"   — caller supplies a path to a JSON file in `json_path`
 
    documents : list[str]
        Raw document strings.  Only used when dataset_name == "custom".
 
    json_path : str
        Absolute path to a JSON dataset file on the container filesystem.
        Only used when dataset_name == "json_file".
        Supports two JSON formats — see load_docs_from_json_file() for details.
 
    save_as : str
        Slug for the saved model folder (e.g. "eval_corpus", "musique_50").
        Defaults to the config auto_save_name ("latest").
    """
    dataset_name: str = "eval_corpus"
    documents: list[str] = []
    json_path: str = ""
    save_as: str = "latest"
 
 
class LoadRequest(BaseModel):
    """Body for POST /api/kg/load."""
    name: str  # model slug, e.g. "eval_corpus"



# ════════════════════════════════════════════════════════════════════════════
#  UTILITY PAGES
# ════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok"}



# ════════════════════════════════════════════════════════════════════════════
#  PAGE ROUTES  (serve HTML templates)
# ══════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Query UI — ask questions against the loaded KG."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/evaluate", response_class=HTMLResponse)
def evaluate_page(request: Request):
    """Evaluation UI — run the full eval pipeline and display metrics."""
    return templates.TemplateResponse("evaluate.html", {"request": request})

@app.get("/train", response_class=HTMLResponse)
def train_page(request: Request):
    """
    Training & model-management UI.
 
    Panel 1 — Status:  current KG stats (polls /api/kg/status)
    Panel 2 — Train:   pick a dataset, trigger a build, watch SSE log
    Panel 3 — Load:    list saved models, hot-load one in seconds
    """
    return templates.TemplateResponse("train.html", {"request": request})



# ════════════════════════════════════════════════════════════════════════════
#  QUERY  (existing, unchanged)
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/query")
def query(body: QueryRequest, request: Request):
    """
    Answer a question using the currently loaded knowledge graph.
 
    If no KG is loaded yet, attempt a one-time lazy load of the default
    model before giving up.  This mirrors the startup Level 2 fallback so
    the endpoint stays robust even if startup failed silently.
    """
    global rag
    request_id = str(uuid.uuid4())

    # Reject empty queries before touching the KG
    if not body.question.strip():
        logger.info("Empty query rejected.", extra={"request_id": request_id})
        raise HTTPException(status_code=422, detail="Query must not be empty.")


     # ── Lazy load fallback ───────────────────────────────────────────────────
    # If rag is still None (startup fallback failed), try once more.
    # This handles the case where the volume was empty at startup but the user
    # built a KG and then the container restarted before they could /api/kg/load.
    if rag is None:
        try:
            cfg = load_config()
            kg_cfg      = cfg.get("kg", {})
            models_dir  = kg_cfg.get("models_dir", "/app/models")
            default_name = kg_cfg.get("auto_save_name", "latest")
            graph = load_kg(name=default_name, models_dir=models_dir)
            rag = HippoRAG(graph=graph)
            rag._active_model_name = default_name
            logger.info(
                f"Lazy-loaded KG '{default_name}' on first query.",
                extra={"request_id": request_id},
            )
        except Exception as exc:
            logger.warning(
                f"Lazy load failed: {exc}",
                extra={"request_id": request_id},
            )


    # If still None after the attempt, the KG genuinely doesn't exist yet
    if rag is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Knowledge graph not loaded. "
                "Open /train to build or load one."
            ),
        )

    logger.info(f"Query received: {body.question}", extra={"request_id": request_id})

    try:
        passages = rag.retrieve(body.question)
        context  = "\n".join(passages)
        answer   = rag.llm.generate(
            f"Answer using context:\n\n{context}\n\nQuestion:\n{body.question}"
        )
        logger.info("Query answered successfully.", extra={"request_id": request_id})
        return {"answer": answer, "passages": passages, "request_id": request_id}
 
    except http_requests.exceptions.ConnectionError:
        logger.error("LLM unreachable.", extra={"request_id": request_id})
        raise HTTPException(
            status_code=503,
            detail="The language model is currently unavailable. Please try again later.",
        )
    except http_requests.exceptions.ConnectTimeout:
        logger.error("LLM connection timed out.", extra={"request_id": request_id})
        raise HTTPException(
            status_code=503,
            detail="The language model is currently unavailable. Please try again later.",
        )




# ════════════════════════════════════════════════════════════════════════════
#  EVALUATION  (existing, unchanged)
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/evaluate")
def evaluate():
    """
    Run the full evaluation pipeline over the bundled multi-hop test dataset.
 
    Returns per-question EM, F1, and Recall@{1,2,5}, plus aggregate scores.
    """
    request_id = str(uuid.uuid4())
 
    if rag is None:
        raise HTTPException(
            status_code=503,
            detail="Knowledge graph not loaded. Open /train to build or load one.",
        )
 
    logger.info("Evaluation started.", extra={"request_id": request_id})
 
    recall_ks     = [1, 2, 5]
    recall_totals = {k: 0.0 for k in recall_ks}
    em_total      = 0.0
    f1_total      = 0.0
    results       = []
 
    for item in QUESTIONS:
        question     = item["question"]
        gold_docs    = item["gold_docs"]
        gold_answers = item["gold_answers"]
 
        try:
            passages = rag.retrieve(question)
            context  = "\n".join(passages)
            answer   = rag.llm.generate(
                f"Answer using context:\n\n{context}\n\nQuestion:\n{question}"
            )
        except Exception as exc:
            logger.error(
                f"Eval query failed: {exc}",
                extra={"request_id": request_id},
            )
            continue
 
        em        = exact_match(answer, gold_answers)
        f1        = f1_score(answer, gold_answers)
        em_total += em
        f1_total += f1
 
        recalls = {}
        for k in recall_ks:
            r = recall_at_k(passages, gold_docs, k)
            recall_totals[k] += r
            recalls[f"Recall@{k}"] = round(r, 4)
 
        results.append({
            "question": question,
            "answer":   answer,
            "passages": passages,
            "em":       round(em, 4),
            "f1":       round(f1, 4),
            **recalls,
        })
 
    n         = len(QUESTIONS)
    aggregate = {f"Recall@{k}": round(recall_totals[k] / n, 4) for k in recall_ks}
    aggregate["ExactMatch"] = round(em_total / n, 4)
    aggregate["F1"]         = round(f1_total / n, 4)
 
    logger.info(
        f"Evaluation complete: {aggregate}",
        extra={"request_id": request_id},
    )
    return {"aggregate": aggregate, "results": results, "request_id": request_id}

#
#       Train and Load
#

# ── New Pydantic request models ─────────────────────────────────────────────
"""
class TrainRequest(BaseModel):
    " ""
    Body for POST /api/train.

    Fields:
        dataset_name:  Which dataset to build from.
                       "eval_corpus"  → the bundled CORPUS from eval_dataset.py
                       "custom"       → use the `documents` field below
        documents:     Only used when dataset_name == "custom".
                       A list of raw document strings to index.
        save_as:       Slug name to save the trained KG under (e.g. "my_corpus").
                       If omitted, defaults to "latest".
    " ""
    dataset_name: str = "eval_corpus"
    documents: list[str] = []
    save_as: str = "latest"


class LoadRequest(BaseModel):
    " ""Body for POST /api/kg/load." ""
    name: str  # The model slug to load, e.g. "eval_corpus"
"""


# ════════════════════════════════════════════════════════════════════════════
#  KG STATUS  —  GET /api/kg/status
# ════════════════════════════════════════════════════════════════════════════
 
@app.get("/api/kg/status")
def kg_status():
    """
    Report whether a KG is currently loaded and its basic graph stats.
 
    The /train page polls this on load to populate the status badge without
    requiring any user interaction.
 
    Response schema:
        {
            "loaded":       bool,
            "node_count":   int | null,
            "edge_count":   int | null,
            "active_model": str | null
        }
    """
    # Guard: rag not loaded at all
    if rag is None:
        return {
            "loaded":       False,
            "node_count":   None,
            "edge_count":   None,
            "active_model": None,
        }
 
    # Guard: rag exists but KG sub-object is missing (shouldn't happen, but safe)
    if not hasattr(rag, "kg") or rag.kg is None:
        return {
            "loaded":       False,
            "node_count":   None,
            "edge_count":   None,
            "active_model": getattr(rag, "_active_model_name", None),
        }
 
    graph = rag.kg.graph  # the underlying NetworkX DiGraph
    return {
        "loaded":       True,
        "node_count":   graph.number_of_nodes(),
        "edge_count":   graph.number_of_edges(),
        "active_model": getattr(rag, "_active_model_name", "unknown"),
    }


# ════════════════════════════════════════════════════════════════════════════
#  KG LIST  —  GET /api/kg/list
# ════════════════════════════════════════════════════════════════════════════
 
@app.get("/api/kg/list")
def kg_list():
    """
    Return all KG models saved on the Docker volume.
 
    The /train page uses this to populate the Load panel table so the user
    can pick a model by clicking a button rather than typing a name.
 
    Response schema:
        {
            "models": [
                {
                    "name":       str,
                    "saved_at":   str,   # ISO timestamp or "unknown"
                    "node_count": int | null,
                    "edge_count": int | null,
                    "doc_count":  int | null
                },
                ...
            ]
        }
    """
    cfg        = load_config()
    models_dir = cfg.get("kg", {}).get("models_dir", "/app/models")
 
    # Ensure the directory exists before trying to list it.
    # This prevents a crash on a truly fresh volume before the first build.
    os.makedirs(models_dir, exist_ok=True)
 
    return {"models": list_saved_kgs(models_dir)}


# ════════════════════════════════════════════════════════════════════════════
#  TRAIN  —  POST /api/train   (SSE streaming)
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/train")
async def train(body: TrainRequest, request: Request):
    """
    Trigger a KG build and stream progress back to the browser via SSE.
 
    Why SSE instead of a plain JSON response
    -----------------------------------------
    KG construction involves one LLM call per document (triple extraction),
    plus embedding computation and graph linking — easily 30 seconds to
    several minutes depending on corpus size and LLM latency.  Without
    streaming the browser would show a frozen spinner with no feedback.
 
    SSE (Server-Sent Events) lets the server push newline-delimited JSON
    objects to the browser over a single long-lived HTTP response.  The
    client reads them with the Fetch Streams API (no WebSocket needed).
 
    SSE message format  — each message is:
        data: {"type": "...", "message": "..."}\n\n
 
    type values:
        "log"   — informational progress line; append to the log box
        "done"  — build succeeded; includes node_count, edge_count, model_name
        "error" — build failed; includes the exception message

    dataset_name values handled here:
        "eval_corpus" — bundled corpus, no extra fields needed
        "custom"      — body.documents must be a non-empty list of strings
        "json_file"   — body.json_path must point to a readable JSON file;
                        format is auto-detected (see load_docs_from_json_file)    
 
    Implementation notes
    --------------------
    The KGBuilder.build() call is blocking (CPU + LLM I/O).  We run it in
    a thread-pool executor via asyncio.get_event_loop().run_in_executor() so
    the FastAPI event loop stays responsive to other requests during the build.
 
    KGBuilder accepts an optional progress_callback(msg: str).  We put those
    messages onto a thread-safe queue.Queue and drain it every 300 ms while
    the build runs, forwarding each line to the browser.
    """
    global rag
 
    request_id = str(uuid.uuid4())
    cfg        = load_config()
    kg_cfg     = cfg.get("kg", {})
    models_dir = kg_cfg.get("models_dir", "/app/models")
 
    # Ensure the destination directory exists before the build tries to write.
    os.makedirs(models_dir, exist_ok=True)
 
    # ── Resolve document list ────────────────────────────────────────────────
    # Each branch produces a plain list[str] of passages.
    # All three branches feed the same KGBuilder below — nothing else changes.
    if body.dataset_name == "eval_corpus":
        # Use the bundled 10-document evaluation corpus (scientists dataset)
        docs = list(CORPUS)
 
    elif body.dataset_name == "custom":
        # Caller supplied raw documents; strip blanks
        docs = [d.strip() for d in body.documents if d.strip()]
        if not docs:
            raise HTTPException(
                status_code=422,
                detail="No documents provided for custom dataset.",
            )
        
    elif body.dataset_name == "json_file":
        # ── JSON file on the container filesystem ────────────────────────────
        # load_docs_from_json_file() handles both:
        #   Format A: ["passage one", "passage two", ...]
        #   Format B: [{"title": "...", "text": "...", "idx": N}, ...]
        # It raises FileNotFoundError or ValueError with a clear message on
        # any problem, which we catch and turn into a 422 for the client.
        json_path = body.json_path.strip()
        if not json_path:
            raise HTTPException(
                status_code=422,
                detail=(
                    "json_path is required when dataset_name is 'json_file'. "
                    "Provide the absolute path to the JSON file inside the container, "
                    "e.g. /app/data/musique_corpus.json"
                ),
            )
        try:
            docs = load_docs_from_json_file(json_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        
    
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown dataset_name: {body.dataset_name!r}. "
                   "Use 'eval_corpus' or 'custom'.",
        )
 
    save_name = body.save_as.strip() or kg_cfg.get("auto_save_name", "latest")
 
    # ── SSE generator ────────────────────────────────────────────────────────
    async def event_stream():
        """
        Async generator that:
          1. Starts the KGBuilder in a thread-pool executor.
          2. Polls a Queue for progress messages every 300 ms.
          3. Yields each message formatted as an SSE data line.
          4. On completion, saves the graph, hot-swaps rag, emits "done".
          5. On exception, emits "error".
        """
        def _emit(type_: str, message: str, **extra) -> str:
            """Serialise a dict as a JSON SSE data line (ends with double newline)."""
            payload = json.dumps({"type": type_, "message": message, **extra})
            return f"data: {payload}\n\n"
 
        # ── Kick off ──
        yield _emit(
            "log",
            f"[{request_id}] Starting KG build: "
            f"dataset='{body.dataset_name}', docs={len(docs)}, save_as='{save_name}'",
        )
        yield _emit(
            "log",
            f"Save target: {models_dir}/{save_name}/graph.pkl  (Docker volume kg_data)",
        )
 
        try:
            loop      = asyncio.get_event_loop()
            log_queue: queue.Queue = queue.Queue()
 
            def _progress(msg: str):
                """Called by KGBuilder from the worker thread."""
                log_queue.put(msg)
 
            def _build():
                """Blocking build — runs in thread pool."""
                builder = KGBuilder(progress_callback=_progress)
                return builder.build(docs)
 
            yield _emit("log", "Initialising KGBuilder ...")
 
            # Run the blocking build without freezing the event loop
            future = loop.run_in_executor(None, _build)
 
            # ── Drain the queue while the build runs ──
            while not future.done():
                await asyncio.sleep(0.3)
                while not log_queue.empty():
                    yield _emit("log", log_queue.get_nowait())
 
            # ── Drain any remaining messages after the build finishes ──
            while not log_queue.empty():
                yield _emit("log", log_queue.get_nowait())
 
            # ── Retrieve result (re-raises any exception from the thread) ──
            new_graph = await future
 
            # ── Save to volume ──
            yield _emit("log", f"Build complete. Saving model as '{save_name}' ...")
            save_kg(
                graph=new_graph,
                name=save_name,
                models_dir=models_dir,
                metadata={
                    "doc_count": len(docs),
                    "dataset":   body.dataset_name,
                },
            )

            # ── Point config save_path at the newly saved graph ──
            #yield _emit("log", "Loading new KG into memory ...")
            yield _emit("log", f"Saved → {models_dir}/{save_name}/graph.pkl")
 
            # Update runtime config path
            #cfg["kg"]["save_path"] = f"{models_dir}/{save_name}/graph.pkl"

            # Reinitialize retriever from disk
            #rag = HippoRAG()
            #rag._active_model_name = save_name

            ##node_count = rag.kg.graph.number_of_nodes()
            #edge_count = rag.kg.graph.number_of_edges()

            # ── Hot-swap the global rag ──
            #yield _emit("log", "Loading new KG into memory ...")
            #rag = HippoRAG(graph=new_graph)
            #rag._active_model_name = save_name
 
            #node_count = new_graph.number_of_nodes()
            #edge_count = new_graph.number_of_edges()
 
            #yield _emit(
            ##    "done",
            #    f"✓ KG '{save_name}' is live: {node_count} nodes, {edge_count} edges.",
            #    node_count=node_count,
            #    edge_count=edge_count,
            #    model_name=save_name,
            #)
 
        except Exception as exc:
            logger.error(
                f"KG build failed: {exc}",
                extra={"request_id": request_id},
            )
            yield _emit("error", f"Build failed: {exc}")
 
    # Return the SSE stream.
    # Cache-Control: no-cache prevents proxies from buffering the stream.
    # X-Accel-Buffering: no disables nginx proxy buffering specifically.
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ════════════════════════════════════════════════════════════════════════════
#  KG LOAD  —  POST /api/kg/load
# ════════════════════════════════════════════════════════════════════════════
 
@app.post("/api/kg/load")
def kg_load(body: LoadRequest):
    """
    Hot-load a saved KG from the Docker volume into memory.
 
    Swaps the global `rag` instance so /api/query immediately uses the new
    KG.  No server restart is required.
 
    This is the primary grader workflow when active_model is not set:
        1. Pre-train and save a KG (e.g. "eval_corpus") before submission.
        2. Grader runs `docker compose up`.
        3. Grader opens /train → Load panel → clicks "Load" next to "eval_corpus".
        4. KG loads in < 5 seconds.  /api/query is immediately ready.
 
    Responses
    ---------
    200  {"status": "ok", "name": str, "node_count": int, "edge_count": int}
    404  {"detail": "No saved KG named '<name>' found ..."}
    500  {"detail": "Failed to load KG: <reason>"}
    """
    global rag
 
    cfg        = load_config()
    models_dir = cfg.get("kg", {}).get("models_dir", "/app/models")
 
    # Ensure the directory exists (defensive — it should exist after any build)
    os.makedirs(models_dir, exist_ok=True)
 
    logger.info(f"Loading saved KG '{body.name}' from '{models_dir}' ...")
 
    try:
        graph = load_kg(name=body.name, models_dir=models_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
 
    # Atomic swap — safe because Python assignment is atomic under the GIL.
    # In-flight requests hold a reference to the old rag and finish normally.
    rag = HippoRAG(graph=graph)
    rag._active_model_name = body.name
 
    logger.info(f"KG '{body.name}' loaded successfully.")
    return {
        "status":     "ok",
        "name":       body.name,
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
    }


