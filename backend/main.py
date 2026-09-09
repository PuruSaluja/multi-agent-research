import asyncio
import json
import queue
import threading
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

# Imported after load_dotenv() so API keys are present when clients are built.
import config  # noqa: E402
from agents.writer import collect_sources  # noqa: E402
from events import set_emitter  # noqa: E402
from graph import compiled_graph  # noqa: E402


@dataclass
class Session:
    """One research run's event queue.

    NOTE: this store is in-process. The app must run with a single worker
    (see the Dockerfile and README) -- with more than one, a POST handled by
    worker A creates a session that worker B cannot find when the browser opens
    the stream. Moving to multiple workers means moving this to Redis.
    """

    queue: "queue.Queue" = field(default_factory=queue.Queue)
    created_at: float = field(default_factory=time.monotonic)


sessions: dict[str, Session] = {}
_sessions_lock = threading.Lock()


def reap_stale_sessions(now: float | None = None) -> int:
    """Drop sessions whose client never connected. Returns how many were removed.

    Without this, every abandoned POST leaks a queue for the life of the
    process.
    """
    now = time.monotonic() if now is None else now
    with _sessions_lock:
        stale = [
            sid
            for sid, s in sessions.items()
            if now - s.created_at > config.SESSION_TTL_SECONDS
        ]
        for sid in stale:
            sessions.pop(sid, None)
    return len(stale)


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    session_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def sweeper():
        while True:
            await asyncio.sleep(config.SESSION_SWEEP_INTERVAL_SECONDS)
            reap_stale_sessions()

    task = asyncio.create_task(sweeper())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        sessions.clear()


app = FastAPI(title="Multi-Agent Research API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_origin_regex=config.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_graph_streaming(session_id: str, query: str) -> None:
    """Run the graph on a worker thread, pushing events onto the session queue."""
    with _sessions_lock:
        session = sessions.get(session_id)
    if session is None:
        return
    q = session.queue

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
        "unanswered_tasks": [],
        "retry_count": 0,
    }

    # Lets nodes (the Writer) push incremental output without threading a
    # callback through every signature.
    set_emitter(lambda event_type, data: q.put((event_type, data)))

    try:
        for chunk in compiled_graph.stream(accumulated_state, stream_mode="updates"):
            for _node_name, node_output in chunk.items():
                for k, v in node_output.items():
                    if k == "agent_logs" and isinstance(v, list):
                        accumulated_state["agent_logs"] = v
                    elif v is not None:
                        accumulated_state[k] = v

                if accumulated_state.get("error"):
                    q.put(("error", {"message": accumulated_state["error"]}))
                    return

                all_logs = accumulated_state.get("agent_logs", [])
                for log in all_logs[emitted_log_count:]:
                    q.put(("agent_update", log))
                emitted_log_count = len(all_logs)

        q.put((
            "complete",
            {
                "final_report": accumulated_state.get("final_report", ""),
                "sub_tasks": accumulated_state.get("sub_tasks", []),
                "sources": collect_sources(accumulated_state.get("search_results", {})),
                "unanswered_tasks": accumulated_state.get("unanswered_tasks", []),
            },
        ))
    except Exception as exc:  # noqa: BLE001 - last resort, must reach the client
        q.put(("error", {"message": str(exc)}))
    finally:
        set_emitter(None)


@app.post("/api/research", response_model=ResearchResponse)
async def start_research(request: ResearchRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    reap_stale_sessions()
    with _sessions_lock:
        if len(sessions) >= config.MAX_ACTIVE_SESSIONS:
            raise HTTPException(
                status_code=429,
                detail="Too many research sessions in flight. Try again shortly.",
            )
        session_id = str(uuid.uuid4())
        sessions[session_id] = Session()

    threading.Thread(
        target=_run_graph_streaming,
        args=(session_id, request.query.strip()),
        daemon=True,
    ).start()

    return ResearchResponse(session_id=session_id)


@app.get("/api/research/{session_id}/stream")
async def stream_research(session_id: str):
    with _sessions_lock:
        session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    q = session.queue

    async def event_generator():
        start = asyncio.get_running_loop().time()
        try:
            while True:
                elapsed = asyncio.get_running_loop().time() - start
                if elapsed > config.RESEARCH_TIMEOUT_SECONDS:
                    yield _sse_event(
                        "error",
                        {
                            "message": (
                                "Research timed out after "
                                f"{config.RESEARCH_TIMEOUT_SECONDS} seconds"
                            )
                        },
                    )
                    break

                try:
                    event_type, data = await asyncio.to_thread(q.get, True, 1.0)
                except queue.Empty:
                    yield ": keepalive\n\n"
                    continue

                yield _sse_event(event_type, data)

                if event_type in ("complete", "error"):
                    break
        finally:
            with _sessions_lock:
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
    return {
        "status": "ok",
        "model": config.ANTHROPIC_MODEL,
        "active_sessions": len(sessions),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
