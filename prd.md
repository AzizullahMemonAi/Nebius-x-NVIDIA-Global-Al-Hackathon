# Nexora — Product Requirements Document

Version: 3.0 | Updated: 3 October 2026 | Status: proposed implementation specification

Related files: [Architecture](architrcture.md), [Rules](rules.md), [Phases](phases.md), [Design](design.md).

**Revision note (v3.0).** This version merges the *Secure Token-Efficient Autonomous Coding Agent — Complete System Architecture v1.0* (28 Sep 2026) and the *Nexora AI* component diagram into the v2.0 hackathon specification. The PDF's security plane (Security Gateway, Policy Engine, Approval Manager, audit log, loop detection), Task Analyzer, Context Optimizer with index and cache, Validator/Critic, security evaluation suite and ablation baselines are now first-class requirements. Where the PDF's production-style choices (PostgreSQL, Redis, 900 s budgets) conflict with the hackathon MVP constraints, the MVP value is the default and the PDF value is documented as the `standard` profile. See [Architecture §3](architrcture.md) for the reconciliation table. "Nexora AI" is the diagram's working title; the product name remains **Nexora** unless the team decides otherwise.

## 1. What to build

Build **Nexora, a secure, token-efficient, adaptive coding agent** for small Python repositories. A developer describes a bug or a small feature. Nexora analyzes the task, screens inputs for risk, selects relevant code through a ranked and budgeted context pipeline, produces a plan, proposes a patch through a routed model, executes every action through a deterministic policy boundary inside a sandbox, validates the result with an independent critic, and presents the diff and evidence for human review.

Nexora's underlying product remains the **Secure Adaptive AI Inference and Optimization Layer** from the original master prompt. Its first application is coding. Security, context optimization, model selection, inference, evaluation and bounded repair are services inside that application.

Two invariants from the PDF architecture are binding on every feature:

- **Security invariant:** the model never receives unrestricted host access. Every file read, file write, command, network request and Git operation is mediated by a policy-controlled tool boundary.
- **Efficiency invariant:** the full repository is never sent to the model by default. Context is indexed, ranked, compressed, cached and budgeted before inference.

The product promise is: **"From a coding task to a reviewable patch, with visible tests, policy decisions, model decisions and context usage."** Efficiency and security improvements are hypotheses to measure, not claims already achieved.

## 2. Problem and target users

Developers often cannot tell why an agent selected a model, whether it omitted important code, what its commands can access, whether it obeyed instructions hidden in a repository, or whether a proposed fix actually passed tests. Nexora makes those decisions and evidence visible while enforcing boundaries in code the model cannot influence.

| User | Main problem | Desired outcome | MVP priority |
| --- | --- | --- | --- |
| Student or hackathon developer | Limited time and inference budget | Complete a small coding task with understandable evidence | Primary |
| Individual Python developer | Repetitive debugging and test writing | Review a focused patch instead of a large unverified rewrite | Primary |
| Small engineering team | Unclear permissions and model behavior | Inspect execution, policy decisions, approvals and costs | Secondary |
| AI infrastructure / security researcher | Difficulty comparing routing, context and security policies | Reproduce baseline versus optimized runs and adversarial cases | Secondary |

The first release is a browser application, not an IDE replacement. The first supported repository type is a small Python project with a reproducible pytest command and preinstalled dependencies. JavaScript/TypeScript and common configuration formats from the PDF scope are P1.

## 3. Hackathon product fit

Selected track: **Coding and Agentic Engineering**. The official overview describes code-writing, execution and testing using Token Factory Sandboxes. The shared platform requirement includes Nebius infrastructure and an NVIDIA open source model. Nexora meets this through a real Token Factory inference integration (OpenAI-compatible API), a verified NVIDIA Nemotron-family model in the main coding path, and the Token Factory sandbox adapter. A working demo URL, public source repository with an open source license and setup instructions, project description, public YouTube demonstration, and tool feedback form the submission package. [Official overview](https://nebiusglobalaihackathon.devpost.com/), checked 25 September 2026 (recheck before release).

Exact event policy and the team's operational checklist are centralized in [rules.md](rules.md). A provider logo, inactive SDK dependency or simulated execution is not implementation evidence.

## 4. Primary user journey

1. Open the application and choose one of three owned sample repositories.
2. Read the workspace boundary and select a task such as "Fix the failing empty-input test."
3. Choose **Auto** routing or a supported fixed model. Set a run budget within the deployment cap.
4. The **Task Analyzer** normalizes the task into objective, constraints, acceptance tests, risk class, likely artifacts and *proposed* capabilities. It grants nothing.
5. The **Security Gateway** labels content provenance, runs prompt-injection heuristics, assesses risk and issues a security decision with reasons. A blocked task shows the reason and an alternative.
6. Nexora builds the repository index and ranked context, then shows a short plan: hypothesis, files to inspect, tool sequence, tests, stop conditions and estimated budget.
7. The user reviews and starts the run. If any step needs elevated permission, the run pauses in `awaiting_approval` with a scoped, expiring request; silence is never approval.
8. Watch stage updates: context built, model selected, patch generated, policy checked, tests running, validation complete. Each tool request shows its policy decision.
9. If validation fails with budget remaining, Nexora replans using only new relevant evidence. The UI explains any model change. Repeating the same failed action triggers loop detection, a stop or a strategy change.
10. Review the final diff, critic findings, test evidence, blocked actions, limitations and usage.
11. Download the verified patch or keep it in the isolated review workspace. Applying it to an external repository remains a separate user action. Nexora never pushes.

For a blocked task, display the policy reason and an actionable alternative. For an unavailable provider, display a failed run and retry control; do not display a fabricated successful result.

## 5. Functional requirements

| ID | Capability | Priority | Acceptance criteria |
| --- | --- | --- | --- |
| F01 | Owned sample workspaces | P0 | Three versioned repositories load into separate sandbox workspaces; initial hashes recorded in a RepositorySnapshot |
| F02 | Natural-language task | P0 | Task length validated; empty and oversized input rejected with useful messages |
| F03 | Task Analyzer | P0 | Produces objective, constraints, acceptance tests, risk class, likely artifacts, proposed capabilities; output has no authority |
| F04 | Security Gateway | P0 | Content labeled by provenance and trust level; injection heuristics advisory; explicit SecurityDecision with reasons; protected files excluded |
| F05 | Policy Engine | P0 | Deterministic; returns ALLOW, ALLOW_WITH_MONITORING, REQUIRE_APPROVAL, DENY or QUARANTINE for every tool request; unknown capability defaults to DENY; errors fail closed |
| F06 | Plan before edits | P0 | Plan has hypothesis, files/symbols, tool sequence, tests, stop conditions, token and time estimate; planner cannot execute tools |
| F07 | Context Optimizer | P0 | Index, ranking, budget allocation, bounded compression, cache; retains task, current diff, relevant source, latest failure; omission manifest and token-estimation method recorded |
| F08 | NVIDIA inference | P0 | Main workflow includes successful real inference using a verified, permitted NVIDIA model through the provider adapter |
| F09 | Token Factory sandbox | P0 | Every file operation, patch and test executes through the actual sandbox service; no host-shell fallback |
| F10 | Typed Tool Router | P0 | Only typed tools (see Architecture §7); malformed or unknown schemas rejected before policy evaluation; no arbitrary model-supplied shell strings |
| F11 | Diff review | P0 | File paths, additions and deletions inspectable; changes outside allowed scope rejected |
| F12 | Validator / Critic | P0 | Layered checks (patch applies, syntax, lint, targeted tests, broader tests within budget, security regression, diff review); structured findings; model self-assessment cannot mark a failed run successful |
| F13 | Bounded repair and loop detection | P0 | Retry bounds follow the active budget profile; repeated identical failing action hits a threshold and stops or changes strategy; cancellation/deadline prevents further calls |
| F14 | Transparent routing | P0 | Auto/fixed mode visible; reason and model ID recorded; fixed mode never silently switches models; single-model state disclosed |
| F15 | Approval Manager | P0 | `awaiting_approval` state; approvals scoped, expiring and auditable; expired or rejected approval blocks the action; high-risk actions never auto-approved |
| F16 | Audit log | P0 | Append-only, redacted, hash-chained events for every model decision, tool request, policy decision, approval, execution result and stop reason |
| F17 | Usage and evidence | P0 | Stage timing, known token usage, test summary, evidence export; unavailable values remain unknown |
| F18 | Reliable run state | P0 | Refresh reconnects to persisted status; duplicate submit creates no duplicate work; every run ends in completed, failed, blocked, cancelled or timeout-failed |
| F19 | Security evaluation suite | P0 | Ten named adversarial cases (Architecture §13) with observed outcomes; all mandatory cases pass |
| F20 | Secret protection | P0 | No raw secret in prompts, repository snapshots, ordinary logs or artifacts; environment allowlist; output redaction and scanning |
| F21 | User repository upload | P1 | Size, extension, archive traversal and ownership checks implemented before enabling |
| F22 | JavaScript/TypeScript support | P1 | Separate fixtures, test command and index support; same policy engine |
| F23 | Scoped memory | P1 | User opts in; repository-scoped summaries with expiry and deletion controls |
| F24 | Semantic retrieval | P1 | Embedding index added only if measured to improve success or tokens over lexical + symbol ranking |
| F25 | Controlled Git commit | P1 | `git.commit` behind approval; `git.push` remains denied unless a separate approved workflow exists |
| F26 | MCP integrations | P2 | Only needed, reviewed servers; same broker authorization applies |
| F27 | Offline model optimization | P2 | Separate experiment report, compatible artifact and quality gate precede any production routing |

P0 is the demo-ready commitment. P1 follows only after P0 gates pass. P2 is research or post-hackathon work unless spare capacity produces verifiable value.

## 6. Context optimization and routing behavior

Pipeline (from the PDF): task query extraction → file candidate retrieval → symbol and reference retrieval → relevance ranking → budget allocation → context compression → cache lookup/write → model context package.

Start with deterministic optimization: exclude binaries, generated folders and secrets; retrieve and rank task-relevant source by keyword overlap, symbol/reference distance, import relationship, failing-test location, git-history signal and generated-file penalty; deduplicate repeated tool output; replace long tool output with structured failure summaries; preserve exact code around high-confidence symbols; summarize low-confidence supporting files. Never compress away the current error, test assertion, tool policy, security-relevant evidence, command text or an active API contract merely to meet a token target.

Recompute the context budget whenever the selected model changes. The usable budget is the model's verified context capacity minus output reservation and a safety margin. If essential context cannot fit, narrow the task or return an explicit limitation.

The cache may hold repository summaries, file/symbol summaries, normalized tool results and test results. It must never contain unredacted credentials or data outside the run's authorization scope.

In Auto mode, a rule-based router uses task complexity, budget, failing-test complexity, context size, observed reliability and previous failure. Candidate tiers from the PDF are Nemotron **Nano** (simple lookup/edit; low latency and cost), **Super** (moderate coding; tool use and quality) and **Ultra** (complex debugging; only if evaluation supports a quality gain). These are candidates, not facts: a tier is enabled only after an inference smoke test, capability check and terms review. Do not assume the largest model is best. Until two models pass integration and quality checks, the UI states that single-model routing is active. Model switching, supported reasoning settings and offline weight compression are distinct mechanisms.

Fixed mode respects the chosen model. If it cannot complete within policy, stop with evidence rather than selecting another model. All attempts count toward the same task budget. A denied operation can never be retried through a more capable model to bypass policy.

## 7. Evaluation and success measures

**Functional suite.** An owned suite of at least 12 small Python tasks. It covers the PDF's eight categories (bug fix, add function, add unit test, refactor, fix failing test, dependency update, modify API endpoint, debug runtime error) plus additional edge-case tasks. The dependency-update task changes a manifest only and is verified against a preinstalled, pinned offline package set; the main demo performs no live package installation. Held-out checks stay outside the agent's writable workspace. Freeze task inputs, initial commits, dependencies and expected outcomes before comparative evaluation.

**Security suite.** Ten named cases using synthetic secrets and owned fixtures: malicious README prompt injection; attempt to read an SSH key; attempt to read environment secrets; dangerous shell command; unauthorized network request; unauthorized Git push; malicious dependency installation; symlink/path traversal; shell escape through command substitution; exfiltration through test output or generated artifacts. The rules.md mandatory list (cross-session artifact access, protected-test edits, timeout enforcement, cancellation) is added to this suite.

**Baselines (ablation).** Baseline A: basic agent with a fixed approved model and simple context. Baseline B: A plus the security layer. Baseline C: A plus the token optimizer. Proposed: security plus token optimization. All receive the same sandbox restrictions, repository and deadline. Baseline A runs inside the sandbox too; it is "no Nexora policy layer", not "no isolation". Include unsuccessful attempts and retries in totals.

| Metric | Calculation or evidence | Proposed gate |
| --- | --- | --- |
| Task success | Held-out checks pass and patch scope permitted / attempted tasks | At least 9 of 12 tasks; disclose suite size |
| Regression | Existing tests fail after a previously passing baseline | No accepted patch with a known regression |
| Token change | `(baseline tokens − Nexora tokens) / baseline tokens × 100`; also context compression ratio | Seek improvement without reducing task success; no guaranteed percentage |
| Latency | Start to terminal result, including queue and retries | Report median and p95; investigate demo tasks over 180 s |
| Policy reliability | Named adversarial cases with observed outcome | No critical case results in an allowed action |
| False-positive blocks | Legitimate actions denied / legitimate actions attempted | Report; investigate any block in the core demo |
| Prompt-injection resistance | Injection cases where no policy-violating action executed / injection cases | All mandatory cases; detector hits reported separately |
| Approval frequency | Approvals requested per run | Report |
| Tool calls and retries | Counted per run | Report |
| Cost | Observed usage × dated applicable rates, plus sandbox costs when known | Unknown if pricing or usage is missing |
| Demo reliability | Three clean rehearsals from reset state | Three completed runs with matching evidence |

Use fixed seeds or deterministic settings where supported and repeated trials where budget allows. Report the number of trials and an interval; with few trials, state that intervals are wide. A successful test run is evidence for the tested behavior, not proof that arbitrary generated code is secure. If optimization worsens quality, ship the stable baseline route and describe the experiment honestly.

**Release gates (from the PDF, adapted).** Controlled internal use only if: no critical security test results in an allowed action; no raw secret appears in model context or ordinary logs; every tool action has a policy decision and audit record; sandbox escape tests are blocked; functional success is measured against Baseline A; token savings cause no unacceptable quality regression; every run terminates through completion, controlled failure, block, cancellation or timeout.

## 8. Nonfunctional requirements

- Keep provider keys server-side. Separate user sessions and workspace authorization.
- Persist run transitions and sanitized events before notifying the browser.
- Start with one application instance and a bounded worker pool. Do not advertise enterprise concurrency or multi-tenant isolation.
- Support keyboard operation, clear focus, readable diffs and status indicators with text.
- Ensure logs are bounded, sanitized and correlated by `run_id`, `step_id`, `request_id` and `trace_id`.
- Reproduce a demo from a clean checkout using a pinned dependency environment and documented configuration.
- Make cancellation effective for queued work and best-effort for in-flight provider operations; disclose any operation that cannot be cancelled immediately.
- Fail closed: policy errors, missing authorization, detector uncertainty and runtime anomalies never fall through to execution.

## 9. Explicit non-goals

Do not build a complete editor, unrestricted computer-use agent, arbitrary internet crawler, production deployment bot, multi-language compiler platform, autonomous payment flow or enterprise identity suite for the MVP. Also out of scope (from the PDF): autonomous production deployment; unreviewed `git push`, account, billing or credential-rotation actions; multi-tenant shared execution without strong tenant isolation; arbitrary model browsing; treating a detector or classifier as a complete security boundary; automatic installation from unknown package sources. Do not require distillation, pruning, quantization, Google ADK, MCP or a vector database merely because these appeared in research notes.

## 10. Original research mapped into this product

| Previous work | Nexora application |
| --- | --- |
| Cline/NLP and security — Azizullah and Asif | Task Analyzer, Security Gateway, Policy Engine, independent action checks and plan/review interaction |
| Token optimization/ADK and Headroom — G. Qasim | Repository index, ranking, budgets, safe compaction, cache and measurable before/after comparisons |
| ECC workflow — Jami | Plan → Test → Implement → Review → Verify → Remember → Improve |
| Odyssey multitask — G. Qadir | Run state machine, task dependencies, Approval Manager; one active coding task per sandbox initially |
| Runtime shifting and nanochat evaluation — Asif | Capability-aware routing, Validator metrics, real evaluation and bounded escalation |
| Interface and Google SDK research — Yesh Raj/Yash | Context, model and security panels; optional SDK only with a concrete need |
| Compression — Amir | Offline experiment lane, isolated from MVP delivery |
| Secure Token-Efficient Autonomous Coding Agent PDF and Nexora AI diagram | Component set, policy decisions, state machine, tool catalog, evaluation suites, release gates (see Architecture) |

Repository names above describe supplied research directions, not verified dependencies. Reuse code only after a separate license and suitability review.

## 11. Remaining after coding development ends

Code completion is not submission readiness. These items stay open until their evidence exists (full tracking in [phases.md §15](phases.md)):

- Real-world verification: provider access, permitted model IDs and capacities, sandbox confinement and egress behavior, quota and deployment budget.
- Benchmark execution and honest reporting: functional suite, security suite, four-baseline ablation, three clean rehearsals.
- Documents not produced by code: threat model, runbook, third-party notices, change log separating pre-existing research from new work.
- Submission package: evidence register E01–E11, 2:45 English video, project description, tool feedback, roster review, representative authorization, link check from a signed-out browser.
- Deferred product work: P1/P2 items above, PostgreSQL/Redis scale-out, stronger tenant isolation, OpenTelemetry export, tamper-evident audit storage beyond the hash chain, offline optimization.
- Post-submission care: availability owner, credit monitoring, preserved release tag.

## 12. Product completion checklist

- [ ] A new reviewer completes an owned coding task without developer assistance.
- [ ] The recorded model and sandbox evidence correspond to actual operations.
- [ ] Diff, tests, failures, blocked actions, approvals, cancellation and unknown metrics display correctly.
- [ ] Protected checks cannot be modified to manufacture success.
- [ ] All ten security cases and the rules.md mandatory cases have recorded outcomes.
- [ ] Baseline A/B/C and Proposed results are reproducible and clearly labeled.
- [ ] Every tool action in a sample run has a policy decision and audit record.
- [ ] Remaining P1/P2 work is described as future work in the submission.
- [ ] Release package passes the checks in rules.md and phases.md.

