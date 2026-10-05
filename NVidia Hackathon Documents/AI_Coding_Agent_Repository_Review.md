# Open-Source AI Coding Agent Software: Repository Review

**Prepared for:** Azizullah Memon's AI coding agent project  
**Reviewed:** 24 September 2026

## Project scope

The target is user-facing software like Cursor: a user describes a task in natural language (for example, “Build a FastAPI login API with JWT”), and the agent creates or edits files, runs commands and tests, fixes errors, and reports results. The proposed additions are automatic security checks, token efficiency, permission controls, and task-based selection of model or reasoning budget. These repositories are product references, not just GitHub-issue-solving benchmarks.

“Community/developer expectations” below refers to specific public GitHub issues. One issue represents its author’s request, not a consensus of all users. “Opportunity for our project” is our analysis, not a claim by the repository maintainers.

## 1. Cline

**Repository title:** Cline — AI Coding Agent for IDE and Terminal  
**GitHub repository:** [cline/cline](https://github.com/cline/cline)

**Pros / Strengths**

- Interactive coding agent with editor and CLI experiences; accepts natural-language tasks and can act on project files and terminal commands.
- Offers plan/act workflows, checkpoints, tool approvals, MCP tools, and multiple model providers.
- Its CLI already exposes configurable thinking levels and context compaction. This makes it a direct reference for adjustable reasoning and token management. [Cline CLI documentation](https://github.com/cline/cline/blob/main/apps/cli/README.md)

**Cons / Weaknesses**

- A broad feature set and multiple interfaces increase the effort needed to understand or customize the entire software.
- Provider-specific context metadata can cause inefficient compaction: an issue reports premature compaction when an OpenAI-compatible model's configured context window is ignored. This is an issue report, not a universal behavior. [Context-window issue](https://github.com/cline/cline/issues/12520)
- Autonomous command execution needs careful independent permission checks; an issue reports destructive commands bypassing approval when a model supplies a false approval flag. [Command-approval issue](https://github.com/cline/cline/issues/12020)

**What is lacking / Community and developer expectations**

- **Documented requests:** Correct provider context-window handling and reliable command approval, as shown in the issues above.
- **Opportunity for our project:** Implement task-dependent model/reasoning selection with measured token budgets and a permission engine that does not trust an LLM's own risk label. Cline already offers manual thinking settings and compaction, so those features alone would not be novel.

## 2. Roo Code

**Repository title:** Roo Code — AI Agent Team in Your Code Editor  
**GitHub repository:** [RooCodeInc/Roo-Code](https://github.com/RooCodeInc/Roo-Code)

**Pros / Strengths**

- User-facing editor software with specialized modes for coding and planning; suitable for building software from natural-language instructions.
- Model choices and mode-based workflows provide useful examples for the interface of an adaptive coding agent. [Repository overview](https://github.com/RooCodeInc/Roo-Code)

**Cons / Weaknesses**

- Mode-specific model selection can surprise users who expect a chosen model to remain fixed. [Model persistence issue](https://github.com/RooCodeInc/Roo-Code/issues/12237)
- Switching to a model with a smaller context window can require additional compression to avoid overflow. [Context on model switching](https://github.com/RooCodeInc/Roo-Code/issues/4022)

**What is lacking / Community and developer expectations**

- **Documented requests:** One issue explicitly proposes choosing a model dynamically based on the request; another asks for changing models during execution. Other users want their manually chosen model to stay fixed. This means automatic routing should be **opt-in and clearly visible**. [Dynamic model selection](https://github.com/RooCodeInc/Roo-Code/issues/11269) · [Mid-task model change](https://github.com/RooCodeInc/Roo-Code/issues/8334) · [Keep chosen model](https://github.com/RooCodeInc/Roo-Code/issues/12237)
- **Opportunity for our project:** Add a router that predicts task difficulty, preserves a manual override, limits cost, and rechecks context size before changing models. A developer has also proposed a more token-efficient representation for tool output. [Token-efficient output request](https://github.com/RooCodeInc/Roo-Code/issues/12111)

## 3. OpenHands

**Repository title:** OpenHands — Open-Source Software Development Agents  
**GitHub repository:** [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands)

**Pros / Strengths**

- Full user-facing agent software with an agent SDK, server, tools, conversations, and workspace support. It is useful when studying an end-to-end software product, rather than only an agent loop. [Repository README](https://github.com/OpenHands/OpenHands/blob/main/README.md)
- Its runtime and sandbox choices provide architectural examples for allowing an agent to execute code in a controlled workspace. [Repository README](https://github.com/OpenHands/OpenHands/blob/main/README.md)

**Cons / Weaknesses**

- Larger architecture creates more setup and integration work for a small hackathon team.
- Sandbox configuration and startup can be operational pain points; a reported issue describes failure to start a sandbox with a custom image. [Custom sandbox issue](https://github.com/OpenHands/OpenHands/issues/15018)

**What is lacking / Community and developer expectations**

- **Documented requests:** Easier model/provider switching, preservation of LLM and condenser settings when changing agent modes, and alternative isolation technology for security-sensitive deployments. These are specific requests and may change as the project evolves. [CLI model switching](https://github.com/OpenHands/OpenHands/issues/10044) · [Settings preservation](https://github.com/OpenHands/OpenHands/issues/14370) · [MicroVM request](https://github.com/OpenHands/OpenHands/issues/13203)
- **Opportunity for our project:** Provide an easier single-user workflow with transparent low/medium/high task routing and clear sandbox permissions. Do not assume OpenHands has no security isolation: it already has sandbox-related infrastructure.

## 4. Aider

**Repository title:** Aider — AI Pair Programming in Your Terminal  
**GitHub repository:** [Aider-AI/aider](https://github.com/Aider-AI/aider)

**Pros / Strengths**

- Natural-language coding in a terminal, with Git integration, codebase mapping, and optional automatic linting and tests. [Repository README](https://github.com/Aider-AI/aider)
- Its repository map selects important code within a token budget, providing an especially useful design reference for efficient context selection. [Repository-map documentation](https://github.com/Aider-AI/aider/blob/main/aider/website/docs/repomap.md)
- Configuration includes thinking-budget and repository-map token settings for supported models. [Sample configuration](https://github.com/Aider-AI/aider/blob/main/aider/website/assets/sample.aider.conf.yml)

**Cons / Weaknesses**

- Terminal-first interaction differs from a Cursor-like visual software experience.
- A repository-map issue reports that its token limit was not respected in one scenario. This is evidence for testing budget enforcement carefully, not proof that the feature always fails. [Token-limit issue](https://github.com/Aider-AI/aider/issues/752)

**What is lacking / Community and developer expectations**

- **Documented requests:** More predictable repository-map token limits and control over unintended edits in architect mode. [Token-limit issue](https://github.com/Aider-AI/aider/issues/752) · [Architect-mode issue](https://github.com/Aider-AI/aider/issues/3543)
- **Opportunity for our project:** Combine a visual user-facing agent with verifiable token limits, explicit action approval, and security checks after generated edits. Aider already has context selection and test support; these should be studied and extended, not presented as absent.

## Recommendation for our project

**Best starting references:** Cline or Roo Code for the interactive software experience; Aider for relevant-code selection; OpenHands for runtime and sandbox architecture. Before choosing a codebase to fork, compare its license, build process, API integration, and fit with the hackathon rules.

**Distinctive feature to build:** A user prompt enters one coding workflow; a transparent router sets an initial model/reasoning tier and token budget; the agent edits and tests code; a security scan checks changes; a separate permission gate evaluates tool actions; failure can increase the tier within a user-defined cost ceiling. Show the chosen tier, token use, approvals, scan findings, and test results in the interface. Changing a model's inference settings is different from training or optimizing its weights.

**Example task:** “Create a FastAPI REST API with registration, login, and JWT authentication.” The agent should create the app, add password hashing and token verification, run authentication tests, inspect generated code for security problems, fix confirmed findings, and report what passed. 
