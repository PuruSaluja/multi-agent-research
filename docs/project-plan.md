# Multi-Agent Research Assistant — Project Plan

## Goal
Build a full-stack AI research assistant that uses multiple specialized agents to search the web, synthesize information, and return structured answers with citations.

## Core Requirements
- Natural language query input from a React frontend
- LangGraph-orchestrated multi-agent backend (planner, researcher, refiner, analyst, writer)
- Real-time streaming responses via Server-Sent Events
- Web search via Tavily API
- Claude (Anthropic) as the LLM backbone
- Deployable via Docker / Render + Vercel

## Out of Scope (v1)
- PDF/document upload

Originally also out of scope, both since built (ADR-007):
- ~~User authentication~~
- ~~Persistent conversation history~~
- Horizontal scaling — session state is in-process, so the API runs one worker

## Success Criteria
- Query returns a sourced, structured answer, bounded by a 180-second timeout
  (`RESEARCH_TIMEOUT_SECONDS`). A typical run with one refine round is well
  inside that; the ceiling exists because Tavily latency and report length both
  vary. *An earlier draft of this plan said "under 30 seconds" — that was never
  measured and the implementation never enforced it.*
- The final report streams into the UI token by token as the Writer produces it
- A pass that finds little evidence is retried with refined queries rather than
  handed to the Analyst as-is
- A total search failure surfaces as an error, never as a confident report
  written from no sources
- System handles concurrent requests without crashing, and refuses new work
  past `MAX_ACTIVE_SESSIONS` rather than degrading

## Tech Stack Decision
| Layer | Choice | Reason |
|-------|--------|--------|
| Frontend | React + Vite | Fast dev experience, easy Vercel deploy |
| Backend | FastAPI | Async-native, pairs well with LangGraph streaming |
| Orchestration | LangGraph | Built-in state machine for agent workflows |
| LLM | Claude Sonnet 4.6 (`claude-sonnet-4-6`) | Strong reasoning, 1M context |
| Search | Tavily | Purpose-built for AI agents |
| Infra | Docker + Render | Simple containerized deployment |

## Milestones
- [x] Backend agent graph working locally
- [x] Streaming SSE endpoint live
- [x] React frontend connected to backend
- [x] Docker Compose running full stack
- [x] Deployed to Render + Vercel
- [x] Conditional refine/retry loop for thin research passes
- [x] Token-level streaming of the final report
- [x] Test suite covering routing, search failure handling, and session lifecycle

## Known Limitations
- Session queues live in process memory. Multiple workers or a restart lose
  in-flight runs; moving past one worker means moving this to Redis.
- Synthetic retry bound: one refine round. Deeper research would need a budget
  rather than a fixed count.
- No auth, no per-user history, no result caching.
