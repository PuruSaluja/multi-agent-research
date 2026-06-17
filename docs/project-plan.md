# Multi-Agent Research Assistant — Project Plan

## Goal
Build a full-stack AI research assistant that uses multiple specialized agents to search the web, synthesize information, and return structured answers with citations.

## Core Requirements
- Natural language query input from a React frontend
- LangGraph-orchestrated multi-agent backend (supervisor + research + synthesis agents)
- Real-time streaming responses via Server-Sent Events
- Web search via Tavily API
- Claude (Anthropic) as the LLM backbone
- Deployable via Docker / Render + Vercel

## Out of Scope (v1)
- User authentication
- Persistent conversation history
- PDF/document upload

## Success Criteria
- Query returns a sourced, structured answer in under 30 seconds
- Frontend streams tokens in real time
- System handles concurrent requests without crashing

## Tech Stack Decision
| Layer | Choice | Reason |
|-------|--------|--------|
| Frontend | React + Vite | Fast dev experience, easy Vercel deploy |
| Backend | FastAPI | Async-native, pairs well with LangGraph streaming |
| Orchestration | LangGraph | Built-in state machine for agent workflows |
| LLM | Claude (claude-sonnet-4-6) | Strong reasoning, large context |
| Search | Tavily | Purpose-built for AI agents |
| Infra | Docker + Render | Simple containerized deployment |

## Milestones
- [ ] Backend agent graph working locally
- [ ] Streaming SSE endpoint live
- [ ] React frontend connected to backend
- [ ] Docker Compose running full stack
- [ ] Deployed to Render + Vercel
