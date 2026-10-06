# Agent Forge Learner Guide

A step by step manual for understanding, running and deploying Agent Forge, a multi-agent system that turns a short prompt into tested Python code.

This guide is written for learners. You do not need to know everything before you start. Each concept is explained when it first matters.

## Table of contents

1. [What we are building and why](#1-what-we-are-building-and-why)
2. [The problem we started with](#2-the-problem-we-started-with)
3. [The big idea: the API never does the work](#3-the-big-idea-the-api-never-does-the-work)
4. [Core concepts explained](#4-core-concepts-explained)
5. [Tools, frameworks and libraries](#5-tools-frameworks-and-libraries)
6. [Project layout](#6-project-layout)
7. [Getting your API keys and secrets](#7-getting-your-api-keys-and-secrets)
8. [Run it on your machine](#8-run-it-on-your-machine)
9. [How one run works, step by step](#9-how-one-run-works-step-by-step)
10. [Building it phase by phase](#10-building-it-phase-by-phase)
11. [The backend in detail](#11-the-backend-in-detail)
12. [The frontend in detail](#12-the-frontend-in-detail)
13. [AI agent evals](#13-ai-agent-evals)
14. [Deployment, in phases](#14-deployment-in-phases)
15. [CI/CD for a team](#15-cicd-for-a-team)
16. [Monitoring and governance](#16-monitoring-and-governance)
17. [Security checklist](#17-security-checklist)
18. [Edge cases that will happen](#18-edge-cases-that-will-happen)
19. [Troubleshooting](#19-troubleshooting)
20. [Where to go next](#20-where-to-go-next)
21. [Glossary](#21-glossary)

---

## 1. What we are building and why

Agent Forge is a small software factory made of AI agents. You type a request such as "Create a module that parses durations like 1h30m into seconds, with validation." Five steps then happen, each handled by a different agent or tool:

| Step | Who | Job |
|---|---|---|
| 1 | Planner | Reads the request and writes a plan with the exact function signatures |
| 2 | Test Writer | Writes pytest tests from the plan only, before any code exists |
| 3 | Coder | Writes the code so those tests pass |
| 4 | Tester | Runs the tests inside a locked down sandbox container |
| 5 | Reviewer | Decides: approve, fix, replan, or ask a human |

You watch this happen live in a web page, and at the end you can download tested code.

You will learn a lot by building this because it touches many real world skills: working with AI models that sometimes misbehave, running untrusted code safely, background jobs, live streaming to a browser, databases, containers, deployment and automated testing.

## 2. The problem we started with

We started with a working local version. It had four agents sharing a folder on your laptop. It worked when everything went well, but it had serious weaknesses:

| Weakness | What goes wrong |
|---|---|
| The Tester wrote tests after seeing the code | The tests copy what the code does, not what the user asked for. Bugs become "expected behavior" and the tests pass. |
| The Coder returned a diff as free text | About one answer in ten had a broken diff header, so a whole run failed over formatting. |
| Models return broken JSON or go offline | One bad answer or one rate limit crashed the run. |
| The Coder could write `while True:` | The run hung forever. |
| The Coder could edit the tests | It changes a test to make it pass instead of fixing the bug. |
| A run happened inside the web request | One slow run blocks a connection, and a deploy kills it. |
| No limits, no logs, no metrics | You find out something is wrong when a user complains. |

The goal of this project is to fix all of these, step by step, until the system is safe enough to put on the internet.

## 3. The big idea: the API never does the work

A run takes one to five minutes, costs money, runs untrusted code and can fail at any step. So we split the system in two:

- The **API** only accepts work and reports on it. It answers in about 50 milliseconds.
- The **worker** does the slow, risky part in the background.

They talk through two shared services:

- **Postgres** stores everything that must last: runs, audit log, checkpoints.
- **Redis** holds the job queue and the live event stream.

```
Browser  ->  Next.js (Vercel)  ->  FastAPI  ->  Postgres
   ^                                  |              ^
   |                                  v              |
   +-------- live events <------  Redis  <----  Worker (LangGraph)
                                                     |
                                                     v
                                    LLM providers + Docker sandbox
```

Why this matters: if the worker crashes or you deploy a new version, the run is not lost. It resumes from its last checkpoint.

## 4. Core concepts explained

Read this section once. Later sections refer back to it.

### 4.1 Multi-agent systems

An agent is a model call with a role, a prompt and a task. A multi-agent system chains several of them so each does one narrow job well. Smaller jobs are easier to prompt, test and fix than one giant prompt.

### 4.2 LangGraph and the state machine

LangGraph lets you describe agents as nodes in a graph and describe how control flows between them with edges. Shared data lives in a **state** object. Each node reads the state and returns only the fields it changed.

Our graph has five nodes: planner, test_writer, coder, tester, reviewer. After the Reviewer, a conditional edge decides where to go next: back to the Coder (fix), back to the Planner (replan), or to the end.

### 4.3 Reducers

Three state fields use `operator.add`: `error_signatures`, `tokens_used`, `cost_usd`. A reducer tells LangGraph how to merge a node's update into the existing value. Instead of replacing the total, it adds the node's amount to it. This keeps the totals correct even when two nodes update in the same step.

### 4.4 Structured outputs with Pydantic

Agents do not answer in prose. Each one must return JSON that matches a Pydantic model (`Plan`, `TestSuiteSpec`, `CodePatch`, `Review`). If the JSON is invalid, the system shows the model the exact error and asks again. Models fix their own mistakes well when told what was wrong.

The Planner's `interface` field is the contract. It lists exact signatures and what errors to raise. The Test Writer and Coder both build against it, so they cannot disagree on names.

### 4.5 Tests before code (the most important idea)

If the same agent writes both code and tests, it grades its own homework. So we flip the order:

1. The Planner defines the interface.
2. The Test Writer writes tests from the plan alone and never sees code.
3. The tests are hashed with SHA-256 and locked.
4. The Coder can read the tests but cannot write under `tests/`. A guard blocks it.
5. The Reviewer recomputes the hash. If it changed, the run is rejected.

Now the tests are an independent opinion of what "correct" means.

### 4.6 Guards

Guards are plain Python checks that run on agent output before anything touches a sandbox. They are fast and never hallucinate. Ours check file paths, file types, file size, protected names, and hardcoded secrets.

### 4.7 Stagnation detection

Each failed test run is turned into a short fingerprint: numbers and memory addresses are replaced, then the first error line is hashed. If the same fingerprint appears twice in a row, the Coder is going in circles. More retries would waste money, so the system asks a human.

### 4.8 Human in the loop with interrupt()

When the Coder keeps failing, the Reviewer calls LangGraph's `interrupt()`. The run pauses, its state is saved in Postgres, and the browser shows a dialog with three choices: retry with a hint, replan, or stop. The user can close the tab and come back tomorrow.

One subtle rule: when a run resumes, the node runs again from the top, and this time `interrupt()` returns the human's answer. So everything before `interrupt()` must be safe to repeat. That is why the budget and failure checks are pure functions of state with no model calls.

### 4.9 Checkpoints and resumable runs

After every node, LangGraph saves a snapshot of the state to Postgres. If the worker crashes mid run, the retry sees which node is next and continues from there. You never pay for the Planner twice. A deploy is just a controlled crash.

### 4.10 Sandboxing untrusted code

Model written code is untrusted. We run it in a throwaway Docker container with these limits:

| Limit | What it prevents |
|---|---|
| No network | Downloading things, sending data out, reaching cloud metadata |
| Half a CPU, 512 MB, 64 processes | Fork bombs and memory bombs |
| 60 second timeout | Infinite loops |
| Read only filesystem with a writable workspace and /tmp | Writing where you do not expect |
| Non-root user, all capabilities dropped, no-new-privileges | Gaining power |
| gVisor runtime (production) | Kernel level escapes, because code talks to a user-space kernel |
| Container removed in a `finally` block, plus a cleanup cron | Leaked containers filling the disk |

### 4.11 Background jobs and queues

The API puts a job on a queue (ARQ on Redis) and returns right away. The worker pulls jobs and runs them. Job ids equal run ids, so the queue itself refuses duplicates.

### 4.12 Server-Sent Events and Redis Streams

To show progress live, the browser opens an `EventSource` to the API. Events come from a Redis **Stream**, not pub/sub. Pub/sub forgets a message the moment it is sent, so a dropped wifi connection loses events forever. A stream keeps a log with ids. When the browser reconnects, it sends `Last-Event-ID` and gets everything it missed. Opening a run page later replays the whole history.

### 4.13 Idempotency

A double click should not create two runs. The browser makes a random key per form load. The database has a unique constraint on `(user_id, idempotency_key)`, so the second insert is refused. Always enforce this in the database, not only in the frontend.

### 4.14 Two kinds of authentication

- The Next.js **server** calls the API with a shared internal key and tells it which user is acting. The browser never sees the key.
- The **browser** reads the stream directly using a short lived, HMAC signed token that unlocks only one run for one user. This exists because `EventSource` cannot send custom headers.

### 4.15 Fallbacks across providers (LiteLLM)

LiteLLM gives one function call for any provider. If Gemini returns a rate limit error, we move to the next model in the list. A network error means "try another provider". A validation error means "show the model its mistake and retry the same model."

### 4.16 Budgets

Three ceilings stop runaway runs: a cost limit, a token limit and an iteration limit. They are checked before any further work.

### 4.17 Observability

Two different questions need two different tools:

- "What did the Coder say on run 4812?" is answered by **Langfuse** traces.
- "Is the failure rate rising right now?" is answered by **Prometheus and Grafana** metrics.

### 4.18 Evals

An eval is a repeatable test of the whole agent system with a score. Without one, every prompt change is a guess. See [section 13](#13-ai-agent-evals).

## 5. Tools, frameworks and libraries

Every tool here is open source (or free to use) and understandable in an afternoon.

### Backend libraries

| Library | Why we use it |
|---|---|
| `langgraph` | State machine, routing, `interrupt()`, streaming |
| `langgraph-checkpoint-postgres` | Durable checkpoints so runs survive crashes |
| `litellm` | One API for all model providers, fallbacks, cost tracking |
| `pydantic`, `pydantic-settings` | Typed agent outputs and typed config from env vars |
| `fastapi`, `uvicorn` | The API, with automatic docs at `/docs` |
| `sse-starlette` | Server-Sent Events for live streaming |
| `arq` | Small async job queue on Redis |
| `redis` | Queue backend and Redis Streams |
| `psycopg[binary,pool]` | Postgres driver with connection pooling |
| `docker` | Python SDK to create sandbox containers |
| `prometheus-client` | Metrics endpoint |
| `structlog` | JSON logs |
| `pyyaml` | Eval task files |

Dev only: `pytest`, `pytest-asyncio`, `ruff`, `httpx`.

### Frontend libraries

| Library | Why |
|---|---|
| Next.js (App Router) | Server actions keep the internal key off the browser |
| shadcn/ui | Component source copied into your repo, so you own it |
| Tailwind CSS | Styling |
| Auth.js (next-auth v5) | GitHub login |
| `@xyflow/react` (React Flow) | The live agent graph |
| `@marsidev/react-turnstile` | Bot check widget |
| `sonner` | Toasts |

### Infrastructure tools

| Tool | Why |
|---|---|
| Docker and Compose | One file describes the whole backend |
| gVisor (`runsc`) | Sandbox runtime with its own user-space kernel |
| Caddy | Reverse proxy with automatic HTTPS |
| `tecnativa/docker-socket-proxy` | Limits what the worker can do with Docker |
| Prometheus and Grafana | Metrics and alerts |
| Uptime Kuma | External uptime checks |
| gitleaks | Secret scanning in CI |
| GitHub Actions | CI and deploy |

### Where things run

| Piece | Platform | Cost | Catch |
|---|---|---|---|
| Frontend | Vercel Hobby | Free | Non-commercial use only |
| API, worker, Postgres, Redis, sandboxes | Oracle Cloud Always Free ARM VM (2 CPU, 12 GB) | Free | ARM images needed, capacity sometimes unavailable |
| Uptime monitor | Oracle free AMD micro VM | Free | Tiny, but enough |
| LLM tracing | Langfuse Cloud Hobby | Free | Usage limits |
| Images | GitHub Container Registry | Free for public repos | Lowercase names only |
| Domain and TLS | DuckDNS and Caddy | Free | Ugly URL |
| Bot protection | Cloudflare Turnstile | Free | Not open source |
| Models | Gemini, Groq, OpenRouter free tiers | Free | Rate limits. Never send private code on free tiers |

Why a VM and not Render or Railway: our worker must start Docker containers, and most platform as a service products do not allow that.

## 6. Project layout

```
agent-forge/
├── agentforge/
│   ├── config.py            settings from environment variables
│   ├── metrics.py           Prometheus counters and histograms
│   ├── core/
│   │   ├── state.py         the shared graph state
│   │   ├── schemas.py       Pydantic models for agent output
│   │   ├── llm.py           structured_call with fallbacks and self repair
│   │   ├── guards.py        path, file, secret and error checks
│   │   ├── sandbox.py       Docker sandbox runner
│   │   ├── graph.py         LangGraph wiring
│   │   ├── db.py            Postgres pool and checkpointer
│   │   └── events.py        Redis Streams and the kill switch
│   ├── agents/              planner, tester, coder, reviewer nodes
│   ├── prompts/             system prompts and PROMPT_VERSION
│   ├── store/               migrations runner and run queries
│   ├── api/                 FastAPI app and security
│   └── worker/              ARQ worker
├── migrations/001_init.sql
├── evals/                   runner, report and task files
├── docker/                  sandbox and app Dockerfiles
├── deploy/                  Caddyfile, Prometheus config, backup script
├── compose.prod.yml         production stack
├── docker-compose.yml       local Postgres and Redis
├── frontend/                Next.js app
├── tests/                   unit and end to end tests
└── .github/                 workflows, CODEOWNERS, PR template
```

## 7. Getting your API keys and secrets

Never commit real keys. The file `.env` is ignored by git. Copy `.env.example` to `.env` and fill it in.

### 7.1 Model keys

| Key | Variable | How to get it |
|---|---|---|
| Gemini | `GEMINI_API_KEY` | Go to aistudio.google.com, sign in, choose Get API key. Free tier. |
| Groq | `GROQ_API_KEY` | Go to console.groq.com, create an account, open API Keys. Free tier. |
| OpenRouter (optional) | `OPENROUTER_API_KEY` | Go to openrouter.ai, open Keys. Use models marked free. |

Model names change often. Keep them in `.env`, never in code:

```
PLANNER_MODEL=gemini/gemini-3.1-flash-lite
TESTER_MODEL=gemini/gemini-3.1-flash-lite
CODER_MODEL=gemini/gemini-3.1-flash-lite
REVIEWER_MODEL=groq/openai/gpt-oss-120b
FALLBACK_MODELS=["groq/openai/gpt-oss-120b"]
```

To see which models your Groq key can use:

```bash
curl -s https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"
```

If a run fails with "model not found", a provider retired that model. Change one line in `.env` and restart the worker.

### 7.2 Secrets you generate yourself

Run this twice, once for each value:

```bash
openssl rand -hex 32
```

| Variable | Used for |
|---|---|
| `INTERNAL_API_KEY` | Frontend server to API. Must match in the backend `.env` and `frontend/.env.local`. |
| `STREAM_TOKEN_SECRET` | Signing live stream tokens. Backend only. |
| `AUTH_SECRET` (frontend) | Auth.js session encryption. Generate with `npx auth secret` or `openssl rand -hex 32`. |

### 7.3 GitHub login

1. On GitHub open Settings, then Developer settings, then OAuth Apps, then New OAuth App.
2. Homepage URL: `http://localhost:3001`
3. Callback URL: `http://localhost:3001/api/auth/callback/github`
4. Create the app, then copy the **Client ID** (it looks like `Ov23li...`, about 20 characters) and generate a **Client secret**.
5. Put them in `frontend/.env.local` as `AUTH_GITHUB_ID` and `AUTH_GITHUB_SECRET`.

Be careful: the long number shown as "App ID" is not the Client ID. If GitHub shows a 404 on the authorize page, you used the wrong value.

You need a second OAuth app for production, because each app allows only one callback URL.

### 7.4 Cloudflare Turnstile

For local work, use Cloudflare's official test keys (they always pass):

```
NEXT_PUBLIC_TURNSTILE_SITE_KEY=1x00000000000000000000AA
TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA
```

For production, create a widget at dash.cloudflare.com under Turnstile and use the real keys.

### 7.5 Optional services

| Service | Variables | How |
|---|---|---|
| Langfuse | `LANGFUSE_ENABLED=true`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | cloud.langfuse.com, create a project, create API keys |
| Discord webhook | GitHub secret `DISCORD_WEBHOOK` | Channel settings, Integrations, Webhooks |

### 7.6 Which variable starts with NEXT_PUBLIC_

Anything starting with `NEXT_PUBLIC_` is baked into the JavaScript that browsers download. Never give a secret that prefix. `INTERNAL_API_KEY` must never have it.

## 8. Run it on your machine

### 8.1 Prerequisites

| Need | Check with |
|---|---|
| Python 3.12 or newer | `python3 --version` |
| Node 20 or newer | `node -v` |
| Docker Desktop, running | `docker info` |
| Git | `git --version` |

### 8.2 Get the code and set up Python

```bash
git clone https://github.com/MasterDexterAI/agent-forge.git
cd agent-forge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 8.3 Create the backend `.env`

```bash
cp .env.example .env
```

Fill in at least:

```
DATABASE_URL=postgresql://forge:forge@localhost:5433/agentforge
REDIS_URL=redis://localhost:6379/0
INTERNAL_API_KEY=<random 64 hex characters>
STREAM_TOKEN_SECRET=<another random 64 hex characters>
FRONTEND_ORIGIN=http://localhost:3001
SANDBOX_RUNTIME=runc
WORKSPACE_ROOT=/tmp/af-work
GEMINI_API_KEY=<your key>
GROQ_API_KEY=<your key>
```

Notes:

- The database port is 5433 because many machines already run a local Postgres on 5432. If yours does not, you can use 5432 and edit `docker-compose.yml` to match.
- `SANDBOX_RUNTIME=runc` is required on a Mac. gVisor only runs on Linux.
- `WORKSPACE_ROOT` must be a folder that exists: `mkdir -p /tmp/af-work`.

### 8.4 Start Postgres and Redis, build the sandbox, run migrations

```bash
docker compose up -d
docker build -t agentforge-sandbox:latest -f docker/sandbox.Dockerfile .
mkdir -p /tmp/af-work
python -m agentforge.store.migrate
```

### 8.5 Run the tests with fake models

The fake mode uses saved JSON answers instead of calling a model, so tests are free and repeatable:

```bash
LLM_MODE=fake pytest -q
```

You should see all tests pass. This includes an end to end test that runs the full graph against a real Docker sandbox.

### 8.6 Start the API and the worker

Open two terminals, both with the virtualenv active.

```bash
# terminal 1
uvicorn agentforge.api.app:app --reload --port 8000

# terminal 2
arq agentforge.worker.worker.WorkerSettings
```

Check it:

```bash
curl localhost:8000/readyz
```

### 8.7 Try a run without the frontend

```bash
curl -s -X POST localhost:8000/v1/runs \
  -H "X-Internal-Key: $INTERNAL_API_KEY" -H "X-User-Id: me" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create slugify.py with slugify(text: str) -> str that lowercases, trims, and joins words with hyphens","idempotency_key":"test-1"}'
```

Copy `run_id` and `stream_token` from the answer, then watch events:

```bash
curl -N "localhost:8000/v1/runs/$RUN_ID/stream?token=$TOKEN"
```

You will see `node` events for planner, test_writer, coder, tester and reviewer, then a `done` event with `"status": "approved"`.

### 8.8 Start the frontend

```bash
cd frontend
cp .env.example .env.local
# fill in AUTH_SECRET, AUTH_GITHUB_ID, AUTH_GITHUB_SECRET, and INTERNAL_API_KEY (same as backend)
npm install
npm run dev -- -p 3001
```

Open http://localhost:3001.

### 8.9 Log in

- **GitHub login:** use the button once your OAuth keys are set.
- **Demo login (development only):** the header shows "Demo login (dev)". It signs you in as a fake user so you can test without GitHub. This button exists only when `NODE_ENV=development`. It is never available in a production build.

All demo sessions share one user, so they share the daily quota of 5 runs. To reset it:

```bash
docker compose exec postgres psql -U forge -d agentforge -c "delete from runs where user_id='demo-user'"
```

### 8.10 Do users need GitHub to use the product?

Yes. In this version GitHub login is the only sign in method. It is quick for developers and gives a stable numeric user id for quotas. Visitors without an account can see only the landing page. A later improvement is to let anonymous visitors watch a recorded replay.

## 9. How one run works, step by step

1. The user logs in and types a prompt.
2. The Next.js server action checks the Turnstile token, then calls `POST /v1/runs` with the internal key and the user id.
3. The API checks the kill switch, prompt length and daily quota. It inserts the run (with the idempotency key), enqueues a job with `_job_id = run_id`, and returns the run id and a stream token.
4. The browser goes to `/runs/{id}` and opens an `EventSource` to `/v1/runs/{id}/stream?token=...`.
5. The worker picks up the job and streams the graph:
   - Planner writes the plan and interface.
   - Test Writer writes pytest tests from the plan and the tests are hashed.
   - Coder writes code.
   - Tester runs everything in a fresh sandbox.
   - Reviewer decides what happens next.
6. Each node completion becomes an event in the Redis stream. The browser lights up that agent in the graph.
7. If the Coder fails three times, or repeats the same error, the graph calls `interrupt()`. The run pauses and the UI shows a dialog.
8. On approval the worker stores the final files, plan, review, cost and iteration count.

The reviewer is the traffic controller. Its order of checks is deliberate, cheapest first:

1. Budget exceeded? Stop.
2. Tests failing? If stuck or out of iterations, ask a human. Otherwise send back to the Coder. No model call.
3. Test hash changed? Reject.
4. Secret pattern in the code? Reject.
5. Only now ask the Reviewer model for a judgment.

## 10. Building it phase by phase

This is the order the project was built and the order we recommend you follow. Each phase makes the next one easier to debug.

| Phase | Name | What you do | Done when |
|---|---|---|---|
| 0 | Freeze the local core | Tag the working version, write three prompts that work | You have a known good point |
| 1 | Harden the core | Structured JSON, LiteLLM fallbacks, fake LLM mode, hardened sandbox, guards, locked tests, stagnation, budgets | `pytest` passes in fake mode and a real run is approved |
| 2 | Evals baseline | Ten tasks with hidden tests, save a baseline | You have numbers before changing prompts |
| 3 | Service layer | Migrations, FastAPI, ARQ worker, Redis Streams, stream tokens, quotas, idempotency, resume | You can `curl` a run and watch events |
| 4 | Observability | Langfuse, Prometheus metrics, structured logs, Grafana | You can see failures as they happen |
| 5 | CI | Lint, tests, sandbox integration test, gitleaks, frontend build, multi-arch images | Every pull request is checked |
| 6 | Deploy the backend | Oracle VM, Docker, gVisor, Compose, Caddy, backups | `/readyz` returns ok on the VM |
| 7 | Frontend | Auth, new run, live run page, human dialog, my runs | The UI works against real endpoints |
| 8 | Soft launch | Share with a small group, 5 runs per user per day, watch dashboards | Failures become new eval tasks |
| 9 | Public launch | Turnstile on, quotas enforced, kill switch tested, landing page | You post it |

The rule behind the order: Core, then evals, then service, then observability, then CI, then deploy, then frontend, then users. If you catch yourself working two phases ahead, ask what you will debug it with.

In this repository, phases 1, 3, 5 (config), 6 (config) and 7 are implemented. Phase 2 has the runner and three starter tasks. Phase 4 has the metrics and the Prometheus and Grafana config. The VM setup and soft launch are steps you perform.

## 11. The backend in detail

### 11.1 Configuration (`agentforge/config.py`)

All settings come from environment variables through `pydantic-settings`. Nothing is hardcoded, so the same image runs on your laptop, in CI and on the server.

### 11.2 Agent output schemas (`core/schemas.py`)

`Plan`, `TestSuiteSpec`, `CodePatch` and `Review` define what each agent may return. Full file contents in JSON replaced the old diff format because it is boring and reliable.

### 11.3 The LLM layer (`core/llm.py`)

`structured_call(model, system, user, schema, meta)`:

1. In fake mode, return a saved fixture.
2. Otherwise add the JSON schema to the system prompt.
3. For each candidate model (primary first, then fallbacks): call it, extract JSON (handles code fences and chatter), validate it with Pydantic.
4. On a provider error, move to the next model right away.
5. On a validation error, show the model the error and try once more.
6. Record tokens and cost in Prometheus.

Cost on free tiers shows list price, not what you paid. Keep it anyway: it tells you what the system would cost on paid models.

### 11.4 Guards (`core/guards.py`)

- `safe_path` rejects absolute paths, `..`, deep paths and unknown file types.
- `validate_code_files` blocks the Coder from writing tests, `conftest.py` or protected folders.
- `validate_test_files` forces tests under `tests/`.
- `hash_files` makes the lock hash, independent of file order.
- `scan_secrets` looks for AWS keys, private keys, GitHub tokens and similar.
- `compress_error` keeps only assertion lines, failed test names and stack frames so the Coder is not drowned in noise.
- `error_signature` produces the fingerprint used for stuck detection.

### 11.5 The sandbox (`core/sandbox.py`)

Files are written to a fresh workspace folder, a container is started with all the limits from section 4.10, the tests run with a `timeout` command, and the container and folder are deleted afterwards. A semaphore allows at most two sandboxes at once. Exit code 124 or 137 means a timeout. Pytest exit code 5 (no tests collected) counts as a failure on purpose.

### 11.6 The service layer

| File | Purpose |
|---|---|
| `migrations/001_init.sql` | Tables: `runs`, `audit_log`, `eval_results` |
| `store/migrate.py` | Applies numbered SQL files once each |
| `store/runs.py` | Create, read, update runs and write the audit log |
| `core/db.py` | Connection pool and the LangGraph checkpointer |
| `core/events.py` | Publish and read Redis Streams, plus the kill switch |
| `api/security.py` | Internal key check and signed stream tokens |
| `api/app.py` | The HTTP endpoints |
| `worker/worker.py` | `execute_run`, cleanup cron, metrics server on port 9101 |

Rule for migrations: never edit one that has run in production. Add `002_...sql` instead, and keep every migration additive.

### 11.7 API endpoints

| Method and path | Purpose |
|---|---|
| `GET /healthz` | Process is alive |
| `GET /readyz` | Database and Redis reachable, queue size |
| `GET /v1/quota` | Runs used and left today |
| `POST /v1/runs` | Create a run |
| `GET /v1/runs` | List my runs |
| `GET /v1/runs/{id}` | Run details and a fresh stream token |
| `POST /v1/runs/{id}/resume` | Answer a human question |
| `POST /v1/runs/{id}/cancel` | Cancel a run |
| `GET /v1/runs/{id}/stream` | Live events (needs the signed token) |

Every "not yours" case returns 404, not 403, because 403 would confirm that the run exists.

### 11.8 The worker and crash recovery

`execute_run` decides how to start:

- Human answered a question: resume with `Command(resume=...)`.
- A checkpoint exists with a next node: continue from it.
- Fresh job: start from the initial state.

A cron job every ten minutes removes orphan sandbox containers, deletes old workspaces, and marks runs stuck for 45 minutes as failed.

## 12. The frontend in detail

### 12.1 Routes

| Route | What the user sees |
|---|---|
| `/` | Landing page with the pitch, the five agents and example prompts |
| `/new` | Prompt box, example chips, quota left, Turnstile, Run button |
| `/runs` | Table of past runs with status, iterations and cost |
| `/runs/[id]` | Live graph, tabs and the human dialog |

### 12.2 Key files

| File | Purpose |
|---|---|
| `src/auth.ts` | Auth.js setup with GitHub (and the dev-only demo login) |
| `src/lib/api.ts` | Server-only helper that calls the backend with the internal key |
| `src/app/new/actions.ts` | Server actions: create run, resume run, Turnstile check |
| `src/hooks/use-run-stream.ts` | Opens the `EventSource` and collects events |
| `src/lib/derive.ts` | Turns a list of events into one view object |
| `src/components/agent-graph.tsx` | The React Flow graph |
| `src/components/hitl-dialog.tsx` | The human decision dialog |
| `src/components/run-view.tsx` | Tabs: Timeline, Plan, Tests, Code, Test output, Review |

### 12.3 Two ideas worth understanding

**The page is a pure function of events.** The `deriveView` reducer folds the event list into a snapshot. Because events replay from the start of the Redis stream, refreshing the page or opening it on your phone shows the same view.

**`import "server-only"`.** The file that holds the internal key starts with this line. If any client component imports it, the build fails. A security mistake becomes a compile error.

### 12.4 Theme

The design tokens live in `src/app/globals.css`. Light is the default theme. A `.dark` class provides dark values. shadcn components read these variables, so changing the file restyles everything. This version of shadcn uses Base UI, so buttons do not support `asChild`. Use `buttonVariants` on a `Link` instead.

### 12.5 Adding a v0 template or new component

1. Run the command v0 gives you, for example `npx shadcn@latest add "<v0 url>"`, inside `frontend/`.
2. Keep the data files (`api.ts`, `derive.ts`, `use-run-stream.ts`, `actions.ts`) and restyle only the presentation.
3. Run `npm run lint`, `npx tsc --noEmit` and `npm run build`.

## 13. AI agent evals

An eval is a repeatable experiment: run the whole agent system on a fixed set of tasks and measure the results. Without it, "the new prompt feels better" is only an opinion.

### 13.1 What we measure

| Metric | Meaning | Why it matters |
|---|---|---|
| Approve rate | Runs the Reviewer approved | Headline number |
| Hidden test pass rate | Runs that also pass tests the agents never saw | The real correctness |
| False approve rate | Approved runs that fail the hidden tests | Your trust metric. Aim for zero. |
| pass^k | Fraction of tasks where all k attempts succeeded | Reliable versus lucky |
| Cost and iterations per solved task | Spend per success | Becomes your pricing |

A confident but wrong system is worse than one that says "I could not do it."

### 13.2 A task file

Each task in `evals/tasks/*.yaml` has an `id`, a `prompt` (what a user would type) and `hidden_tests` (the ground truth the agents never see). Write hidden tests like an adversary: cover boundaries and invalid inputs, not only the happy path.

Starter tasks included: `slugify`, `roman`, `lru_cache`.

### 13.3 Running evals

```bash
python -m evals.run --suite smoke --repeats 1 --out eval-report
python -m evals.run --suite full --repeats 3 --out evals/baseline
```

This calls real models, so it needs your API keys and Docker. Output files: `results.json`, `summary.json`, and `discord.json`.

### 13.4 The habit

1. Save a baseline before changing anything.
2. After any prompt, model or logic change, run the evals and compare.
3. Hidden pass rate up or flat: good.
4. False approve rate up: reject the change, even if the pass rate rose.
5. Cost jumps with no gain: not worth it.
6. Put before and after numbers in the pull request.

You can make the nightly job fail on regressions with `EVAL_MIN_HIDDEN_PASS` and `EVAL_MAX_FALSE_APPROVE` environment variables.

### 13.5 Where tasks come from

Every real failure in production should become a new eval task with hidden tests that encode the correct behavior. The suite then grows from real usage.

### 13.6 What good looks like

With free models on small standard library tasks, expect a hidden pass rate of about 60 to 85 percent. Do not chase 100. Chase a false approve rate near zero and a high pass^k.

### 13.7 Ideas to improve the agents (measure each one with evals)

1. Better prompts with a worked example for the Coder, and assumptions stated by the Planner.
2. Route simple tasks to cheaper models.
3. Search and replace edits on fix iterations instead of full rewrites.
4. Retrieve similar solved tasks as examples (pgvector).
5. A second Reviewer model; approve only if both agree.
6. Property based tests with Hypothesis.
7. Work inside real repositories (a big step, do it last).
8. Let the Planner ask one clarifying question.

Bump `PROMPT_VERSION` in `agentforge/prompts/__init__.py` whenever you change any prompt. It is attached to every trace so you can compare versions.

## 14. Deployment, in phases

The architecture has two machines: Vercel for the frontend and one Oracle Cloud ARM VM for everything else. Deploy in this order.

### Phase A: Prepare the repository

- CI is green on `main`.
- Secrets are not in git (see [section 17](#17-security-checklist)).
- Images build for both amd64 and arm64.

### Phase B: Create the VM

1. Create an account at cloud.oracle.com. Choose your home region carefully because it cannot be changed.
2. Create an instance: Ubuntu 24.04 aarch64, shape `VM.Standard.A1.Flex`, 2 OCPU, 12 GB, 100 GB boot volume, with your SSH public key.
3. In the VCN security list, allow TCP 80 and 443 from anywhere.
4. Set a billing alert at 1 dollar.
5. If you see "out of capacity", try another availability domain or another hour.

### Phase C: Prepare the server

```bash
ssh ubuntu@YOUR_VM_IP
sudo apt update && sudo apt -y upgrade
sudo timedatectl set-timezone UTC
```

Open ports 80 and 443 in the VM firewall as well (Oracle images block them by default), add a 4 GB swap file, then install Docker:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
```

### Phase D: Install gVisor

gVisor puts a user-space kernel between the sandbox and the host. Follow the install steps at gvisor.dev for your architecture, run `sudo runsc install`, restart Docker, then check:

```bash
docker run --rm --runtime=runsc hello-world
docker run --rm alpine uname -r
docker run --rm --runtime=runsc alpine uname -r
```

The last command should print a different, fake kernel version.

### Phase E: Folders, code and domain

```bash
sudo mkdir -p /srv/agentforge/workspaces /srv/agentforge/backups
sudo chown -R 1000:1000 /srv/agentforge/workspaces
sudo chown -R ubuntu:ubuntu /srv/agentforge/backups
cd /srv/agentforge && git clone https://github.com/MasterDexterAI/agent-forge.git app
```

Claim a free subdomain at duckdns.org and point it to the VM's public IP. Caddy needs a domain name to get a free HTTPS certificate.

The workspace folder must have the same path on the host and inside the worker container. The host Docker daemon resolves bind mounts on the host, so a mismatch gives an empty `/workspace` in the sandbox.

### Phase F: Production `.env` on the VM

```
IMAGE=ghcr.io/your-user/agent-forge
TAG=latest
API_DOMAIN=yourname.duckdns.org
POSTGRES_PASSWORD=<long random>
DATABASE_URL=postgresql://forge:<same password>@postgres:5432/agentforge
REDIS_URL=redis://redis:6379/0
INTERNAL_API_KEY=<long random>
STREAM_TOKEN_SECRET=<long random>
FRONTEND_ORIGIN=https://your-app.vercel.app
SANDBOX_RUNTIME=runsc
SANDBOX_IMAGE=agentforge-sandbox:latest
WORKSPACE_ROOT=/srv/agentforge/workspaces
GEMINI_API_KEY=...
GROQ_API_KEY=...
GRAFANA_PASSWORD=<long random>
```

Then `chmod 600 .env`.

### Phase G: First deploy by hand

Do it manually once so you understand what CI will automate.

```bash
cd /srv/agentforge/app
docker build -t agentforge-sandbox:latest -f docker/sandbox.Dockerfile .
docker compose -f compose.prod.yml pull
docker compose -f compose.prod.yml up -d postgres redis
docker compose -f compose.prod.yml run --rm api python -m agentforge.store.migrate
docker compose -f compose.prod.yml up -d
curl https://yourname.duckdns.org/readyz
```

Run the curl test from section 8.7 against the real domain. When a run finishes `approved` inside gVisor, the backend is live.

What the production stack contains (`compose.prod.yml`):

| Service | Purpose |
|---|---|
| caddy | HTTPS reverse proxy. Blocks `/metrics`. |
| api | FastAPI |
| worker | ARQ worker, mounts the workspace folder |
| docker-proxy | Limits what the worker can ask Docker to do |
| postgres | Database with 50 max connections. No public port. |
| redis | Queue and streams. `noeviction` and append-only so jobs are not lost. |
| prometheus, grafana | Metrics and dashboards |

Postgres and Redis have no published ports. Publishing a database port is how databases get attacked within hours.

### Phase H: Backups

`deploy/backup.sh` dumps the database nightly and deletes dumps older than seven days. Add it to cron (`0 3 * * *`). Copy dumps off the machine weekly and test a restore once. An untested backup is a hope, not a backup.

### Phase I: Uptime monitor

Run Uptime Kuma on the second free micro VM, not on the same machine you monitor. Add monitors for `/readyz` and your Vercel URL, and a Discord notification.

### Phase J: Deploy the frontend on Vercel

1. Import the GitHub repository on vercel.com.
2. Set Root Directory to `frontend`.
3. Add every variable from `frontend/.env.example` with production values. `API_URL` and `NEXT_PUBLIC_API_URL` both point to `https://yourname.duckdns.org`.
4. Create a production GitHub OAuth app with your Vercel URL as the callback.
5. Set `FRONTEND_ORIGIN` on the VM to the Vercel URL, otherwise the browser blocks the stream request (CORS).
6. Use real Turnstile keys.

Vercel gives every pull request a preview URL. Previews are for visual review. Test login on production and locally.

### Phase K: Turn on automatic deploys

Add GitHub repository secrets `DEPLOY_HOST` and `DEPLOY_SSH_KEY` (a dedicated key pair, never your personal key), then add a repository variable `DEPLOY_ENABLED` set to `true` (Settings, Secrets and variables, Actions, Variables). Until that variable exists, the release workflow builds images but skips the deploy job. In Settings, Environments, create `production` with required reviewers so merging and deploying are two separate decisions.

### Rolling back

Every image is tagged with its commit SHA:

```bash
TAG=<previous sha> docker compose -f compose.prod.yml up -d api worker
```

Migrations do not roll back, so keep them additive.

### Capacity

On the free 2 core VM, expect roughly two concurrent runs and 30 to 60 runs an hour. When that is not enough, add another VM as a worker. Workers only talk to Redis and Postgres, so nothing else changes.

## 15. CI/CD for a team

### 15.1 The flow

Issue, branch, pull request, CI checks and a Vercel preview, review, merge, build images, manual approval, deploy over SSH, smoke check on `/readyz`.

### 15.2 Workflows

| File | What it does |
|---|---|
| `ci.yml` | Backend: ruff, format check, sandbox build, migrations, pytest. Frontend: lint, type check, build. Secrets: gitleaks. |
| `release.yml` | Builds multi-architecture images to GHCR, then deploys after approval |
| `evals.yml` | Nightly or manual real model evals, report to Discord |

Why CI uses fake models: pull requests from forks cannot read your secrets, and a provider outage should never block a typo fix.

### 15.3 Branch protection (set in GitHub settings)

- Require a pull request and one approval, including code owners.
- Require the checks `backend`, `frontend` and `secrets`.
- Require branches to be up to date.
- Block force pushes.

### 15.4 Working together

One issue, one branch, one pull request. Keep pull requests small (under about 300 lines). Anyone who changes agent behavior adds an eval task and pastes before and after numbers.

### 15.5 Pre-commit

```bash
pip install pre-commit
pre-commit install
```

This runs ruff and gitleaks on your laptop before each commit.

## 16. Monitoring and governance

### 16.1 Langfuse: the story of one run

Set `LANGFUSE_ENABLED=true` and the keys. Every model call is traced with the run id, agent name and prompt version. Use it to answer "why did the Coder do that on this run?"

### 16.2 Prometheus and Grafana: the fleet

The API exposes `/metrics` (never public) and the worker exposes port 9101. Build four panels and alert on each:

| Number | Meaning |
|---|---|
| Run failure rate | Often means a provider is down or a model name was retired |
| LLM failure rate | Rate limits or an outage |
| Cost per hour | Zero on free tiers, important once you pay |
| Sandbox timeout rate | Looping code or an overloaded machine |

### 16.3 The kill switch

Set `ACCEPT_NEW_RUNS=false` in the environment, or flip it instantly without a redeploy:

```bash
docker compose -f compose.prod.yml exec redis redis-cli set kill_switch:accept_runs 0
```

Set it back to `1` to resume. New runs get a 503 while running ones finish.

### 16.4 The audit log

`audit_log` records run created, resumed, cancelled and escalated. Rows are never updated. One query answers "who did what and when."

### 16.5 Honest safety notes

The system limits abuse with no sandbox network, hard resource limits, per user quotas, a Planner that refuses harmful requests, and gVisor. You still owe users a way to report abuse and a privacy note: prompts and code are stored, and free tier models may see them. Do not let anyone run private or sensitive code on the free public version.

### 16.6 A weekly ritual

Fifteen minutes a week: check the four numbers, read three traces and one failure, scan the audit log, pick one failing eval task to fix, and confirm a backup restores.

## 17. Security checklist

- `.env` and `frontend/.env.local` are never committed. `.env` was removed from git tracking. Only `.env.example` files are in the repository.
- No secret has the `NEXT_PUBLIC_` prefix.
- `INTERNAL_API_KEY` is read only in server code (`src/lib/api.ts` starts with `import "server-only"`).
- Stream tokens are HMAC signed, short lived and tied to one run and one user.
- Comparisons of secrets use `hmac.compare_digest`.
- Users can only read their own runs. Others get 404.
- The sandbox has no network and strict limits.
- The demo login exists only in development.
- If a key ever leaks, rotate it immediately at the provider. Deleting it from git history is not enough.
- gitleaks runs in CI and in pre-commit.

## 18. Edge cases that will happen

Each one is handled on purpose. The fix is always one of four moves: a hard limit, a fresh sandbox, an independent check, or a durable checkpoint.

| Symptom | Fix |
|---|---|
| Model returns broken JSON | Extract JSON, validate, show the error, retry once |
| Provider rate limits mid run | Fall back to the next model |
| Coder writes an infinite loop | 60 second timeout in the sandbox |
| Fork bomb or memory bomb | Process, memory and CPU limits |
| Agents grade their own homework | Tests first, hashed and locked |
| Coder edits the tests | Guard blocks writes, Reviewer rechecks the hash |
| Coder repeats the same error | Error fingerprints, then ask a human |
| Run costs too much | Cost, token and iteration ceilings |
| Two users click Run at once | Concurrency limits and a queue |
| Double click on Run | Database idempotency and job id |
| User closes the tab | Run continues, events replay later |
| Wifi drops while streaming | Redis Streams and `Last-Event-ID` |
| Worker crashes or deploy mid run | Checkpoints and automatic retry |
| Someone abandons a human question | Run waits at no cost (add a sweep if you want) |
| A container leaks | `finally` cleanup and a cron sweep |
| Workspace is empty in the sandbox | Same path on host and worker |
| Someone guesses another run id | Ownership check and 404 |
| Prompt injection | No network, secret scan, Planner refusal |
| A model is retired | Change one line in `.env` |
| Postgres connections run out | Pool sizes below the server limit |
| Huge test output | Clip and compress before prompting |

## 19. Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `role "forge" does not exist` | A local Postgres is using port 5432. Use the Docker one on 5433 and check `DATABASE_URL`. |
| `ModuleNotFoundError: agentforge` in pytest | Run from the repo root. `pytest.ini` sets `pythonpath = .`. |
| Run fails with `LLMError ... model_not_found` | A model was retired. List models for your key and update `.env`. |
| Worker cannot start sandboxes | Docker is not running, or the sandbox image is not built. |
| Sandbox sees an empty `/workspace` | Workspace path differs between host and worker. |
| GitHub shows 404 on login | `AUTH_GITHUB_ID` is the App ID, not the Client ID. |
| `exec format error` on the VM | Image was not built for arm64. Use the multi-arch release build. |
| Browser blocks the live stream | `FRONTEND_ORIGIN` on the backend does not match your frontend URL. |
| Demo login button missing | You are not running `npm run dev`. It is development only. |
| Daily limit reached while testing | Delete the demo user's runs (see section 8.9). |
| `timeout: command not found` on Mac | Use `curl --max-time 120` instead. |

## 20. Where to go next

The most useful real world uses of this architecture, in order:

1. A test backfill tool that writes tests for existing files and opens a pull request with the ones that pass.
2. A good first issue solver that proposes small fixes.
3. Dependency bump repair.
4. Small legacy migrations.
5. Coding practice with real feedback for students.

The pattern across all of them: propose, never merge without a human, verify before showing, and pick work people dislike doing by hand.

Suggested first extension: add a mode that reads one existing file, writes tests for its functions, runs them, and prints the ones that pass.

## 21. Glossary

| Term | Plain meaning |
|---|---|
| Agent | A model call with a role and a prompt |
| State | The shared data every graph node reads and updates |
| Node and edge | A step in the graph, and the arrow between steps |
| Reducer | A rule for merging an update into existing state |
| Checkpoint | A saved snapshot of state after each node |
| Interrupt | A deliberate pause waiting for a human |
| Guard | A plain code check on agent output |
| Sandbox | A locked down container for untrusted code |
| gVisor | A user-space kernel that adds a wall around containers |
| Queue | A waiting line of jobs |
| Worker | A process that takes jobs from the queue |
| SSE | Server-Sent Events, a one way live stream to the browser |
| Redis Stream | A log of events with ids that can be replayed |
| Idempotency | Doing the same request twice has the effect of once |
| HMAC | A signature made with a shared secret |
| Eval | A repeatable scored test of the whole agent system |
| Hidden tests | Tests the agents never see, used to judge correctness |
| False approve | The Reviewer approved code that was actually wrong |
| pass^k | All k attempts at a task succeeded |
| Fallback | Switching to another model when one fails |
| Kill switch | A flag that stops new runs instantly |
| CORS | A browser rule about which sites may call an API |
| ARM | The CPU architecture of the Oracle VM and Apple Silicon |
