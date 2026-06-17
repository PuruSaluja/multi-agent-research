# Architecture Decision Records

## ADR-001: Use LangGraph over raw LangChain chains

**Status**: Accepted

**Context**: The research workflow requires conditional branching — if the first search returns poor results, the agent should retry with a refined query. Linear chains can't express this cleanly.

**Decision**: Use LangGraph's `StateGraph` to model the agent workflow as a directed graph with explicit state transitions.

**Consequences**: More setup boilerplate, but the workflow is inspectable, testable per-node, and easy to extend with new agents.

---

## ADR-002: Server-Sent Events over WebSockets for streaming

**Status**: Accepted

**Context**: Needed real-time token streaming from FastAPI to React. Both SSE and WebSockets support this.

**Decision**: Use SSE (`text/event-stream`). It's unidirectional (server → client), which matches our use case exactly. No need for bidirectional communication.

**Consequences**: Simpler server implementation (`StreamingResponse` in FastAPI). Client uses native `EventSource` API. Reconnect logic is handled by the browser automatically.

---

## ADR-003: Separate Render (backend) and Vercel (frontend) deployments

**Status**: Accepted

**Context**: Could deploy everything on one platform or split across specialized platforms.

**Decision**: Backend on Render (Docker container support, persistent services), frontend on Vercel (optimized for static/React builds, global CDN).

**Consequences**: Need to manage CORS and environment variables across two platforms. Simpler than running a monolith, and both free tiers are sufficient for demo purposes.

---

## ADR-004: Claude claude-sonnet-4-6 as primary LLM

**Status**: Accepted

**Context**: Evaluated GPT-4o and Gemini 1.5 Pro as alternatives.

**Decision**: Claude claude-sonnet-4-6 — best instruction-following for structured JSON output, 200k context window useful for long research synthesis.

**Consequences**: Locked into Anthropic API pricing. Abstracted behind a LangChain wrapper so switching is possible if needed.
