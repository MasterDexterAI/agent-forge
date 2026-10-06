from prometheus_client import Counter, Gauge, Histogram

RUNS = Counter("agentforge_runs_total", "Finished runs by status", ["status"])
RUN_SECONDS = Histogram("agentforge_run_seconds", "Run wall time", buckets=(10, 30, 60, 120, 300, 600, 900))
ITERATIONS = Histogram("agentforge_iterations", "Test runs per finished run", buckets=(1, 2, 3, 4, 5, 6, 8))
LLM_TOKENS = Counter("agentforge_llm_tokens_total", "LLM tokens", ["agent"])
LLM_COST = Counter("agentforge_llm_cost_usd_total", "LLM cost in USD", ["agent"])
LLM_FAILURES = Counter("agentforge_llm_failures_total", "Failed LLM calls", ["model"])
SANDBOX_ACTIVE = Gauge("agentforge_sandboxes_active", "Running sandboxes")
SANDBOX_SECONDS = Histogram(
    "agentforge_sandbox_seconds", "Sandbox execution time", buckets=(1, 3, 10, 30, 60, 90)
)
SANDBOX_TIMEOUTS = Counter("agentforge_sandbox_timeouts_total", "Sandbox runs that hit the timeout")
