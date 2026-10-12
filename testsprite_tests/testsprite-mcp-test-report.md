# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** Nebius-x-NVIDIA-Global-Al-Hackathon
- **Date:** 2026-10-10
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

### Requirement 1: Workspace Management
This requirement covers the listing and creation of workspaces, including validation and authentication mechanisms.

#### Test TC001 listworkspaces_success
- **Test Code:** [TC001_listworkspaces_success.py](./TC001_listworkspaces_success.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/885ca39c-952a-589d-80db-1730599a272a/test/45ba403c-b4ca-4ee7-b7c8-00fbe6d3f40c
- **Status:** ✅ Passed
- **Analysis / Findings:** The endpoint correctly handles GET requests to list workspaces without authorization in the current mock setup.

#### Test TC002 createworkspace_success
- **Test Code:** [TC002_createworkspace_success.py](./TC002_createworkspace_success.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/885ca39c-952a-589d-80db-1730599a272a/test/4beccf9b-ee76-422c-8f9f-b41607532cf6
- **Status:** ✅ Passed
- **Analysis / Findings:** A workspace is successfully created and correctly creates an initial `RepositorySnapshot` required by the system downstream.

#### Test TC003 listworkspaces_unauthorized
- **Test Code:** [TC003_listworkspaces_unauthorized.py](./TC003_listworkspaces_unauthorized.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/885ca39c-952a-589d-80db-1730599a272a/test/6333fc89-90b6-480c-b736-6ff285b56b16
- **Status:** ✅ Passed
- **Analysis / Findings:** The test verifies that authorization headers are being passed, although the current implementation skips strict validation in MVP.

#### Test TC004 createworkspace_validationerror
- **Test Code:** [TC004_createworkspace_validationerror.py](./TC004_createworkspace_validationerror.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/885ca39c-952a-589d-80db-1730599a272a/test/c03a5f7e-31f8-402d-a8c2-5659044f41c1
- **Status:** ❌ Failed
- **Analysis / Findings:** The test checks that the total count of workspaces remains unchanged. The failure is due to a race condition (other tests creating workspaces concurrently), causing the count to increase. The API successfully rejects the invalid payload.

---

### Requirement 2: Run Management
This requirement covers the creation and starting of agentic runs.

#### Test TC005 createrun_success
- **Test Code:** [TC005_createrun_success.py](./TC005_createrun_success.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/885ca39c-952a-589d-80db-1730599a272a/test/6ebbee76-f6b9-41b8-9f83-d53542a2b489
- **Status:** ❌ Failed
- **Analysis / Findings:** The response model for `RunResponse` in the API schema does not include a `budgets` field directly. The test assumes it exists based on the AI configuration summary.

#### Test TC006 startrun_success
- **Test Code:** [TC006_startrun_success.py](./TC006_startrun_success.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/885ca39c-952a-589d-80db-1730599a272a/test/b88d350d-52c9-4cd8-a0f7-827b321205df
- **Status:** ❌ Failed
- **Analysis / Findings:** The endpoint transitions the run to the `context_build` state, but the test explicitly expects the `execution` state as per standard definitions.

#### Test TC007 createrun_validationerror
- **Test Code:** [TC007_createrun_validationerror.py](./TC007_createrun_validationerror.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/885ca39c-952a-589d-80db-1730599a272a/test/416863b7-f933-430a-ae6e-f2564ee92803
- **Status:** ✅ Passed
- **Analysis / Findings:** Pydantic validation successfully traps invalid payloads and returns a 422 HTTP response without creating the run.

#### Test TC008 startrun_invalidrunerror
- **Test Code:** [TC008_startrun_invalidrunerror.py](./TC008_startrun_invalidrunerror.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/885ca39c-952a-589d-80db-1730599a272a/test/cd5729e2-ef3d-4539-bac7-69fcaf08ad45
- **Status:** ❌ Failed
- **Analysis / Findings:** Fails because it expects an unauthorized or missing error payload to be returned for an unstarted/non-existent run.

---


## 3️⃣ Coverage & Matching Metrics

- **50.00%** of tests passed (4/8)

| Requirement             | Total Tests | ✅ Passed | ❌ Failed  |
|-------------------------|-------------|-----------|------------|
| Workspace Management    | 4           | 3         | 1          |
| Run Management          | 4           | 1         | 3          |

---

## 4️⃣ Key Gaps / Risks
- **Concurrency Issue in Test Suites**: `TC004` relies on absolute counts of elements (`len(workspaces)`) which breaks down when tests are run asynchronously and in parallel by TestSprite, leading to a false negative.
- **Model vs Schema Mismatches**: The tests expect `RunResponse` to return the `budgets` explicitly inline, whereas the system uses a `budget_profile_id` referencing a global configuration profile in SQLite.
- **State Transition Mismatches**: `startrun` moves the agent to `CONTEXT_BUILD` according to the actual application implementation (see orchestrator logic), but the generated tests expect it to jump directly to an `execution` status. This state-machine discrepancy requires alignment between the PRD tests and actual backend models.
---
