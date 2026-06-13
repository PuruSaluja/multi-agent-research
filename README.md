# Multi-Agent Research Assistant

A full-stack web application where specialized AI agents collaborate in real-time
to answer complex research questions. Built as a portfolio project for AI/ML
Engineer and Agentic AI roles.

## Architecture

```
User Question
     â”‚
     â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    LangGraph State Machine                  â”‚
â”‚                                                             â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚ Planner  â”‚â”€â”€â”€â–¶â”‚ Researcher â”‚â”€â”€â”€â–¶â”‚ Analyst â”‚â”€â”€â”€â–¶â”‚Writerâ”‚ â”‚
â”‚  â”‚          â”‚    â”‚            â”‚    â”‚         â”‚    â”‚      â”‚ â”‚
â”‚  â”‚Breaks    â”‚    â”‚Tavily web  â”‚    â”‚Synthesize    â”‚Write â”‚ â”‚
â”‚  â”‚question  â”‚    â”‚search per  â”‚    â”‚findings â”‚    â”‚MD    â”‚ â”‚
â”‚  â”‚into 3-5  â”‚    â”‚sub-task    â”‚    â”‚& gaps   â”‚    â”‚reportâ”‚ â”‚
â”‚  â”‚sub-tasks â”‚    â”‚            â”‚    â”‚         â”‚    â”‚      â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚       â”‚               â”‚                â”‚              â”‚    â”‚
â”‚       â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â”‚
â”‚                          error_handler (any node)           â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
     â”‚
     â–¼ FastAPI SSE stream
     â”‚
     â–¼
React UI â€” real-time agent timeline + final Markdown report
```

### Agent Roles

| Agent | Role | LLM |
|---|---|---|
| **Planner** | Decomposes the query into 3-5 searchable sub-questions | Claude claude-sonnet-4-6 |
| **Researcher** | Calls Tavily search for each sub-question, collects top 3 results | Tavily API |
| **Analyst** | Synthesizes all search results, notes contradictions and uncertainty | Claude claude-sonnet-4-6 |
| **Writer** | Produces a structured Markdown report with citations | Claude claude-sonnet-4-6 |

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph + LangChain |
| LLM | Anthropic Claude claude-sonnet-4-6 |
| Web search | Tavily API |
| Backend | FastAPI + SSE streaming |
| Frontend | React 18 + Vite + Tailwind CSS |
| Containerization | Docker + docker-compose |

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes docker-compose)
- Anthropic API key â€” [console.anthropic.com](https://console.anthropic.com)
- Tavily API key (free tier) â€” [tavily.com](https://tavily.com)

> Alternatively, without Docker: Python 3.11+ and Node 18+

## Quick Start

### 1. Clone the repo
```bash
git clone <your-repo-url>
cd multi-agent-research
```

### 2. Add API keys
```bash
cp .env.example .env
# Edit .env and fill in your keys:
#   ANTHROPIC_API_KEY=sk-ant-...
#   TAVILY_API_KEY=tvly-...
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
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Getting API Keys

### Anthropic API Key
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up / log in â†’ API Keys â†’ Create Key
3. Copy the `sk-ant-...` key into `.env`

### Tavily API Key (free tier â€” 1,000 searches/month)
1. Go to [app.tavily.com](https://app.tavily.com)
2. Sign up â†’ Dashboard â†’ API Keys
3. Copy the `tvly-...` key into `.env`

## Example Queries

- *"What are the most promising applications of large language models in healthcare?"*
- *"What are the latest breakthroughs in quantum computing?"*
- *"How does Anthropic's approach to AI safety compare to OpenAI's?"*
- *"What are the most effective evidence-based treatments for insomnia?"*
- *"What is the current state of fusion energy research?"*

## Project Structure

```
multi-agent-research/
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ main.py               # FastAPI app â€” REST + SSE endpoints
â”‚   â”œâ”€â”€ graph.py              # LangGraph state machine
â”‚   â”œâ”€â”€ models.py             # ResearchState TypedDict
â”‚   â”œâ”€â”€ agents/
â”‚   â”‚   â”œâ”€â”€ planner.py        # Decomposes query â†’ sub-tasks (JSON)
â”‚   â”‚   â”œâ”€â”€ researcher.py     # Tavily search per sub-task
â”‚   â”‚   â”œâ”€â”€ analyst.py        # Synthesizes search results
â”‚   â”‚   â””â”€â”€ writer.py         # Produces final Markdown report
â”‚   â”œâ”€â”€ tools/
â”‚   â”‚   â””â”€â”€ search.py         # Tavily client wrapper
â”‚   â”œâ”€â”€ requirements.txt
â”‚   â””â”€â”€ Dockerfile
â”œâ”€â”€ frontend/
â”‚   â”œâ”€â”€ src/
â”‚   â”‚   â”œâ”€â”€ App.jsx            # Main app â€” state + SSE wiring
â”‚   â”‚   â”œâ”€â”€ components/
â”‚   â”‚   â”‚   â”œâ”€â”€ QueryInput.jsx     # Search box + example chips
â”‚   â”‚   â”‚   â”œâ”€â”€ AgentTimeline.jsx  # Pipeline stations + log feed
â”‚   â”‚   â”‚   â”œâ”€â”€ AgentCard.jsx      # Individual log entry
â”‚   â”‚   â”‚   â””â”€â”€ FinalReport.jsx    # Markdown report + sources
â”‚   â”‚   â””â”€â”€ index.css
â”‚   â”œâ”€â”€ package.json
â”‚   â”œâ”€â”€ vite.config.js
â”‚   â””â”€â”€ Dockerfile
â”œâ”€â”€ docker-compose.yml
â”œâ”€â”€ .env.example
â””â”€â”€ README.md
```

## How It Works

1. **User submits a query** â†’ `POST /api/research` â†’ returns `session_id`
2. **Frontend opens an SSE stream** â†’ `GET /api/research/{session_id}/stream`
3. **LangGraph runs in a background thread**, emitting events to a per-session queue
4. **FastAPI SSE generator polls the queue** and forwards events as `agent_update` / `complete` / `error`
5. **Frontend renders** log entries in real-time, then fades in the final Markdown report

The entire pipeline runs inside a 180-second timeout. If any agent fails, the
state machine routes to an `error_handler` node and the frontend shows the
error message.

## Screenshots

**Home â€” enter any research question:**

![Home screen](screenshots/app-home.png)

**Agents working â€” live pipeline view:**

![Agents running](screenshots/app-running.png)

**Result â€” full structured research report with citations:**

![Research report](screenshots/app-result.png)

## Future Improvements

- **Agent memory** â€” persist prior research sessions so the Analyst can reference earlier findings
- **More tools** â€” add Wikipedia, ArXiv, Google Scholar adapters
- **Streaming LLM output** â€” stream token-by-token from Claude for faster perceived response
- **User-selectable depth** â€” quick (1 search/task) vs deep (5 searches/task)
- **Export options** â€” download as PDF or Notion page
- **Fine-tuning** â€” fine-tune the Writer agent on high-quality research reports
- **Caching** â€” cache Tavily results for identical sub-queries
- **Auth + history** â€” save past research sessions per user
