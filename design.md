# Nexora — Design System and Interface Specification

Version: 3.0 | Updated: 3 October 2026 | Proposed visual and interaction system

Related: [PRD](prd.md), [Architecture](architrcture.md), [Rules](rules.md), [Phases](phases.md).

**Revision note (v3.0).** Adds interface for the PDF architecture's security plane: security decision display, policy-decision timeline, approval dialog, blocked/quarantined states, loop-stop and budget-exhausted messages, audit view, and the expanded run states. Colors, typography and spacing are unchanged.

## 1. Design direction

Nexora should feel like a focused developer workspace: calm, precise and transparent. The task, patch and test result are the visual priorities. The distinctive product elements are the context window analysis, the visible model-routing control and the visible security decisions: the user can always see what was allowed, denied or sent for approval, and why.

Use a dark navy theme with restrained teal accents. Avoid decorative AI imagery, fake terminal output, excessive gradients and constant animation. The user should understand what is happening without reading internal architecture terminology; internal names such as "QUARANTINE" or "policy engine" appear with plain-language labels.

Product tagline: **"Code with evidence."**

Primary action language: "Start task," "Review plan," "Approve this action," "Reject," "Run tests," "Review patch," "Download patch" and "Cancel run." Prefer concrete actions to labels such as "Activate intelligence."

## 2. Color tokens

| Token | Hex | Usage |
| --- | --- | --- |
| `--bg` | `#0B1220` | Application background |
| `--surface` | `#111C2E` | Main cards and panels |
| `--surface-raised` | `#1B2B43` | Menus, selected rows and dialogs |
| `--border` | `#64748B` | Essential control borders and separators |
| `--text` | `#F1F5F9` | Primary copy and headings |
| `--text-muted` | `#A7B6CA` | Secondary copy and metadata |
| `--accent` | `#5EEAD4` | Primary buttons, active stage and selected controls |
| `--accent-ink` | `#062D2A` | Text on the teal button |
| `--link` | `#A5B4FC` | Links and secondary interactive emphasis |
| `--success` | `#86EFAC` | Passed, verified, allowed |
| `--warning` | `#FCD34D` | Review required, approval needed, monitored, approaching limit |
| `--danger` | `#FDA4AF` | Failure, denied action, quarantine and destructive controls |
| `--focus` | `#C4B5FD` | Keyboard focus ring |

Use status text and an icon with each semantic color. "Passed" and "Failed" cannot be distinguished only by green and red. Policy decisions follow the same rule: ALLOW (success + check icon), ALLOW_WITH_MONITORING (success + eye icon, "Allowed, monitored"), REQUIRE_APPROVAL (warning + hand icon), DENY (danger + block icon), QUARANTINE (danger + isolate icon, "Quarantined"). Diff additions include `+` and deletions include `−`, with separate accessible labels.

Calculated reference contrast on `--surface`: primary text 15.59:1, muted text 8.29:1, essential border 3.59:1. Teal-button text is 10.02:1. These calculations cover the listed solid colors; hover, disabled and diff states still need rendered checks.

Use solid text colors on the specified backgrounds. Do not lower text opacity until it becomes unreadable. Aim for at least 4.5:1 contrast for normal text and 3:1 for essential non-text controls; verify actual rendered combinations during implementation.

## 3. Fonts and typography

Use local system fonts to avoid external requests and font-loading delays. Do not bundle proprietary font files.

```css
:root {
  --font-ui: system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  --font-code: ui-monospace, "SFMono-Regular", Consolas,
    "Liberation Mono", monospace;
}
```

| Role | Size / line height | Weight | Usage |
| --- | --- | --- | --- |
| Page title | 28px / 36px | 700 | Workspace heading |
| Section title | 20px / 28px | 600 | Plan, patch, security and result panels |
| Panel title | 16px / 24px | 600 | Context, model, security and test cards |
| Body | 16px / 24px | 400 | Plans, explanations and prompts |
| Compact control | 14px / 20px | 500 | Buttons, tabs and navigation |
| Metadata | 13px / 18px | 400 | Timestamp, version and reason-code labels |
| Code and logs | 13px / 20px | 400 | Diffs, commands and output |
| Metric | 24px / 32px | 600 | A small number of important observations |

Never make long descriptions all caps. Use tabular numerals for counts and durations. Keep prose lines approximately 60–80 characters wide. Let code scroll horizontally without causing the entire page to overflow.

## 4. Spacing, shape and elevation

Use a spacing scale of 4, 8, 12, 16, 24, 32 and 48 pixels. Main panels use 24px padding on desktop and 16px on narrow screens. Related controls use 8px gaps; unrelated groups use 24px or more.

Border radius: 8px on controls, 12px on cards, 16px on dialogs. Use 1px borders. Reserve shadows for floating menus and dialogs; panel hierarchy should come primarily from spacing and surface tone.

Buttons should have at least a 44px target height. Icon-only buttons require tooltips and accessible names. Keep one strong primary action per decision area. Cancel remains visible while a run is active.

## 5. Desktop workspace layout

For widths of 1280px and above, use three regions:

| Region | Approximate width | Content |
| --- | --- | --- |
| Workspace navigation | 220px | Project selector, sample tasks, run history |
| Main work area | Flexible; minimum 520px | Tabs: Task, Plan, Activity, Patch, Tests, Security, Evidence |
| Inspection panel | 300px | Model, context, budget, security summary and evidence summary |

Use a 64px header with Nexora identity, workspace name, budget profile name and connection state. The main work area receives the most visual space. Do not force users to watch a scrolling chat transcript to find the final patch.

For widths 768–1279px, collapse navigation and place the inspection panel in a drawer. Below 768px, use a single column with accessible tabs for Task, Patch, Tests, Security and Details. Preserve the task status and cancel control near the top. A pending approval request must stay visible at the top on every width.

## 6. Screen specifications

### A. Start workspace

Show three sample tasks with a plain-language purpose and expected repository type. Include a boundary statement: "Runs in an isolated task workspace. Every action is checked by a policy before it runs. Changes are provided for review."

Primary action: "Open sample." Secondary action: "View setup." Arbitrary repository upload stays hidden or explicitly unavailable until its P1 safety gate passes.

### B. Task composer, analysis and plan

The composer contains the task field, routing mode, optional fixed-model selector and run limit summary (profile name plus deadline, attempts and token cap). A model is selectable only if enabled in the backend registry. Disable submit for invalid input and show a nearby reason.

After submit, show a compact **analysis card**: objective, constraints, acceptance tests, risk class and the *proposed* capabilities, labeled "Proposed, not granted." Then a **security decision** line: Allowed / Needs approval / Blocked, with reason codes in plain language.

The plan lists hypothesis, candidate files and symbols, tool sequence, test command, stop conditions and estimated budget. "Start task" becomes available after the plan loads. Users can edit their task before acceptance; changing the task invalidates the old analysis and plan.

### C. Active run

Show a short stage timeline: Analyzing, Security review, Planning, Building context, Generating, Policy check, Executing, Validating and Reviewing. Display elapsed time, not an invented completion percentage. The active stage has text, an icon and a subtle highlight.

Under the timeline, show a **policy-decision feed**: each tool request with tool name, target, decision badge and reason code. Expose sanitized log snippets in a collapsible panel. Do not reveal private chain-of-thought; route reasons, decision reasons and action summaries are sufficient. Keep the user's original task visible above the activity.

### D. Approval dialog

When a request needs approval, the run enters "Awaiting approval" and a dialog (also an inline card at the top of the main area) shows:

- the exact action in plain language and the normalized command or target;
- why it was flagged (reason codes, risk label);
- the **scope** (this one action) and the **expiry** countdown as text, for example "Expires in 4:32";
- what happens if rejected or if it expires: "The run will stop safely."

Actions: "Approve this action" and "Reject." Neither is the default focus target for high-risk requests; focus lands on the explanation heading. Escape closes the dialog without approving or rejecting and does not cancel the run. Silence is never approval: after expiry, show "Approval expired. The run stopped safely."

### E. Patch review

Default to a unified diff, grouped by file. Show changed-file count, additions, deletions, verification status and any out-of-scope warning. Offer a side-by-side mode only if implementation time permits.

The primary action is "Download patch" for the reviewed artifact. A failed patch is labeled "Unverified patch"; downloading it requires explicit acknowledgment of the failed result. Do not make "Apply to main," commit or push a default action.

### F. Results and evidence

Show test counts, critic findings, policy-check outcome, model used, attempts, elapsed time, tool-call count and token usage. Separate known, estimated and unavailable metrics. Offer a downloadable evidence report containing run ID, configuration versions (policy, budget profile, model registry), tested patch hash, blocked actions and limitations.

### G. Security tab

Shows, for the current run: the security decision and reason codes; content provenance summary (counts by source: task, repository, tool output, model); injection-detector findings with disposition ("Flagged and treated as data"); every policy decision in a filterable table; approvals with scope, approver and expiry; blocked actions; and an **audit trail** list with a "Download audit export" action and a hash-chain status line ("Chain verified" or "Verification unavailable"). Label detector findings as advisory.

## 7. Context window panel

This panel is a core feature, not a decorative circular gauge.

- Display selected model capacity only when verified.
- Divide the budget into instructions, task, selected source, recent tool output, reserved output and safety margin.
- Show included files and omitted categories with reasons, and the ranking reason for each included file (for example "Failing test location").
- Show cache use as text: "2 of 5 summaries reused."
- Label tokenizer-derived values "Estimated" unless they match provider accounting.
- Show actual provider usage separately after inference completes; show compression ratio only when both sizes are known.
- Warn near the configured capacity threshold and explain the planned response.
- Display "Capacity unknown" instead of guessing a percentage.

When switching models, briefly show "Recalculating context for selected model." Do not reuse the previous model's capacity. A percentage bar must have a textual equivalent such as "Estimated input: 4,820 tokens." Example numbers belong in design mocks only and must never ship as observed run data.

## 8. Model-shifting control

Place a compact chip in the inspection panel: `Auto · actual model name` or `Fixed · actual model name`. Use a route/swap icon with an accessible label; do not rely on the icon to explain the feature.

Clicking opens details: current model ID, selection reason, attempt number and permitted alternatives. In Auto mode, a genuine switch produces a timeline event such as "Changed model after failed verification." In Fixed mode, unavailable or inadequate capability produces a visible limitation instead of a silent replacement. A denied action is never shown as retried on another model.

If only one model is enabled, display "One model configured." Keep pricing unknown when no validated price table exists. Avoid terms such as "brain upgraded" that imply capability was established without evidence.

## 9. State and microcopy matrix

| Run state | Main message | Available action |
| --- | --- | --- |
| Empty | "Choose a sample repository to begin." | Open sample |
| `queued` | "Your task is queued." | Cancel |
| `analyzing` | "Analyzing the task." | Cancel |
| `security_review` | "Checking the task and repository content." | Cancel |
| `awaiting_approval` | "This action needs your approval." | Approve / Reject / Cancel |
| `planning` | "Preparing a plan." | Cancel |
| `awaiting_start` | "Review the plan before execution." | Start task / edit task |
| `context_build`, `model_step`, `policy_check`, `executing`, `validating` | "Running in the task workspace." (stage name shown in the timeline) | Cancel / inspect details |
| `replanning` | "Verification failed. Trying a bounded repair with new evidence." | Cancel / view failure |
| `completed` | "Checks passed. Review the patch." (label "Verified") | Review / download |
| `failed` | "The task did not pass verification." | Inspect evidence / revise task |
| `blocked` | "This action is outside what is allowed." | Edit task / view policy reason |
| `cancel_requested` | "Stopping the run. An in-flight operation may finish." | Inspect status |
| `cancelled` | "Run cancelled." | Start a new run |
| `interrupted` | "The run was interrupted. Reconciling saved progress." | Wait / retry |
| Disconnected | "Connection lost. Reconnecting to saved progress." | Retry connection |
| Provider unavailable | "The model service is unavailable." | Retry later |

Additional situations:

| Situation | Message | Action |
| --- | --- | --- |
| Action denied | "An action was denied: <plain reason>. The run continues only if a safe alternative exists." | View decision |
| Quarantined | "An artifact was isolated for review. The run stopped." | View decision / revise task |
| Approval rejected or expired | "No approval was given. The run stopped safely." | Edit task / new run |
| Injection flagged | "Repository text that looks like an instruction was treated as data." | View finding |
| Loop stopped | "The same step failed repeatedly, so the run stopped." | Inspect evidence / revise task |
| Budget exhausted | "The run reached its limit (<which>)." | Inspect evidence / revise task |
| Secret redacted | "Sensitive-looking text was removed from the output." | View detail |
| Sandbox unavailable | "The execution service is unavailable. Nothing was run." | Retry later |

Error messages should identify the failed stage and a useful next action. Do not display provider stack traces or secrets. A toast can supplement a result but cannot be the only place a critical failure or denial is shown.

## 10. Accessibility and interaction

Use semantic buttons, headings, form labels and landmarks. Keep keyboard focus visible with a 2px focus ring and 2px offset. Opening a dialog moves focus inside; closing returns focus to the triggering control. Escape closes dismissible overlays but must not silently cancel an active task or resolve an approval.

Announce major status changes, new approval requests and denials with a polite live region (approval requests may use an assertive region because they are time-limited). Do not announce every log line. Support browser zoom to 200%, reduced motion and keyboard-only operation. Tooltips must also work on focus. Do not place essential explanations only inside hover states. Approval countdowns are text that updates at a low rate and are not the only indicator of expiry.

Use 120–180ms transitions for opacity or small state changes. Disable nonessential animation under `prefers-reduced-motion`. Avoid animated counters that imply metrics are arriving when no backend event exists.

## 11. Frontend implementation rules

Centralize tokens in `web/styles/tokens.css`. Components read application state rather than creating separate conflicting run states. Keep API error normalization in `web/js/api.js` and event reduction in `web/js/state.js`. New components: `web/js/components/security.js` (decision feed and Security tab), `approvals.js` (approval card and dialog), `audit.js` (audit list and export).

Render code, logs, reason codes and repository-derived text as escaped text; never as HTML. Bound visible log history and allow downloading a sanitized complete artifact where available. Avoid rendering arbitrary model HTML. Preserve selection and scroll position when new events arrive; do not force the user back to the latest log line while reviewing an earlier error. The UI never decides authorization: it displays backend decisions, and approval buttons call the approval endpoint, which re-validates scope, expiry and ownership.

Keep the interface in English for the first release and the demonstration. The underlying copy structure should allow later localization without changing contracts.

## 12. Design acceptance checklist

- [ ] The main task and its outcome are identifiable within five seconds.
- [ ] Model, context and security panels reflect backend state and real capabilities.
- [ ] A user can distinguish verified, failed, blocked, quarantined, cancelled and awaiting-approval outcomes.
- [ ] Every policy decision shown has a reason and is reachable from the Security tab.
- [ ] The approval dialog states the exact action, scope and expiry, and expiry is handled safely.
- [ ] Unknown metrics are explicit; mock values do not appear in live results.
- [ ] Diff review and test evidence are accessible without reading the full activity log.
- [ ] Keyboard, 200% zoom, narrow screens and reduced motion are checked.
- [ ] Normal text and essential control contrast are checked in actual rendered states, including policy badges.
- [ ] At least one independent reviewer completes the core journey, including one denied or approval path.
- [ ] Recording text remains readable at the intended video resolution.

