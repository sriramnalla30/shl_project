"""
FastAPI app — routes, lifecycle, lifespan handler.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import DATA_DIR, load_catalog, load_url_allowlist, get_settings
from app.schemas import ChatRequest, ChatResponse, Message
from app.agent.state import AgentState, Slots
from app.observability.tracing import init_tracing

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Globals set during lifespan ──────────────────────────────────────────────
_graph = None
_catalog: list[dict] = []
_url_allowlist: frozenset[str] = frozenset()
_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load catalog, indexes, and compile graph once at startup."""
    global _graph, _catalog, _url_allowlist, _ready

    logger.info("Starting up — loading catalog and indexes…")
    init_tracing()

    # Load catalog
    _catalog = load_catalog()
    logger.info("Catalog loaded: %d records", len(_catalog))

    # Load URL allowlist
    _url_allowlist = load_url_allowlist()
    if not _url_allowlist:
        raise RuntimeError(
            "url_allowlist.txt is missing or empty. "
            "Run `python scripts/build_indexes.py` to generate data/ artifacts before starting the server."
        )
    logger.info("URL allowlist loaded: %d URLs", len(_url_allowlist))

    # Initialize retrieval modules
    from app.retrieval.bm25 import load_bm25
    from app.retrieval.dense import load_dense
    load_bm25(DATA_DIR, _catalog)
    load_dense(DATA_DIR)

    # Set catalog references in nodes that need it
    from app.agent.nodes.retriever import set_catalog as set_retriever_catalog
    from app.agent.nodes.comparator import set_catalog as set_comparator_catalog
    from app.agent.nodes.validator import set_url_allowlist
    set_retriever_catalog(_catalog)
    set_comparator_catalog(_catalog)
    set_url_allowlist(_url_allowlist)

    # Build graph
    from app.agent.graph import build_graph
    _graph = build_graph()
    logger.info("LangGraph compiled successfully")

    _ready = True
    logger.info("✅ Startup complete — ready to serve")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="SHL Assessment Recommender",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    if not _ready:
        raise HTTPException(status_code=503, detail="Not ready")
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not _ready or _graph is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    start = time.time()
    try:
        # Count user turns
        user_turns = sum(1 for m in request.messages if m.role == "user")

        # Build initial state
        initial_state: AgentState = {
            "messages": request.messages,
            "turn": user_turns,
            "slots": Slots(),
            "in_scope": True,
            "intent": None,
            "candidates": [],
            "shortlist": [],
            "compare_pair": None,
            "draft": None,
            "validation_errors": [],
            "retry_count": 0,
            "final": None,
        }

        # Invoke the graph
        result = await _graph.ainvoke(initial_state)

        # Extract final response
        final = result.get("final")
        if final:
            response = ChatResponse(**final)
        elif result.get("draft"):
            response = ChatResponse(**result["draft"])
        else:
            response = ChatResponse(
                reply="Could you tell me more about the role you're hiring for?",
                recommendations=[],
                end_of_conversation=False,
            )

        elapsed = time.time() - start
        logger.info("Chat completed in %.2fs (turn=%d, recs=%d)",
                     elapsed, user_turns, len(response.recommendations))
        return response

    except Exception as e:
        elapsed = time.time() - start
        logger.error("Chat failed after %.2fs: %s", elapsed, e, exc_info=True)
        # Return safe fallback response rather than 500
        return ChatResponse(
            reply="I'm having trouble processing your request. Could you tell me about the role you're hiring for?",
            recommendations=[],
            end_of_conversation=False,
        )
