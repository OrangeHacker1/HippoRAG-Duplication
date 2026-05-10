import uuid
import requests as http_requests
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from api.logger import get_logger
from retrieval.retriever import HippoRAG
from eval.metrics import recall_at_k, exact_match, f1_score
from data.eval_dataset import QUESTIONS

logger = get_logger(__name__)

rag: HippoRAG | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag
    try:
        rag = HippoRAG()
        logger.info("HippoRAG loaded successfully.")
    except Exception as e:
        logger.warning(f"Could not load HippoRAG on startup: {e}. Build the KG first.")
    yield


app = FastAPI(title="HippoRAG", lifespan=lifespan)
templates = Jinja2Templates(directory="api/templates")


class QueryRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/query")
def query(body: QueryRequest, request: Request):
    request_id = str(uuid.uuid4())
    log = logger.getChild("query")

    if not body.question.strip():
        logger.info("Empty query rejected.", extra={"request_id": request_id})
        raise HTTPException(status_code=422, detail="Query must not be empty.")

    if rag is None:
        raise HTTPException(
            status_code=503,
            detail="Knowledge graph not loaded. Run python run_build_kg.py first."
        )

    logger.info(f"Query received: {body.question}", extra={"request_id": request_id})

    try:
        passages = rag.retrieve(body.question)
        context = "\n".join(passages)
        answer = rag.llm.generate(
            f"Answer using context:\n\n{context}\n\nQuestion:\n{body.question}"
        )
        logger.info(f"Query answered successfully.", extra={"request_id": request_id})
        return {"answer": answer, "passages": passages, "request_id": request_id}

    except http_requests.exceptions.ConnectionError:
        logger.error("LLM unreachable.", extra={"request_id": request_id})
        raise HTTPException(
            status_code=503,
            detail="The language model is currently unavailable. Please try again later."
        )
    except http_requests.exceptions.ConnectTimeout:
        logger.error("LLM connection timed out.", extra={"request_id": request_id})
        raise HTTPException(
            status_code=503,
            detail="The language model is currently unavailable. Please try again later."
        )


@app.get("/evaluate", response_class=HTMLResponse)
def evaluate_page(request: Request):
    return templates.TemplateResponse("evaluate.html", {"request": request})


@app.post("/api/evaluate")
def evaluate():
    request_id = str(uuid.uuid4())

    if rag is None:
        raise HTTPException(
            status_code=503,
            detail="Knowledge graph not loaded. Run python run_build_kg.py first."
        )

    logger.info("Evaluation started.", extra={"request_id": request_id})

    recall_ks = [1, 2, 5]
    recall_totals = {k: 0.0 for k in recall_ks}
    em_total = 0.0
    f1_total = 0.0
    results = []

    for item in QUESTIONS:
        question = item["question"]
        gold_docs = item["gold_docs"]
        gold_answers = item["gold_answers"]

        try:
            passages = rag.retrieve(question)
            context = "\n".join(passages)
            answer = rag.llm.generate(
                f"Answer using context:\n\n{context}\n\nQuestion:\n{question}"
            )
        except Exception as e:
            logger.error(f"Eval query failed: {e}", extra={"request_id": request_id})
            continue

        em = exact_match(answer, gold_answers)
        f1 = f1_score(answer, gold_answers)
        em_total += em
        f1_total += f1

        recalls = {}
        for k in recall_ks:
            r = recall_at_k(passages, gold_docs, k)
            recall_totals[k] += r
            recalls[f"Recall@{k}"] = round(r, 4)

        results.append({
            "question": question,
            "answer": answer,
            "passages": passages,
            "em": round(em, 4),
            "f1": round(f1, 4),
            **recalls,
        })

    n = len(QUESTIONS)
    aggregate = {f"Recall@{k}": round(recall_totals[k] / n, 4) for k in recall_ks}
    aggregate["ExactMatch"] = round(em_total / n, 4)
    aggregate["F1"] = round(f1_total / n, 4)

    logger.info(f"Evaluation complete: {aggregate}", extra={"request_id": request_id})
    return {"aggregate": aggregate, "results": results, "request_id": request_id}
