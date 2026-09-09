# Multi-Agent Research Assistant

A full-stack web application where specialized AI agents collaborate in real-time
to answer complex research questions. Built as a portfolio project for AI/ML
Engineer and Agentic AI roles.

## Architecture

```
User Question
     |
     v
+---------------------------------------------------------------------------+
|                       LangGraph State Machine                             |
|                                                                           |
|  +---------+    +------------+    +---------+    +--------+               |
|  | Planner |--->| Researcher |--->| Analyst |--->| Writer |               |
|  |         |    |            |    |         |    |        |               |
|  | Breaks  |    | Tavily     |    |Synthesize   | Streams |               |
|  | question|    | search per |    | findings|   | the MD  |               |
|  | into 3-5|    | sub-task   |    | & gaps  |   | report  |               |
|  |sub-tasks|    |            |    |         |   |         |               |
|  +---------+    +-----+------+    +---------+   +--------+                |
|                       |  ^                                                |
|            thin pass? |  | refined queries                                |
|                       v  |                                                |
|                  +-----------+                                            |
|                  |  Refiner  |  rewrites sub-questions that found nothing |
|                  +-----------+  (bounded by MAX_RESEARCH_RETRIES)         |
|                                                                           |
|            error_handler <-- any node that sets state["error"]            |
+---------------------------------------------------------------------------+
     |
     v FastAPI SSE stream
     |
     v
React UI -- live agent timeline + the report streaming in token by token
```

### Agent Roles

| Agent | Role | Backed by |
|---|---|---|
| **Planner** | Decomposes the query into 3-5 searchable sub-questions | Claude Sonnet 4.6 |
| **Researcher** | Tavily search per sub-question, top 3 results each | Tavily API |
| **Refiner** | Rewrites sub-questions that returned nothing, so they can be retried | Claude Sonnet 4.6 |
| **Analyst** | Synthesizes results, notes contradictions and unevidenced gaps | Claude Sonnet 4.6 |
| **Writer** | Streams a structured Markdown report with citations | Claude Sonnet 4.6 |

The Researcher to Refiner to Researcher edge is conditional: it only fires when a
pass leaves most sub-questions unanswered and retry budget remains. See
[ADR-001](docs/architecture-decisions.md).

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph |
| LLM | Anthropic Claude Sonnet 4.6 (`claude-sonnet-4-6`) |
| Web search | Tavily API |
| Backend | FastAPI + SSE streaming |
| Frontend | React 18 + Vite + Tailwind CSS |
| Containerization | Docker + docker-compose |
| Tests | pytest |

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes docker-compose)
- Anthropic API key -- [console.anthropic.com](https://console.anthropic.com)
- Tavily API key (free tier) -- [tavily.com](https://tavily.com)

> Alternatively, without Docker: Python 3.11+ and Node 18+

## Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/PuruSaluja/multi-agent-research.git
cd multi-agent-research
```

### 2. Add API keys
```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

### 3. Run with Docker
```bash
docker-compose up --build
```

Open **http://localhost:5173** in your browser.

### Running without Docker

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000 --workers 1
```

On Windows the activate step is `.venv\Scripts\activate`.

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

Only the two API keys are required. Everything else has a working default --
see [.env.example](.env.example) for the full list.

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Claude API key |
| `TAVILY_API_KEY` | *(required)* | Tavily search key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Model used by every agent |
| `CORS_ALLOW_ORIGINS` | localhost dev origins | Comma-separated browser origins allowed to call the API |
| `CORS_ALLOW_ORIGIN_REGEX` | unset | Regex for origins with varying hostnames (Vercel previews) |
| `RESEARCH_TIMEOUT_SECONDS` | `180` | Hard cap on a single run |
| `MAX_RESEARCH_RETRIES` | `1` | Refine/re-search rounds allowed |
| `MAX_ACTIVE_SESSIONS` | `50` | Backpressure; further requests get a 429 |
| `REDIS_URL` | unset | Shares session state and the search cache. Required before running more than one worker |
| `WEB_CONCURRENCY` | `1` | uvicorn workers. Only raise this with `REDIS_URL` set |
| `DATABASE_URL` | `sqlite:///./data/app.db` | Accounts and saved history. Point at Postgres for multi-instance |
| `AUTH_SECRET` | dev default | Signs login tokens. **Must be set to a random value in production** |
| `SEARCH_CACHE_TTL_SECONDS` | `21600` | How long search results are reused. `0` disables |
| `SEARCH_CONCURRENCY` | `5` | Sub-question searches run in parallel up to this many |

### Accounts and history

Research works signed out. Signing in saves each run and makes it re-openable
from the History panel. Passwords are hashed with Argon2 and never stored or
logged in plaintext.

`AUTH_SECRET` signs the login tokens, so anyone holding it can forge a token
for any account. The built-in default is for local development only — the app
warns loudly at startup if it is still in use, and `render.yaml` has Render
generate one per deployment.

### Running more than one worker

Session state is per-process by default, so a run started on one worker cannot
be streamed from another. Set `REDIS_URL` and both the session queues and the
search cache move to Redis, which makes `WEB_CONCURRENCY` above 1 safe.
`GET /api/health` reports `multi_worker_safe` so you can check rather than
assume.

## Getting API Keys

### Anthropic API Key
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up / log in, then API Keys, then Create Key
3. Copy the `sk-ant-...` key into `.env`

### Tavily API Key (free tier -- 1,000 searches/month)
1. Go to [app.tavily.com](https://app.tavily.com)
2. Sign up, then Dashboard, then API Keys
3. Copy the `tvly-...` key into `.env`

## Example Queries

- *"What are the most promising applications of large language models in healthcare?"*
- *"What are the latest breakthroughs in quantum computing?"*
- *"How do leading AI labs differ in their approach to AI safety?"*
- *"What are the most effective evidence-based treatments for insomnia?"*
- *"What is the current state of fusion energy research?"*

## Project Structure

```
multi-agent-research/
+-- backend/
|   +-- main.py               # FastAPI app -- REST + SSE endpoints, session store
|   +-- graph.py              # LangGraph state machine + routing predicates
|   +-- config.py             # Every tunable, read from the environment
|   +-- llm.py                # Shared Anthropic client
|   +-- events.py             # ContextVar emitter for incremental node output
|   +-- models.py             # ResearchState TypedDict
|   +-- agents/
|   |   +-- planner.py        # Decomposes query into sub-tasks (JSON)
|   |   +-- researcher.py     # Tavily search per sub-task
|   |   +-- refiner.py        # Rewrites unproductive sub-questions
|   |   +-- analyst.py        # Synthesizes search results
|   |   +-- writer.py         # Streams the final Markdown report
|   +-- tools/
|   |   +-- search.py         # Tavily client wrapper, retries, SearchError
|   +-- tests/                # pytest suite
|   +-- requirements.txt
|   +-- Dockerfile
+-- frontend/
|   +-- src/
|   |   +-- App.jsx            # Main app -- state + SSE wiring
|   |   +-- components/
|   |       +-- QueryInput.jsx     # Search box + example chips
|   |       +-- AgentTimeline.jsx  # Pipeline stations + log feed
|   |       +-- AgentCard.jsx      # Individual log entry
|   |       +-- FinalReport.jsx    # Markdown report + sources
|   +-- nginx.conf             # SPA fallback for the production image
|   +-- Dockerfile             # multi-stage: dev / build / nginx
+-- scripts/
|   +-- live_smoke.py          # end-to-end run against the real APIs
+-- docs/                      # plan, ADRs, dev log
+-- docker-compose.yml
+-- render.yaml
+-- .env.example
+-- README.md
```

## How It Works

1. **User submits a query** -- `POST /api/research` returns a `session_id`
2. **Frontend opens an SSE stream** -- `GET /api/research/{session_id}/stream`
3. **LangGraph runs in a background thread**, emitting events to a per-session queue
4. **FastAPI's SSE generator drains the queue**, forwarding `agent_update`,
   `report_token`, `complete` and `error` events
5. **Frontend renders** the agent timeline live, then the report as it streams in

### Events

| Event | Payload | When |
|---|---|---|
| `agent_update` | one log entry | an agent finishes a step |
| `report_token` | `{text}` | each chunk of the Writer's output |
| `complete` | report, sub-tasks, sources, unanswered sub-tasks | run finished |
| `error` | `{message}` | any node failed, or the run timed out |

A run is capped at `RESEARCH_TIMEOUT_SECONDS`. If any agent fails, the state
machine routes to `error_handler` and the frontend shows the message.

### Failure handling

A search that runs and matches nothing is *not* the same as a search that could
not run. Tavily calls retry with backoff and then raise `SearchError`; the
Researcher records which sub-questions are unanswered, and fails the whole run
only if every search failed. The Analyst refuses to synthesize when there are no
sources at all, rather than producing a confident report from nothing.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

40 tests covering search retry and failure semantics, researcher outcome
handling, graph routing predicates, session lifecycle and backpressure, CORS
configuration, an integration test that drives the real compiled graph through
a refine round, and an end-to-end test that runs the actual FastAPI app and
parses the real SSE stream. External APIs are faked, so the suite needs no keys
and makes no billable calls.

### Live smoke test

The suite proves the wiring; it does not prove that a real run produces a good
report. This script does, against the real Anthropic and Tavily APIs:

```bash
python scripts/live_smoke.py
python scripts/live_smoke.py --query "what is the state of fusion energy research"
```

It starts a real uvicorn server, submits a query over HTTP, consumes the SSE
stream while printing each agent's progress, and then checks that the report
streamed incrementally, that the streamed chunks reassemble into the final
report, that sources were cited, and that the Markdown structure asked for is
present. The report is written to `scripts/last_live_report.md` for review.

It makes **real, billable API calls** -- about three Claude calls plus one
Tavily search per sub-question -- which is why it is deliberately not part of
`pytest`. Exit codes: 0 success, 1 a check failed, 2 keys not configured.

## Deployment

- **Backend**: Deploy to [Render](https://render.com) -- `render.yaml` is
  included for one-click blueprint deploy. Set `CORS_ALLOW_ORIGINS` to your
  deployed frontend origin, and `CORS_ALLOW_ORIGIN_REGEX` if you want Vercel
  preview builds to work too. The service must stay on **one instance and one
  worker** -- see [ADR-005](docs/architecture-decisions.md).
- **Frontend**: Deploy to [Vercel](https://vercel.com) --
  `frontend/vercel.json` is included; set `VITE_API_URL` to your Render backend
  URL. Note that `VITE_*` variables are inlined at build time, so changing one
  requires a rebuild.

> On Render's free tier the backend spins down after inactivity; the first
> request after an idle period pays a cold start.

## Screenshots

**Home -- enter any research question:**

![Home screen](screenshots/app-home.png)

**Agents working -- live pipeline view:**

![Agents running](screenshots/app-running.png)

**Result -- full structured research report with citations:**

![Research report](screenshots/app-result.png)

## Future Improvements

- **Agent memory** -- persist prior research sessions so the Analyst can reference earlier findings
- **More tools** -- add Wikipedia, ArXiv, Google Scholar adapters
- **User-selectable depth** -- quick (1 search/task) vs deep (5 searches/task)
- **Export options** -- download as PDF or Notion page
- **Caching** -- cache Tavily results for identical sub-queries
- **Auth + history** -- save past research sessions per user
- **Redis-backed sessions** -- the prerequisite for running more than one worker
