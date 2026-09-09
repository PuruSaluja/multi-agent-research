# Development Log

## September 9, 2026

An audit of the repo against its own documentation turned up nine places where
the docs described something the code did not do. Fixed all of them, and added
the test suite that would have caught most of them.

### Corrections to the June 17 entry below
- **"LangGraph streaming required wrapping `astream_events` rather than
  `astream`"** — this was never true of this codebase. Neither call appears
  anywhere in it; `main.py` used (and still uses) the synchronous
  `compiled_graph.stream(stream_mode="updates")`. What streamed was per-agent
  log entries, not tokens.
- **"CORS needed explicit origin allowlist for Vercel preview URLs"** — no
  Vercel origin was ever added. `allow_origins` was hardcoded to localhost, so
  a deployed frontend would have been blocked.

### Fixed
- **Docker networking.** Commit `3ba4d2e` had changed `VITE_API_URL` from
  `http://localhost:8000` to `http://backend:8000` as a "fix". That value is
  inlined into the browser bundle, and `backend` only resolves inside the
  compose network — so the documented `docker-compose up` flow failed on its
  first API call. Reverted, with a comment explaining why.
- **CORS is configuration now.** `CORS_ALLOW_ORIGINS` plus an optional
  `CORS_ALLOW_ORIGIN_REGEX` for preview deployments, surfaced in `render.yaml`
  and `.env.example`.
- **Token streaming is real.** The Writer now uses `client.messages.stream()`
  and emits each chunk as a `report_token` SSE event; the frontend renders the
  report progressively instead of waiting for the run to finish. Nodes reach
  the session queue through a ContextVar emitter (`backend/events.py`) rather
  than threading a callback through every signature.
- **The refine loop ADR-001 described now exists.** A new `refiner` node
  rewrites sub-questions that found nothing, and `route_after_research` loops
  back for another pass when coverage is thin and budget remains.
- **Search failures are no longer silent.** `search_web` retries with backoff
  and raises `SearchError` instead of returning `[]`; the Researcher keeps
  "ran and found nothing" separate from "could not run", and errors the run if
  every search failed. The Analyst refuses to synthesize from zero sources.
- **Dead dependency removed.** `langchain` and `langchain-anthropic` were
  pinned but never imported — the agents use the Anthropic SDK directly. The
  model ID moved to `config.ANTHROPIC_MODEL` and the client to `llm.py`, so
  it is no longer repeated in each agent.
- **Images run production servers.** The backend Dockerfile no longer passes
  `--reload` (compose overrides the command for local dev); the frontend
  Dockerfile is multi-stage, serving built assets from nginx, with a `dev`
  target for compose.
- **Session leak closed.** Sessions carry a `created_at`; a background sweeper
  drops ones whose client never connected, and `MAX_ACTIVE_SESSIONS` returns
  429 rather than letting the queue dict grow unbounded. The single-worker
  requirement is now written down (ADR-005) instead of implied.
- **Plan reconciled with reality.** Milestones ticked, and the unmeasured
  "under 30 seconds" success criterion replaced with the timeout the code
  actually enforces.

### Verified
- 37 backend tests pass (`pytest` in `backend/`), including an integration test
  that drives the real compiled graph through planner → researcher → refiner →
  researcher → analyst → writer and asserts the retry loop both fires and
  terminates.
- `npm run build` produces a clean production bundle (288 modules).
- Not verified: a live end-to-end run against the real Anthropic and Tavily
  APIs. That needs credentials this audit did not have, so every test fakes the
  two external clients.

### Verified against the live APIs
Two full runs with real keys, via `scripts/live_smoke.py`:

| | run 1 | run 2 |
|---|---|---|
| query | health effects of sleep deprivation | causes of the 2008 financial crisis |
| total | 100.4s | 108.2s |
| first report token | 40.1s | 40.7s |
| report | 15,020 chars, 97 chunks | 15,514 chars, 111 chunks |
| sources | 15 | 15 |

Both produced structured reports with inline citations and a Limitations
section, and all eight checks passed. Streamed chunks reassembled byte for byte
into the final report.

### Found and fixed during that run
The agent timeline was not actually live. `compiled_graph.stream()` only yields
when a node returns, so the Researcher's five searches — about 15 seconds of
work — all appeared at once with the same timestamp. Progress now goes through
the emitter (`emit_log`) as each step finishes, so the Researcher reports at
7.2s, 10.6s, 12.7s, 16.2s and 18.6s rather than in one burst. `main.py` no
longer diffs the log list; the emitter is the only path for `agent_update`.

### Analyst streaming
The 40-second wait before anything appeared was the worst part of a run: the
Planner, five searches and the Analyst all completed before the Writer produced
the first visible token. The Analyst now streams too, into a collapsible panel
that folds away once the report starts.

Measured on a live run ("How does CRISPR gene editing actually work?"):

| | before | after |
|---|---|---|
| first visible output | 40.1s | 15.8s |
| first report token | 40.1s | 37.4s |
| total | 100.4s | 120.4s |

Output is now near-continuous from 4.2s: planner at 4.2s, searches through
13.5s, analysis 15.8s to 35.4s, report from 37.4s. The two remaining gaps are
about two seconds each.

### Next
- Cache Tavily results for repeated sub-queries to cut API cost
- Query history panel in the frontend
- Move session state to Redis if this ever needs more than one worker

---

## June 17, 2026

> Two claims in this entry were later found to be inaccurate — see the
> corrections in the September 9 entry above.

### Done
- Deployment stable on Render + Vercel
- SSE streaming working end-to-end
- Docker Compose tested locally
- README updated with setup instructions and architecture diagram

### Issues Encountered
- Render cold-start timeout (free tier spins down after inactivity) — documented workaround in README
- CORS needed explicit origin allowlist for Vercel preview URLs
- LangGraph streaming required wrapping `astream_events` rather than `astream` to get token-level chunks

### Next
- Add retry logic in the supervisor node for failed Tavily searches
- Explore caching frequent queries to reduce API costs
- Consider adding a query history panel to the frontend
