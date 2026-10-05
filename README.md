# Nexora — Secure, Token-Efficient Adaptive Coding Agent

> **Code with evidence.** A secure, token-efficient, adaptive autonomous coding agent for small Python repositories. Built for the **Nebius x NVIDIA Global AI Hackathon** (Coding and Agentic Engineering track).

---

## 🌟 Highlights

- **🔒 Security Invariant:** The model never receives unrestricted host access. Every file read, file write, shell command, network call, and Git operation is mediated by a typed Tool Router and a deterministic Policy Engine running in a sandboxed environment.
- **⚡ Efficiency Invariant:** The full repository is never sent to the model by default. Context is indexed (AST symbols & imports), ranked, compressed, cached, and strictly budgeted before inference.
- **🤖 Adaptive Routing:** Auto and fixed routing across NVIDIA Nemotron tiers (Nano, Super, Ultra) via Nebius Token Factory inference, plus multi-provider registry support with clear routing justification.
- **🛡️ Deterministic Policy Engine:** Evaluates all capabilities against declarative policies (`ALLOW`, `ALLOW_WITH_MONITORING`, `REQUIRE_APPROVAL`, `DENY`, `QUARANTINE`) with strict fail-closed behavior.
- **⏳ Scoped Approvals:** Human-in-the-loop approvals are single-action, expiring, and auditable. Silence is *never* approval.
- **🧪 Layered Validation & Critic:** Multi-stage checks (clean patch application, Python syntax compilation, linting, targeted tests, security regression checks, and diff review).
- **📜 Append-Only Audit Trail:** Tamper-evident SHA-256 hash-chained event logs for every action and decision.
- **💻 Odysseus Developer Workspace:** Fast, responsive UI with dedicated panels for real-time runs, planning, policy feeds, security audits, diff inspection, and test metrics.

---

## 🏛️ System Architecture

```
┌──────────────────────────────────────────────────────────┐
│              Browser Workspace (Odysseus UI)             │
│        (Runs, Plans, Policy, Security, Diff, Tests)       │
└────────────────────────────┬─────────────────────────────┘
                             │ REST / SSE
                             ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI Backend API Service                 │
└──────────────┬────────────────────────────┬──────────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────────┐   ┌────────────────────────┐
│     SQLite / PostgreSQL     │   │    Run Orchestrator    │
│  (18 Relational Entities,   │◀──│ (Finite State Machine) │
│    SHA-256 Audit Chain)     │   └───────────┬────────────┘
└─────────────────────────────┘               │
       ┌────────────────────────┬─────────────┴──────────┬────────────────────────┐
       ▼                        ▼                        ▼                        ▼
┌──────────────┐       ┌─────────────────┐      ┌─────────────────┐      ┌────────────────┐
│ Task Analyzer│       │ Security Gateway│      │Context Optimizer│      │  Model Router  │
│(Requirements,│       │ (Provenance &   │      │ (AST Ranking,   │      │(NVIDIA Nemotron│
│ Constraints) │       │Injection Checks)│      │ Budget & Cache) │      │  via Nebius)   │
└──────────────┘       └────────┬────────┘      └─────────────────┘      └────────┬───────┘
                                │                                                 │
                                ▼                                                 ▼
                       ┌─────────────────┐                              ┌─────────────────┐
                       │ Approval Manager│                              │   Tool Router   │
                       │(Expiring Grants)│                              │ (Typed Schemas) │
                       └─────────────────┘                              └────────┬────────┘
                                                                                 │
                                                                                 ▼
                                                                        ┌─────────────────┐
                                                                        │  Policy Engine  │
                                                                        │ (Deterministic) │
                                                                        └────────┬────────┘
                                                                                 │
                                                                                 ▼
                                                                        ┌─────────────────┐
                                                                        │ Sandbox Adapter │
                                                                        │ (Isolated Exec) │
                                                                        └────────┬────────┘
                                                                                 │
                                                                                 ▼
                                                                        ┌─────────────────┐
                                                                        │Validator /Critic│
                                                                        │ (Layered Tests) │
                                                                        └─────────────────┘
```

---

## 📂 Repository Layout

```
.
├── nexora/                      # Primary Application Core
│   ├── backend/                 # FastAPI service
│   │   ├── app/
│   │   │   ├── api/             # REST endpoints (/workspaces, /runs, /models, etc.)
│   │   │   ├── core/            # Security gateway, policy engine, context optimizer, router, validator
│   │   │   ├── models/          # SQLAlchemy relational models (18 tables)
│   │   │   ├── schemas/         # Pydantic schemas and API contracts
│   │   │   └── worker/          # Run orchestrator and state machine
│   │   ├── config/              # policies.yaml and application settings
│   │   └── requirements.txt     # Python backend dependencies
│   ├── database/                # Schema DDL (PostgreSQL & SQLite) and migrations
│   ├── fixtures/                # Reproducible test fixture workspaces
│   │   ├── sample-calculator/   # Buggy calculator (failing empty-input test)
│   │   ├── sample-api/          # FastAPI schema validation bug
│   │   └── sample-cli/          # CLI argument parsing bug
│   └── frontend/                # Browser application (Odysseus UI, CSS themes, modular JS)
│
├── NVidia Hackathon Documents/  # Research reports, architecture diagrams, and review papers
├── prd.md                       # Product Requirements Document (PRD v3.0)
├── architrcture.md              # Complete System Architecture & Specifications
├── design.md                    # Design System and UI Specifications
├── phases.md                    # Rebased Phased Delivery Plan & Milestones
├── rules.md                     # Hackathon Compliance & Evidence Register (E01-E11)
├── repair_schema.py             # Schema reconciliation utility
├── seed_demo_data.py            # Idempotent fixture & model seed script
└── check_tables.py              # SQLite table verification utility
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ (optional, for frontend dev server)
- Nebius API key with NVIDIA Nemotron access (or local development mode)

### 2. Backend Setup
```bash
cd nexora/backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
# Edit .env with your keys (NEBIUS_API_KEY, etc.)
```

### 3. Initialize Database & Seed Demo Data
```bash
# From repository root:
python repair_schema.py
python seed_demo_data.py
```

### 4. Run the Backend Server
```bash
cd nexora/backend
uvicorn nexora.backend.app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 5. Launch the Frontend
In another terminal, serve the frontend static files:
```bash
cd nexora/frontend
python -m http.server 3000
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Run Lifecycle State Machine

```
QUEUED ──► ANALYZING ──► SECURITY_REVIEW ──► PLANNING ──► AWAITING_START
                                                               │
                                                               ▼ (Accept Plan)
┌──────────────────────────────────────────────────────────────┴──────────┐
│  EXECUTION LOOP                                                         │
│  CONTEXT_BUILD ──► MODEL_STEP ──► POLICY_CHECK ──► EXECUTING            │
│        │                 │               │              │               │
│        ▼                 ▼               ▼              ▼               │
│   (AST Index)      (Inference)     (Deterministic)  (Sandbox)           │
│                                                         │               │
│                                                         ▼               │
│                                                    VALIDATING           │
│                                                         │               │
│                                ┌────────────────────────┴────────────┐  │
│                                ▼                                     ▼  │
│                             PASSED                                FAILED│
│                                │                                     │  │
│                                ▼                                     ▼  │
│                            COMPLETED                       REPLANNING◄──┘
└────────────────────────────────┬────────────────────────────────────────┘
                                 ▼
                     TERMINAL: COMPLETED | FAILED | BLOCKED | CANCELLED
```

---

## 🛡️ Hackathon Compliance & Evidence Register

| Evidence ID | Description | Location / Artifact |
| :--- | :--- | :--- |
| **E01** | Real inference trace via Nebius / NVIDIA Nemotron | `nexora/backend/app/core/router.py` |
| **E02** | Sandboxed execution record | `nexora/backend/app/core/tools.py` |
| **E03** | Interactive UI with diff, tests & review | `nexora/frontend/` |
| **E04** | Clean setup log and deployment | `phases.md`, `README.md` |
| **E05** | License & dependency notices | `LICENSE`, `nexora/backend/requirements.txt` |
| **E06** | Change log & development lineage | `phases.md`, `NVidia Hackathon Documents/` |
| **E07** | Project description & demo narrative | `prd.md`, `architrcture.md` |
| **E08** | Ablation evaluation framework (Baselines A, B, C, Proposed)| `prd.md §7`, `phases.md §8` |
| **E09** | Team roster and contribution mapping | `phases.md §2`, `rules.md` |
| **E10** | Security evaluation suite (10 adversarial cases) | `rules.md §3`, `prd.md §7` |
| **E11** | Append-only SHA-256 audit log export | `nexora/backend/app/core/audit.py` |

---

## 📄 Documentation

- [Product Requirements Document (PRD)](prd.md)
- [System Architecture](architrcture.md)
- [Design System & Interface](design.md)
- [Phased Delivery Plan](phases.md)
- [Hackathon Rules & Compliance](rules.md)

---

## ⚖️ License

Distributed under the [MIT License](LICENSE). Built for the **Nebius x NVIDIA Global AI Hackathon**.
