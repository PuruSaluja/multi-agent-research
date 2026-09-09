# Architecture Decision Records

## ADR-001: Use LangGraph over raw LangChain chains

**Status**: Accepted — implemented

**Context**: The research workflow requires conditional branching — if a search pass returns poor results, the workflow should retry with refined queries. Linear chains can't express this cleanly.

**Decision**: Use LangGraph's `StateGraph` to model the agent workflow as a directed graph with explicit state transitions.

**Implementation**: `route_after_research` in `backend/graph.py` inspects coverage (how many sub-questions produced sources) after every research pass. A thin pass with retry budget left routes to the `refiner` node, which rewrites the unproductive sub-questions; the graph then loops back to `researcher`. `retry_count` and `MAX_RESEARCH_RETRIES` bound the cycle. A healthy pass goes straight to `analyst`.

**Consequences**: More setup boilerplate, but the workflow is inspectable, testable per-node, and easy to extend. The cycle needs an explicit bound — an unbounded refine loop would spend the API budget on a query that will never match anything.

---

## ADR-002: Server-Sent Events over WebSockets for streaming

**Status**: Accepted

**Context**: Needed real-time streaming from FastAPI to React. Both SSE and WebSockets support this.

**Decision**: Use SSE (`text/event-stream`). It's unidirectional (server → client), which matches our use case exactly. No need for bidirectional communication.

**Consequences**: Simpler server implementation (`StreamingResponse` in FastAPI). Client uses the native `EventSource` API. The browser handles reconnect automatically — though a reconnect cannot resume a completed run, since session queues are dropped once drained.

---

## ADR-003: Separate Render (backend) and Vercel (frontend) deployments

**Status**: Accepted

**Context**: Could deploy everything on one platform or split across specialized platforms.

**Decision**: Backend on Render (Docker container support, persistent services), frontend on Vercel (optimized for static/React builds, global CDN).

**Consequences**: CORS and environment variables must be managed across two platforms. The backend's allowed origins are configuration, not code — `CORS_ALLOW_ORIGINS` for the production origin and `CORS_ALLOW_ORIGIN_REGEX` for Vercel preview URLs, whose hostname changes per build. Both free tiers are sufficient for demo purposes.

---

## ADR-004: Claude Sonnet 4.6 as primary LLM

**Status**: Accepted

**Context**: Evaluated GPT-4o and Gemini 1.5 Pro as alternatives.

**Decision**: Claude Sonnet 4.6 (`claude-sonnet-4-6`) — best instruction-following for structured JSON output, and a large context window useful for long research synthesis.

**Consequences**: Locked into Anthropic API pricing. The model ID is a single environment variable (`ANTHROPIC_MODEL`, read in `backend/config.py`) and all four agents share one client factory in `backend/llm.py`, so changing model is a config change rather than a code edit. *An earlier version of this ADR claimed the LLM was "abstracted behind a LangChain wrapper" — it never was; the agents call the Anthropic SDK directly, and the unused LangChain dependency has since been removed.*

---

## ADR-005: Keep session state in process, and run one worker

**Status**: Accepted, with a known ceiling

**Context**: A research run is started by `POST /api/research` and consumed by a later `GET .../stream`. The two requests need to share a queue.

**Decision**: Hold session queues in a process-local dict, and run uvicorn with `--workers 1`. A background sweeper drops sessions whose client never connected, and `MAX_ACTIVE_SESSIONS` applies backpressure.

**Consequences**: Simple, no extra infrastructure, and correct for a single-instance demo. It does not survive a restart and cannot scale horizontally — with two workers, a POST handled by worker A creates a session worker B cannot find. Redis is the migration path if this ever needs more than one instance. This constraint is recorded in the Dockerfile, the README, and the `Session` docstring so it is not rediscovered by accident.
