import asyncio
import json
import queue
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

# Import after env is loaded so API keys are available
from graph import compiled_graph
from agents.writer import _collect_sources

# In-memory session store: session_id -> Queue
sessions: dict[str, queue.Queue] = {}
TIMEOUT_SECONDS = 180


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    session_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    sessions.clear()


app = FastAPI(title="Multi-Agent Research API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_graph_streaming(session_id: str, query: str) -> None:
    """Run LangGraph streaming, collecting incremental state updates."""
    q = sessions[session_id]
    emitted_log_count = 0
    accumulated_state: dict = {
        "query": query,
        "sub_tasks": [],
        "search_results": {},
        "analysis": "",
        "final_report": "",
        "agent_logs": [],
        "current_agent": "",
        "error": None,
    }

    try:
        for chunk in compiled_graph.stream(accumulated_state, stream_mode="updates"):
            for node_name, node_output in chunk.items():
                # Merge output into accumulated state
                for k, v in node_output.items():
                    if k == "agent_logs" and isinstance(v, list):
                        accumulated_state["agent_logs"] = v
                    elif v is not None:
                        accumulated_state[k] = v

                if accumulated_state.get("error"):
                    q.put(("error", {"message": accumulated_state["error"]}))
                    return

                # Emit new log entries
                all_logs = accumulated_state.get("agent_logs", [])
                for log in all_logs[emitted_log_count:]:
                    q.put(("agent_update", log))
                emitted_log_count = len(all_logs)

        # Emit completion
        sources = _collect_sources(accumulated_state.get("search_results", {}))
        q.put(("complete", {
            "final_report": accumulated_state.get("final_report", ""),
            "sub_tasks": accumulated_state.get("sub_tasks", []),
            "sources": sources,
        }))

    except Exception as exc:
        q.put(("error", {"message": str(exc)}))


@app.post("/api/research", response_model=ResearchResponse)
async def start_research(request: ResearchRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    session_id = str(uuid.uuid4())
    sessions[session_id] = queue.Queue()

    thread = threading.Thread(
        target=_run_graph_streaming,
        args=(session_id, request.query.strip()),
        daemon=True,
    )
    thread.start()

    return ResearchResponse(session_id=session_id)


@app.get("/api/research/{session_id}/stream")
async def stream_research(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    q = sessions[session_id]

    async def event_generator():
        start = asyncio.get_running_loop().time()
        try:
            while True:
                elapsed = asyncio.get_running_loop().time() - start
                if elapsed > TIMEOUT_SECONDS:
                    yield _sse_event("error", {"message": f"Research timed out after {TIMEOUT_SECONDS} seconds"})
                    break

                try:
                    # Poll non-blocking to keep the async loop free
                    event_type, data = await asyncio.to_thread(q.get, timeout=1.0)
                except queue.Empty:
                    # Send a keepalive comment so the connection stays alive
                    yield ": keepalive\n\n"
                    continue

                yield _sse_event(event_type, data)

                if event_type in ("complete", "error"):
                    break
        finally:
            sessions.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
