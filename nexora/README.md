# Nexora - Secure, Token-Efficient Adaptive Coding Agent

> **Code with evidence.** A secure, token-efficient, adaptive coding agent for small Python repositories.

## Overview

Nexora is a coding agent built for the **Nebius x NVIDIA Global AI Hackathon**. It analyzes coding tasks, screens inputs for security risks, selects relevant code through a ranked and budgeted context pipeline, produces a plan, proposes patches through a routed NVIDIA Nemotron model, executes every action through a deterministic policy boundary inside a sandbox, validates results with an independent critic, and presents the diff and evidence for human review.

## Key Features

### 🔒 Security First
- **Security Invariant**: The model never receives unrestricted host access. Every file read, write, command, network request, and Git operation crosses the Tool Router and Policy Engine.
- **Policy Engine**: Deterministic decisions (ALLOW, ALLOW_WITH_MONITORING, REQUIRE_APPROVAL, DENY, QUARANTINE) with fail-closed behavior.
- **Approval Manager**: Scoped, expiring approvals - silence is NEVER approval.
- **Injection Detection**: Heuristic detection of prompt injection in repository content (advisory only).
- **Secret Protection**: No raw secrets in prompts, logs, or artifacts. Automatic redaction.

### ⚡ Token Efficiency
- **Context Optimizer**: Indexes, ranks, budgets, compresses, and caches repository context.
- **Efficiency Invariant**: Full repository never sent to model by default.
- **Cache**: Repository summaries, file/symbol summaries, normalized tool results, test results.

### 🤖 Adaptive Routing
- **Model Router**: Auto/fixed mode with visible routing reasons.
- **Provider Adapter**: Normalized OpenAI-compatible calls to Nebius/NVIDIA with timeouts, backoff, idempotency.
- **Candidate Tiers**: Nemotron Nano (simple), Super (moderate), Ultra (complex) - enabled after verification.

### 🧪 Validation & Evidence
- **Validator/Critic**: Layered checks (patch applies, syntax, lint, targeted tests, broader tests, security regression, diff review).
- **Loop Detection**: Stops repeated failed actions (threshold: 2 in demo, 3 in standard).
- **Audit Log**: Append-only, hash-chained record of every decision and action.
- **Evidence Export**: Downloadable run reports with policy decisions, test results, and limitations.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Browser   │────▶│  API Server  │────▶│  Run Orchestrator│
│  Workspace  │     │  (FastAPI)   │     │  (Worker Pool)  │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                    ┌──────────────┐               │
                    │  PostgreSQL  │◀──────────────┤
                    │  (Runs,      │               │
                    │   Events,    │               ▼
                    │   Audit)     │     ┌─────────────────┐
                    └──────────────┘     │  Sandbox        │
                                         │  (Token Factory)│
                                         └─────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Node.js 18+ (for frontend development)
- Nebius API key with NVIDIA Nemotron access
- Token Factory Sandbox access

### Backend Setup

```bash
cd nexora/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../.env.example .env
# Edit .env with your API keys

# Run database migration
cd ../database
python migrate.py

# Start backend
cd ../backend
uvicorn nexora.backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd nexora/frontend

# For development, serve with any static server
# e.g., using Python
python -m http.server 3000
```

## Configuration

### Budget Profiles
Two profiles are included by default:
- **demo**: 10 steps, 20 tool calls, 1 retry, 300s timeout, 8K input / 2K output tokens
- **standard**: 40 steps, 80 tool calls, 3 retries, 900s timeout, 50K input / 12K output tokens

### Model Registry
Models must be registered and enabled after verification:
```sql
INSERT INTO model_registry (model_id, display_name, provider, tier, context_capacity, max_output_tokens, supports_tools, supports_reasoning, is_enabled, verification_date, terms_reviewed)
VALUES ('nemotron-3-ultra', 'Nemotron 3 Ultra', 'nebius', 'ultra', 128000, 4096, true, true, true, NOW(), true);
```

### Policy Configuration
Policies are defined in `backend/config/policies.yaml`:
- Protected paths
- Denied/allowed commands
- Approval-required capabilities
- Monitoring capabilities

## API Endpoints

### Workspaces
- `GET /api/v1/workspaces` - List workspaces
- `POST /api/v1/workspaces` - Create workspace
- `GET /api/v1/workspaces/{id}` - Get workspace
- `PATCH /api/v1/workspaces/{id}` - Update workspace
- `DELETE /api/v1/workspaces/{id}` - Delete workspace

### Runs
- `POST /api/v1/runs` - Create run (analyzes task, creates plan)
- `GET /api/v1/runs` - List runs
- `GET /api/v1/runs/{id}` - Get run details
- `POST /api/v1/runs/{id}/start` - Start/continue run (accept plan)
- `POST /api/v1/runs/{id}/approve` - Approve/reject action
- `POST /api/v1/runs/{id}/cancel` - Cancel run

### Models & Profiles
- `GET /api/v1/models` - List enabled models
- `GET /api/v1/budget-profiles` - List budget profiles

## Run Lifecycle

```
QUEUED → ANALYZING → SECURITY_REVIEW → PLANNING → AWAITING_START
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────┐
│  EXECUTION LOOP                                             │
│  CONTEXT_BUILD → MODEL_STEP → POLICY_CHECK → EXECUTING      │
│       │              │              │            │           │
│       ▼              ▼              ▼            ▼           │
│  (build)        (infer)        (policy)      (sandbox)      │
│                                              │               │
│                                              ▼               │
│                                        VALIDATING           │
│                                              │               │
│                              ┌───────────────┴────────────┐  │
│                              ▼                           ▼  │
│                         PASSED                        FAILED  │
│                              │                           │    │
│                              ▼                           ▼    │
│                         COMPLETED              REPLANNING ◄──┘    │
│                                                          │        │
│                                                          ▼        │
│                          (budget exhausted?) → FAILED/BLOCKED     │
└──────────────────────────────────────────────────────────────┘
```

## Development

### Project Structure
```
nexora/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── core/          # Core components (policy, security, context, etc.)
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic services
│   │   ├── worker/        # Background worker/orchestrator
│   │   └── main.py        # FastAPI app entry
│   ├── config/            # Configuration
│   └── requirements.txt
├── frontend/
│   ├── styles/            # CSS (tokens, main)
│   ├── js/                # JavaScript (api, state, components, app)
│   └── index.html
├── database/
│   ├── schema.sql         # PostgreSQL schema
│   └── migrate.py         # Migration script
```

### Adding a New Tool
1. Add tool to `ToolName` enum in `backend/app/core/tools.py`
2. Add schema to `TOOL_SCHEMAS`
3. Add capability mapping to `TOOL_CAPABILITIES`
4. Implement execution in `LocalSandboxAdapter`
5. Add policy rules in `config/policies.yaml`

### Running Tests
```bash
cd nexora/backend
pytest -v --cov=nexora.backend.app
```

## Hackathon Compliance

This project follows the Nexora policy from the hackathon requirements:
- ✅ Real provider integration (Nebius/NVIDIA)
- ✅ Real sandbox execution (Token Factory)
- ✅ Deterministic policy engine
- ✅ Scoped, expiring approvals
- ✅ Hash-chained audit log
- ✅ No unrestricted shell execution
- ✅ No API keys in frontend
- ✅ No silent model switching
- ✅ No fallback services that break integration
- ✅ Evidence register (E01-E11)

## License

MIT License - See LICENSE file for details.

## Acknowledgments

Built for the **Nebius x NVIDIA Global AI Hackathon** using:
- NVIDIA Nemotron models via Nebius
- Token Factory Sandboxes
- FastAPI, SQLAlchemy, PostgreSQL
- Research from the Secure Token-Efficient Autonomous Coding Agent architecture
