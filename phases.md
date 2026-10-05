# Nexora — Phased Delivery Plan

Version: 3.0 | Planning baseline rebased: 3 October 2026

Related: [PRD](prd.md), [Architecture](architrcture.md), [Rules](rules.md), [Design](design.md).

All dates below are proposed internal targets. Official timing is centralized in rules.md. The v2.0 calendar began 26 September; this version **rebases the remaining work from 3 October 2026**. If Phase 0 or Phase 1 items were already completed, mark them done with evidence and pull later phases forward. The plan assumes the seven two-person workstreams from the master prompt are available; individual availability has not been confirmed.

## 1. Delivery strategy

Finish a thin, real coding workflow first, **with the policy boundary in it from the start** (the PDF's security invariant is not a late add-on). Add measurable context optimization and transparent routing after it works. Preserve the three-plane design without forcing offline model training into the critical path.

Critical dependency sequence: provider access → inference and sandbox smoke tests → validated contracts and policy engine skeleton → one tested patch through the full policy path → security suite and approvals → optimization comparison (Baselines A/B/C/Proposed) → complete UI → reproducible deployment → evidence package.

Research can proceed alongside implementation, but no critical feature is complete until it works in the shared application.

## 2. Team ownership

| Lead / two-person workstream | Primary delivery | Review partner |
| --- | --- | --- |
| Asif | Provider adapter, capability registry, Model Router, Validator/Critic metrics, evaluation harness | Qasim and Jami |
| G. Qasim | Repository index, ranking, budgets, compaction, cache, token comparisons | Asif and Aziz |
| Amir | Baseline B/C configuration support; optional offline compression | Asif |
| Azizullah/Aziz | Task Analyzer rules, Security Gateway, injection detector, Policy Engine and policy YAML, secrets, security suite | Qadir |
| G. Qadir | State machine, worker, persistence, Approval Manager, audit chain, sandbox adapter, loop guard, deployment | Aziz and Asif |
| Yesh Raj/Yash | Browser application, model/context/security panels, approval dialog, diff and test UX | Jami |
| Jami | Acceptance criteria, test workflow, integration review, release evidence, runbook | All leads |

Appoint one technical integration owner and one submission representative in Phase 0. These can be existing leads. Treat 14 people as the working team structure, not an organizer-approved roster; perform the roster check in rules.md.

## 3. Milestone calendar (rebased)

| Phase | Proposed dates, 2026 | Deliverable | Exit gate |
| --- | --- | --- | --- |
| 0 — Access and scope | Oct 3–4 | Verified provider path, frozen MVP, chosen budget profile values | Real inference and sandbox evidence |
| 1 — Skeleton and contracts | Oct 5–7 | API, worker, state machine, policy engine skeleton, audit chain, frontend shell | One persisted run visible after refresh; one denied tool request audited |
| 2 — Coding vertical slice | Oct 8–11 | Analyze, plan, patch, policy-checked sandbox tests, critic, review | One owned bug-fix task succeeds end-to-end |
| 3 — Security and acceptance | Oct 12–15 | Full gateway, approvals, command/path/secret policies, security suite | All ten PDF cases plus mandatory cases pass |
| 4 — Context and routing | Oct 16–19 | Index, ranking, cache, loop detection, optional second tier, A/B/C/Proposed runs | Fair comparison report |
| 5 — Product experience | Oct 20–22 | Complete accessible workflow including security and approval UI | Independent user rehearsal |
| 6 — Reliability and deployment | Oct 23–25 | Reproducible release candidate | Clean setup plus three rehearsals |
| 7 — Submission preparation | Oct 26–28 | Evidence E01–E11, video, finalized entry draft | Representative review complete |
| Buffer | Oct 29 | Only critical fixes and access checks | Stable tagged build |

The official window closes 30 October 2026 at 10:00 Pacific (22:00 Pakistan time); the internal target is an entry ready two days before closing. Do not use the final day as the first deployment day. The calendar is compressed compared with v2.0 (about 26 days remain); use the scope-reduction rules in §12 early rather than late.

## 4. Phase 0 — Access, rules and scope

**Owners:** Asif, Qadir, Aziz, representative.

1. Confirm track and scope using the current documents; recheck official pages.
2. Test actual account access, quota, permitted model IDs, context capacities and usage reporting. Record which Nemotron tiers (Nano, Super, Ultra) are actually available.
3. Run one harmless command in the actual sandbox service; record image, credential scope, lifecycle, timeout and cleanup behavior.
4. Verify whether required confinement and network restrictions are supported.
5. Pick owned Python fixtures and establish their initial tests.
6. Decide `demo` profile numbers (steps, tool calls, tokens, deadline) from measured latency.
7. Review licenses, participant roster and any ambiguous event condition.
8. Freeze P0 scope and choose the integration owner.

**Exit evidence:** redacted provider trace, sandbox operation record, approved fixture manifest, model registry draft and decision log. If sandbox access is blocked, resolve access before building UI around an imaginary integration. A local mock supports development only and cannot satisfy the exit gate.

## 5. Phase 1 — Shared skeleton and contracts

**Owners:** Qadir, Aziz, Yash, Asif; Jami reviews.

Implement the proposed file structure, typed contracts (TaskAnalysis, SecurityDecision, ToolRequest, PolicyDecision, Approval and the rest of Architecture §13) and configuration loading. Create the database schema including `policy_decisions`, `approvals` and hash-chained `audit_events`. Build the run queue, worker leases, the state machine from Architecture §11 and the event stream. Implement the Tool Router and a Policy Engine skeleton with default-deny and fail-closed behavior. Add a frontend shell with real API connectivity.

Define fixtures for contract tests. Explicitly mark development adapters as mocks. Implement session authorization and artifact access checks early.

**Exit criteria:** create a run, observe its events, reload the browser, recover persisted state, reject cross-session access, and show one deliberately denied tool request with its policy decision and audit row. Contract examples are reviewed by all consuming workstreams.

## 6. Phase 2 — First real coding task

**Owners:** Qadir and Asif; Aziz on policy; Yash builds the review surface.

Build the smallest complete path: task → Task Analyzer → Security Gateway (basic) → plan → plan acceptance → NVIDIA inference → typed tool requests → Policy Engine → sandbox → deterministic test result → critic → reviewable artifact. Use one approved model and simple context before optimizing.

Run initial tests before the patch to establish the failure. Preserve the initial snapshot. Keep protected evaluator checks separate from editable source. Return clear failure states for invalid patches, unavailable providers and unsuccessful tests.

**Exit criteria:** an owned bug-fix fixture completes without manual file repair; every tool action in the run has a policy decision and audit record; the UI's patch hash matches the tested artifact; a reviewer can inspect test evidence and download the patch.

## 7. Phase 3 — Security and acceptance gates

**Owners:** Aziz, Jami and Qadir.

Complete the Security Gateway (provenance labels, injection heuristics, risk analyzer), canonical path handling, structured command policy, environment allowlist, secret redaction and scanning, safe output rendering and bounded logs. Build the Approval Manager (`awaiting_approval`, scope, expiry, owner check). Add global deadlines, action limits, cancellation, cleanup and restoration of the workspace before retry.

Exercise the ten PDF cases (README injection, SSH key read, environment secret read, dangerous shell command, unauthorized network request, unauthorized Git push, malicious dependency install, symlink/path traversal, command-substitution escape, exfiltration through test output) plus cross-session access, protected-test edit, oversized output, expired session, provider timeout and worker restart. Use synthetic credentials.

**Exit criteria:** every case has a recorded outcome (E10); no critical case results in an allowed action; a denied operation cannot be retried through a more capable model; a process restart does not duplicate an uncertain action; false-positive blocks on legitimate demo actions are counted.

## 8. Phase 4 — Context, routing and measurement

**Owners:** Qasim and Asif; Amir assists evaluation.

Implement the Python `ast` symbol index, ranking, budget allocation, bounded compaction, output deduplication, cache and loop detection. Display selected and omitted context and whether token counts are estimated or reported.

Freeze the benchmark suite (at least 12 functional tasks). Run **Baseline A, B, C and Proposed** under equal sandbox restrictions, with repeated trials where budget allows. Add a second model only if access, compatibility and quality are verified; implement visible route reasons and fixed-model behavior before advertising automatic switching.

**Exit criteria:** reproducible report with success, tokens, compression ratio, latency, tool calls, retries, policy denials and failures; no claimed improvement without observed evidence. If a policy reduces success, retain the reliable configuration and document the failed experiment.

## 9. Phase 5 — Complete user experience

**Owners:** Yash and Jami.

Implement all important UI states (including security review, awaiting approval, policy-denied, quarantined, loop-stopped and budget-exhausted), responsive layout, keyboard operation, focus behavior and informative errors. Build the context panel, model control, security panel, approval dialog, route history, diff viewer, test summary, audit view and evidence export.

Give a person who did not implement the UI only the setup instructions and a sample task. Observe hesitation; fix unclear labels and missing state before adding decorative effects.

**Exit criteria:** independent reviewer completes the core journey; failed, blocked, cancelled and awaiting-approval runs remain understandable. No placeholder success numbers remain in the real demo.

## 10. Phase 6 — Deployment and reliability

**Owners:** Qadir, Jami and Aziz.

Deploy the single-host architecture with persistent state and HTTPS. Exercise clean setup, reset, secrets configuration, quota exhaustion and reconnect behavior. Verify the public application's restrictions and ensure one visitor cannot retrieve another visitor's artifacts or audit export.

Run three rehearsals from clean fixture state. Keep a known-good release tag and a documented rollback procedure in `docs/runbook.md`. Freeze nonessential dependencies, prompts and policy files after the release candidate passes.

**Exit criteria:** deployable clean checkout, matching model/policy/profile versions, no critical security defect, three evidenced core runs. A recording is not a substitute for fixing the live application.

## 11. Phase 7 — Submission package

**Owners:** representative, Jami and Yash; all leads supply evidence.

Complete the E01–E11 register in rules.md. Prepare a concise narrative: audience, task, distinctive implementation, real integration, measured results and limitations. Explain what was built during the project period and what came from earlier research and the supplied architecture.

Suggested 2:45 demo storyboard:

| Time | Show |
| --- | --- |
| 0:00–0:20 | The developer problem and one concrete task |
| 0:20–0:45 | Workspace, plan and model/context controls |
| 0:45–1:30 | Real patch generation and sandbox test evidence |
| 1:30–1:55 | Diff review, outcome and model decision |
| 1:55–2:25 | A visible security boundary: injected README instruction or denied command, with the policy decision and audit row |
| 2:25–2:45 | Measured comparison, honest limitations and repository/demo references |

If footage is shortened, label time compression. Record clean English audio, readable text and no sensitive material. Check every link from a signed-out browser before the representative submits.

## 12. Scope reduction rules

| If this happens | Keep | Cut or defer |
| --- | --- | --- |
| Second model is unreliable | One real verified model and visible fixed mode | Automatic model switching claims |
| Context compaction hurts quality | Relevant-file selection and omission report | Aggressive summarization |
| Upload isolation is incomplete | Reviewed fixture repositories | Arbitrary uploads |
| UI schedule slips | Task, progress, diff, tests, model/context and security panels | Animations, dashboards, audit explorer polish |
| Offline work overruns | Benchmarks supporting core runtime | Training, pruning and quantization |
| Integration is blocked | Resolve actual access and test the path | Decorative integration screens |
| Calendar compression bites | Policy Engine, sandbox, critic, security suite, Baseline A vs Proposed | Separate Baseline B and C runs (document as not run) |
| Egress cannot be verified | Network denied entirely | Any proxy allowlist |

Never cut independent permission checks, actual sandbox execution, real provider integration, audit records or truthful results to preserve optional features.

## 13. Optional offline experiment lane

Amir can investigate one optimization at a time after helping freeze the evaluation baseline. Each experiment needs a hypothesis, authorized dataset, compatible teacher/student setup, compute budget and held-out evaluation. Produce a short report even if the result is negative. Stop if it risks release work. No offline artifact enters routing without a compatible serving path, quality comparison and reviewed promotion.

## 14. Operating rhythm and post-submission care

Daily: brief blocker check, one integrated demo and a written decision log. Every two days: review failing acceptance criteria and remove scope that does not serve the core journey. Before merging: affected owner reviews contract changes; Aziz reviews policy and security changes; Jami checks evidence expectations.

After submission, assign a primary and backup availability owner, monitor provider credits and preserve the submitted release. Follow rules.md for the permitted change process. Record incidents and operational recovery without silently substituting a different claimed product.

## 15. Remaining after coding development ends

Finishing the code does **not** finish the project. Track these until each has evidence.

### 15.1 Verification that code cannot provide

| Item | Why it remains | Owner | Evidence |
| --- | --- | --- | --- |
| Real provider and model verification | Model IDs, tier availability (Nano/Super/Ultra), capacities and usage reporting must be observed on the live account | Asif | E01, registry file |
| Sandbox confinement and egress proof | Token Factory Sandbox restrictions must be tested, not assumed | Qadir, Aziz | E02, Phase 0 record |
| Benchmark runs | Functional suite, Baselines A/B/C/Proposed, repeated trials | Asif, Qasim | E08 |
| Security suite execution | Ten PDF cases plus mandatory cases | Aziz, Jami | E10 |
| Audit chain verification | Hash-chain check on a real exported run | Qadir | E11 |
| Three clean rehearsals | From reset state on the deployed build | Jami | E04 |
| Independent user test | Someone outside the UI team completes the journey | Jami | Phase 5 notes |
| Budget and credits | Inference, sandbox and hosting cost for the review period | Representative | Budget note |

### 15.2 Documents and compliance

| Item | Owner |
| --- | --- |
| `docs/threat-model.md` and `docs/runbook.md` | Aziz; Jami |
| LICENSE, `THIRD_PARTY_NOTICES.md`, provenance register | Aziz, maintainer |
| Change log separating pre-existing research from new work (E06) | Jami |
| Roster review and representative authorization (E09) | Representative |
| Project description, tool feedback form, screenshots | Representative, Yash |
| 2:45 English video, uploaded publicly | Yash, Jami |
| Signed-out link check; final read of full official rules | Representative |
| Release tag, image digest and manifest | Qadir |

### 15.3 Deferred product work (not in the MVP)

| Item | Priority | Trigger to start |
| --- | --- | --- |
| User repository upload with archive, size and ownership checks | P1 | Sandbox confinement proven |
| JavaScript/TypeScript support and fixtures | P1 | Python path stable |
| Semantic/embedding retrieval | P1 | Measured gain over lexical + symbol ranking |
| Controlled `git.commit` behind approval | P1 | Approval Manager proven |
| Scoped, consented memory with expiry | P1 | Core journey stable |
| PostgreSQL, Redis queue, per-service identities | Scale-out | Before any horizontal scaling |
| Egress/secret proxy and package mirrors | Scale-out | A fixture truly needs egress |
| OpenTelemetry export, external immutable audit store | Scale-out | Beyond single host |
| Stronger multi-tenant isolation | Scale-out | Before shared public use |
| MCP integrations | P2 | Concrete need and review |
| Distillation, pruning, quantization, student model | P2 | Offline lane with reports |
| Second and third model tiers in Auto routing | Gated | Verified access and measured quality |

### 15.4 After submission

Availability owner and backup named; credit monitoring; incident log; no silent substitution of the submitted product; changes after closing only through the organizer's exception process.

