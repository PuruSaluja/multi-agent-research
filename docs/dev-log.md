# Development Log

## June 17, 2026

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
