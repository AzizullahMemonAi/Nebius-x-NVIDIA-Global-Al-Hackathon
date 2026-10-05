# Nexora — Hackathon Compliance and Engineering Rules

Version: 3.0 | Updated: 3 October 2026 | Official pages last checked: 25 September 2026 (recheck due; see §12)

Related files: [PRD](prd.md), [Architecture](architrcture.md), [Phases](phases.md), [Design](design.md).

## 1. Authority and scope

The organizer's [Official Rules](https://nebiusglobalaihackathon.devpost.com/rules) govern eligibility and submission. This file is an actionable project checklist, not a replacement for the full terms. Sections labeled **Nexora policy** are the team's engineering choices. Technical thresholds are proposed defaults, not organizer requirements.

If the official rules change, update this file and assess impact before the release. Do not use older research notes or the supplied architecture PDF as authority for dates, team limits or provider availability. The PDF is an engineering baseline only.

## 2. Official rules — compact reference

Source: [Official Rules](https://nebiusglobalaihackathon.devpost.com/rules), sections 1–7.

- Submission window: August 26–October 30, 2026; closing time 10:00 Pacific / 17:00 UTC / 22:00 Pakistan time.
- Judging: December 1–15, ending noon Pacific. Winners: approximately January 11, 2027.
- Participants need majority age, eligible residence and no disqualifying conflicts. Teams appoint a representative. No numerical team cap was found; do not assume unlimited membership.
- Existing projects require significant in-period improvements and an explanation.
- Materials require English or translations; judging access must remain free through judging. Private demos need access instructions.
- Use authorized third-party components and satisfy ownership/license conditions; sponsor funding or preferential support can affect eligibility.
- Submission changes after closing require the specified organizer exception.
- Viability screening precedes four equally weighted criteria: implementation, design, impact and idea quality.
- Ownership remains with creators; judging/publicity permissions apply.

Consult sections 8–13 directly for prizes, verification, taxes, releases, dispute terms and organizer powers. Check every participant against section 3; do not treat nationality alone as an eligibility guarantee.

## 3. Submission package and evidence

The [official overview](https://nebiusglobalaihackathon.devpost.com/) also requests feedback on the tools used, integration explanations and an account of significant updates for pre-existing work. Its video guidance mentions audio; use English narration. The detailed rules' stricter video wording drives the team's 2:45 target.

### Nexora policy: evidence register

Create `submission/evidence.md` during implementation. Use a table with `item`, `owner`, `artifact`, `verified_at`, `reviewer` and `status`. A checkbox alone is not evidence.

| Evidence ID | Concrete artifact to prepare | Responsible owner |
| --- | --- | --- |
| E01 | Successful real inference trace with actual model ID and redacted request metadata | Asif |
| E02 | Sandbox execution record tied to the same run and patch hash | Qadir |
| E03 | Demonstration showing task, generated patch, tests and review outcome | Yash and Jami |
| E04 | Clean-checkout setup log and deployment access rehearsal | Qadir and Jami |
| E05 | Root LICENSE, dependency notices and component provenance register | Aziz and repository maintainer |
| E06 | Dated change log separating pre-existing research from new implementation | All leads; Jami consolidates |
| E07 | Final narrative, screenshots, tool feedback and video URL | Team representative |
| E08 | Comparative evaluation manifest (Baselines A, B, C, Proposed) and honest results | Asif and Qasim |
| E09 | Roster review and representative authorization record | Team representative |
| E10 | Security suite results: ten PDF cases plus mandatory cases, with observed outcome per case | Aziz and Jami |
| E11 | Sample audit export for one run showing policy decision and audit record for every tool action, plus hash-chain verification | Qadir and Aziz |

Do not publish credentials as evidence. If a private testing account is needed, give access through the submission's intended testing-instructions mechanism, with a restricted account that cannot access unrelated work.

## 4. What to use — Nexora policy

| Use | Required practice |
| --- | --- |
| Python backend and typed contracts | Validate requests, model results, tool arguments and state transitions |
| Real provider adapters | Isolate transport and normalize usage without hiding provider failures |
| Capability registry | Record actual model ID, context capacity, allowed parameters and verification date |
| Task Analyzer and Security Gateway | Analyzer proposes only; gateway emits an explicit decision with reasons |
| Policy Engine | Deterministic, versioned, independent of the model; five decisions (ALLOW, ALLOW_WITH_MONITORING, REQUIRE_APPROVAL, DENY, QUARANTINE) |
| Typed Tool Router | Reject unknown tools and malformed schemas before policy evaluation |
| Approval Manager | Approvals scoped to one action, expiring, auditable |
| Sandboxed execution | Validate confinement before enabling code runs |
| Structured patches | Validate paths, sizes and scope before applying changes |
| Reproducible fixtures | Pin initial commits, dependencies and expected checks |
| Versioned configuration | Associate every run with policy, prompt, budget-profile and registry versions |
| Audit log | Append-only, redacted, hash-chained |
| Minimal frontend | Show trustworthy state, diff, policy decisions, evidence and recovery controls |
| Measured evaluation | Preserve raw observations, configuration and failure cases |

A package becomes an approved dependency only after its purpose, exact version, license and operational cost are recorded. A research reference does not automatically become a dependency.

## 5. What to avoid — Nexora policy

- Unrestricted shell execution on the application host or developer laptop.
- Mounting host directories, Docker sockets or provider credentials into task sandboxes.
- Treating a model-supplied `safe=true` or approval flag as authorization.
- Inferring approval from silence, timeout or a previous unrelated approval.
- Placing API keys in frontend code, committed configuration, logs or screenshots.
- Using a fallback service that silently breaks the selected integration path.
- Claiming model shifting when only an icon changes, or claiming weight compression from a reasoning-budget setting.
- Treating a prompt-injection detector or model classifier as a complete security boundary.
- Retrying a denied action through a stronger model or reworded request to bypass policy.
- Introducing multiple orchestration frameworks before a single end-to-end run works.
- Adding unrelated Google services, MCP servers or web search merely to display more integrations.
- Automatically merging generated changes, pushing to a main branch or deploying them.
- Running dynamic package installs from unknown sources.
- Describing stubbed adapters, replayed demonstrations or planned features as live capabilities.
- Copying a repository wholesale without verifying license, attribution and substantive changes.

Google SDK/ADK research may inform later architecture. It does not replace the main runtime integration. Likewise, nanochat and model-compression research are optional references rather than mandatory components.

## 6. Input, context and prompt-injection policy

Treat task text, repository files, comments, README content, dependency metadata, logs, tool output, retrieved material and memory summaries as untrusted. Label every block with provenance and trust level when incorporating it into model context. Keep instructions and repository data in separate message structures, and instruct the model that repository text is data, not authority. A comment that asks the agent to reveal secrets or ignore policy remains repository data.

Use deterministic controls for enforceable boundaries: canonical paths, explicit workspaces, validated tool arguments, safe environment construction and server-owned commands. The injection detector may flag suspicious content and raise risk, but cannot guarantee safety. Log detector evidence and final disposition. Content must never be able to modify policy files or tool schemas.

Before context selection, exclude `.env`, credential files, private keys, unrelated user files, binary artifacts and generated dependency folders. Preserve necessary code structure and identifiers; arbitrary redaction that corrupts code must produce a limitation instead of a misleading patch.

Context reduction must retain the task, active constraints, relevant interfaces, current diff, newest failure, command text, policy decisions and security-relevant evidence. Keep an omission manifest. On a model change, rebuild the bundle under the new capacity. Do not assume JSON always saves tokens; measure with the selected tokenizer or label estimates. The context cache must hold no unredacted credentials and no data outside the run's authorization scope.

## 7. Tool, command, network, secret and Git policy

**Tools.** Initially expose narrow typed actions: `repo.list`, `repo.read`, `repo.write` (structured patch inside a task branch), `test.run` (server-selected command), `git.status`, `git.diff`, `git.branch`. Keep `shell.run`, `git.commit`, `git.push` and `network.fetch` disabled or approval-gated as set in Architecture §7. Reject arbitrary model-provided shell strings.

**Broker checks.** The Tool Router and Policy Engine validate workspace ownership, action permission, normalized arguments, canonical and resolved paths, patch scope, remaining time, remaining action count and approval state. No generated instruction can amend the active policy. Default deny for unknown commands, paths, destinations and capabilities. Policy errors fail closed.

**Commands.** Classify with structured parsing plus runtime controls, not regex alone. Deny command substitution and nested interpreters unless explicitly allowed; verify executable identity; allowlist environment variables; restrict working and output directories; apply resource limits. Risk handling: low is automatic within policy; medium (installs, builds) is denied in the demo and policy-checked with pinned sources in the `standard` profile; high requires explicit approval; critical (`rm -rf`, raw disk, credential access, host escape) is blocked and audited. Never assume an allowlisted executable makes repository-controlled code safe.

**Isolation and network.** Commands execute inside verified isolation with resource limits. Task sandboxes have no internet access in the MVP. Preinstall dependencies; do not run dynamic package installs during the main demo. If egress is ever enabled, it passes through a proxy with destination, method, DNS, IP, redirect, TLS, size and upload controls, and the team must demonstrate that raw sockets and alternate DNS cannot bypass it.

**Secrets.** Never in prompts, repository files, command arguments or ordinary logs. Treat environment variables as sensitive unless allowlisted. Redact stdout/stderr, traces, diffs, exceptions and model context. Scan files and tool output for accidental disclosure. If a secret appears in output: redact, quarantine the artifact, audit, and stop if necessary. Prefer short-lived scoped credentials.

**Git.** Allowed: status, diff, branch, read-only log within the repository. Commit: approval or configured policy. Reset and destructive history changes: block or explicit approval. Push: explicit human approval only, and denied in the MVP. Remote URL changes: blocked.

**Evaluator integrity.** Keep evaluator checks immutable and outside the writable task scope. Reject changes that remove tests to conceal failures. If a task legitimately changes test expectations, route it through explicit approval and preserve independent acceptance checks.

## 8. Inference, routing and cost policy

- Record the actual model ID returned/configured for every attempt.
- Enable a model only after an inference smoke test, capability check and terms review. Nano, Super and Ultra are candidate tiers, not assumed availability.
- Do not assume the largest model is best; an Ultra route needs measured quality gain.
- Keep fixed mode fixed. In Auto mode, show the reason for a model change.
- Separate retries caused by transport problems from repairs caused by failed verification.
- Enforce the active budget profile (`demo` default; `standard` only when explicitly selected) and the shared deadline.
- Use an idempotency key per inference request; apply timeout and exponential backoff within budget.
- Refuse unsupported parameters instead of silently pretending they took effect.
- Set unknown usage or cost to `null`; show "Unavailable" in the UI.
- Distinguish estimated prompt tokens from provider-reported billable usage.
- Include failed calls and sandbox activity in a total-cost report when observable.
- Failover only to an approved model; never in fixed mode.

If only one qualified model is available, ship honest single-model behavior. A second tier is a feature gate, not a reason to fabricate routing evidence.

## 9. Evaluation and claim policy

Claims such as faster, cheaper, safer or more accurate require a named measurement and scope. Report sample size, number of trials, configurations and failures. Avoid turning one curated demo into a general benchmark claim.

Compare the same tasks and starting repositories across Baseline A (basic agent), Baseline B (plus security layer), Baseline C (plus token optimizer) and Proposed (both), with equal sandbox restrictions. Include retries in latency and usage. Report token reduction separately from task success. If the denominator is zero or the comparison is invalid, show no percentage. Use fixed seeds or deterministic settings where supported; with few repeated trials, state that intervals are wide.

Use deterministic tests and policy checks for acceptance. An LLM may summarize results or advise on quality; it does not overrule failed tests. A passing suite establishes only the checked behavior.

**Mandatory adversarial cases** (synthetic secrets, owned fixtures): malicious README prompt injection; SSH key read attempt; environment-secret read attempt; dangerous shell command; unauthorized network request; unauthorized Git push; malicious dependency installation; symlink escape and path traversal; shell escape through command substitution; exfiltration through test output or generated artifacts; plus cross-session artifact access, output-based injection, protected-test edits, timeout enforcement, cancellation, oversized output, expired session, provider timeout and worker restart.

**Release gates.** Controlled use only if: no critical security test results in an allowed action; no raw secret appears in model context or ordinary logs; every tool action has a policy decision and audit record; sandbox escape tests are blocked; functional success is measured against Baseline A; token savings do not cause unacceptable quality regression; every run terminates through completion, controlled failure, block, cancellation or timeout.

## 10. Memory and offline optimization policy

Memory starts disabled. If added, store compact, repository-scoped, consented summaries with origin, expiry and deletion. Do not store raw secrets or treat remembered content as higher-priority instructions.

Distillation, pruning and quantization run in the offline lane. Before an experiment, record data rights, model terms, baseline, budget and evaluation criteria. Before promotion, verify artifact compatibility and task quality. Do not claim a student model exists until weights, training configuration and results are available.

## 11. Team workflow and definition of done

Use small branches, focused pull requests and named reviewers. Contract changes require affected module owners to review. Policy files (`config/policies/*`) and security-related code require independent review by the security owner (Aziz, with Qadir as reviewer); this is a team process, not a model's self-approval.

Follow Jami's sequence: Plan → Test → Implement → Review → Verify → Remember → Improve. "Remember" means documenting a useful lesson; it does not require an autonomous long-term memory feature.

A feature is done only when implemented, integrated, demonstrated, documented and checked against its acceptance criteria. A research document, mock screen or isolated notebook does not satisfy a runtime feature. Every new tool or capability ships with a policy rule, a denial test and an audit event.

## 12. Release and unresolved checks

- [ ] Recheck official pages and record the review date (last recorded: 25 September 2026; the submission window closes 30 October 2026).
- [ ] Verify participant eligibility and roster handling, especially the planned 14-person arrangement; ask organizers if entry UI or published guidance is ambiguous.
- [ ] Confirm provider account access, model availability, sandbox limits, egress behavior and deployment budget.
- [ ] Review any unusual prior funding/support situation with organizers rather than self-certifying.
- [ ] Pass the evidence register E01–E11 and remove placeholder values from release materials.
- [ ] Complete `docs/threat-model.md` and `docs/runbook.md` (listed in the architecture but not yet written).
- [ ] Tag the submitted commit; retain matching configuration and artifacts.
- [ ] Assign an availability owner and a budget for the full review period.
- [ ] Have the representative read the complete official terms, including sections not summarized here.

These checks are release tasks for the project team. The five documents do not register, submit or publish the project automatically.

