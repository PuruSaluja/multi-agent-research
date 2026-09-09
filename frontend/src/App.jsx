import { useState, useRef, useEffect } from "react";
import QueryInput from "./components/QueryInput";
import AgentTimeline from "./components/AgentTimeline";
import AnalysisPanel from "./components/AnalysisPanel";
import FinalReport from "./components/FinalReport";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const INITIAL_STATE = {
  status: "idle",
  agentLogs: [],
  finalReport: "",
  // Accumulated from `analysis_token` / `report_token` events so both appear
  // progressively instead of arriving whole when the run ends.
  streamingAnalysis: "",
  streamingReport: "",
  subTasks: [],
  sources: [],
  currentAgent: "",
  errorMessage: "",
};

export default function App() {
  const [state, setState] = useState(INITIAL_STATE);
  const [query, setQuery] = useState("");
  const esRef = useRef(null);

  useEffect(() => {
    return () => esRef.current?.close();
  }, []);

  async function handleSubmit(q) {
    // Close any existing stream
    esRef.current?.close();
    setQuery(q);
    setState({ ...INITIAL_STATE, status: "running" });

    let sessionId;
    try {
      const res = await fetch(`${API_URL}/api/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      sessionId = data.session_id;
    } catch (err) {
      setState((s) => ({
        ...s,
        status: "error",
        errorMessage: err.message ?? "Failed to start research",
      }));
      return;
    }

    const es = new EventSource(`${API_URL}/api/research/${sessionId}/stream`);
    esRef.current = es;

    es.addEventListener("agent_update", (e) => {
      const log = JSON.parse(e.data);
      setState((s) => ({
        ...s,
        agentLogs: [...s.agentLogs, log],
        currentAgent: log.agent,
      }));
    });

    es.addEventListener("analysis_token", (e) => {
      const { text } = JSON.parse(e.data);
      setState((s) => ({ ...s, streamingAnalysis: s.streamingAnalysis + text }));
    });

    es.addEventListener("report_token", (e) => {
      const { text } = JSON.parse(e.data);
      setState((s) => ({ ...s, streamingReport: s.streamingReport + text }));
    });

    es.addEventListener("complete", (e) => {
      const payload = JSON.parse(e.data);
      setState((s) => ({
        ...s,
        status: "complete",
        finalReport: payload.final_report,
        subTasks: payload.sub_tasks,
        sources: payload.sources,
        currentAgent: "",
      }));
      es.close();
    });

    es.addEventListener("error", (e) => {
      if (e.data) {
        const payload = JSON.parse(e.data);
        setState((s) => ({
          ...s,
          status: "error",
          errorMessage: payload.message ?? "An error occurred",
        }));
      } else {
        // SSE transport error
        setState((s) => {
          if (s.status === "running") {
            return { ...s, status: "error", errorMessage: "Connection lost" };
          }
          return s;
        });
      }
      es.close();
    });
  }

  function handleReset() {
    esRef.current?.close();
    setState(INITIAL_STATE);
    setQuery("");
  }

  const isRunning = state.status === "running";
  const showResults = state.status !== "idle";

  return (
    <div className="min-h-screen bg-gray-50">
      {!showResults ? (
        // Centered input view
        <div className="flex items-center justify-center min-h-screen px-4">
          <QueryInput onSubmit={handleSubmit} disabled={isRunning} />
        </div>
      ) : (
        // Results view
        <div className="max-w-5xl mx-auto px-4 py-8">
          {/* Header row */}
          <div className="flex items-start justify-between gap-4 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <button
                  onClick={handleReset}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-medium transition"
                >
                  ← New research
                </button>
              </div>
              <h2 className="text-xl font-semibold text-gray-900 max-w-2xl">{query}</h2>
            </div>
            <StatusBadge status={state.status} />
          </div>

          {/* Error banner */}
          {state.status === "error" && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
              <strong>Error:</strong> {state.errorMessage || "Something went wrong."}
              <button
                onClick={handleReset}
                className="ml-4 underline hover:no-underline"
              >
                Try again
              </button>
            </div>
          )}

          {/* Agent timeline — always visible while running or complete */}
          <section className="mb-8 bg-gray-50 border border-gray-200 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-gray-600 mb-4 uppercase tracking-wide">
              Agent Pipeline
            </h3>
            <AgentTimeline
              logs={state.agentLogs}
              currentAgent={state.currentAgent}
              status={state.status}
            />
          </section>

          {/* The Analyst's synthesis, streamed then collapsed once the
              Writer takes over */}
          <AnalysisPanel
            text={state.streamingAnalysis}
            streaming={isRunning && !state.streamingReport}
            collapsed={Boolean(state.streamingReport) || state.status === "complete"}
          />

          {/* Final report */}
          {state.status === "complete" && state.finalReport && (
            <FinalReport report={state.finalReport} sources={state.sources} />
          )}

          {/* The Writer's output, rendered as it streams in */}
          {isRunning && state.streamingReport && (
            <FinalReport report={state.streamingReport} sources={[]} streaming />
          )}

          {/* Running spinner, until any streamed output starts arriving */}
          {isRunning && !state.streamingReport && !state.streamingAnalysis && (
            <div className="flex items-center gap-3 text-gray-500 text-sm">
              <span className="inline-block w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
              Agents are working…
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    running: { label: "Running", cls: "bg-indigo-100 text-indigo-700" },
    complete: { label: "Complete", cls: "bg-green-100 text-green-700" },
    error: { label: "Error", cls: "bg-red-100 text-red-700" },
  };
  const { label, cls } = map[status] ?? {};
  if (!label) return null;
  return (
    <span className={`shrink-0 text-xs font-semibold px-3 py-1 rounded-full ${cls}`}>
      {label}
    </span>
  );
}
