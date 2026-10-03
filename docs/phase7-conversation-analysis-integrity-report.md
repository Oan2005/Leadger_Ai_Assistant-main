# Leadger Phase 7: Conversation and Analysis Integrity Test Report

**Test date:** 2026-10-03  
**Environment:** TEST only (`.env.test`, dedicated Supabase project, TEST database URL, `leadger-test` Pinecone index)  
**Scope:** Authentication, `/employee/question` chat flow, retrieval, persistence, analysis handling, and observable isolation behavior  
**Application changes:** None

## Re-test Addendum — 2026-10-03 14:29

This addendum supersedes the pre-remediation observations below wherever
behavior is explicitly re-tested. No application code, schema, TEST data, or
Pinecone vectors were modified during this re-test.

### Current results

| Area | Result | Evidence |
| --- | --- | --- |
| Remediation route tests | PASS | `tests/test_employee_assistant_route.py`: 8 tests collected and passed. |
| TEST environment checks | PASS | `tests/integration/test_environment.py` passed as part of the combined run. |
| Full existing suite | PASS | `64 passed, 4 skipped, 4 warnings`. |
| Empty/whitespace questions | PASS | HTTP 400; retrieval, LLM, conversation, document, and analysis mocks were not called. |
| Analysis failure | PASS | HTTP 503; no successful chat response is returned. |
| Retrieval failure | PASS | HTTP 503; LLM and persistence stages were not called. |
| LLM failure | PASS | HTTP 503; conversation and analysis stages were not called. |
| Conversation creation failure | PASS | HTTP 503; document and analysis stages were not called. |
| TEST database injection | PASS | The environment test now resolves the injected TEST database URL. |
| Invalid authentication | PASS | Missing token returned 401; malformed token returned 401. |
| Existing TEST analysis integrity | FAIL | Cola remains 4 conversations/3 analyses; Pepsi remains 6/6; orphan analyses remain 0. |
| Real authenticated chat | BLOCKED | Existing TEST employee sign-in returned 403, “User Account Is Not Available”; no chat request was sent. |
| Cross-tenant/user conversation endpoints | BLOCKED | No conversation retrieval or mutation endpoints exist in the route surface. |

### Current TEST authentication evidence

The two configured TEST employee emails still have application rows in the
TEST database, but sign-in returned HTTP 403 for both during this re-test.
Because no TEST user or database data was modified, the cause was not
investigated through destructive account operations.

### Current consistency conclusion

The current route no longer silently returns HTTP 200 when analysis fails.
However, conversation persistence occurs before analysis and uses separate
database commits. The route therefore returns HTTP 503 after a conversation
may already exist if analysis fails. This is an observed partial-persistence
behavior, not an atomic transaction guarantee.

**Re-test classification: PASS WITH REMEDIATION**

## 1. Executive Summary

The TEST Supabase project, TEST database, TEST Pinecone index, and both existing TEST employee accounts were reachable. The real chat flow was not executed end-to-end because the employee chat and analysis clients load an OpenRouter credential from the non-TEST `.env`; sending a real request would violate the TEST-only requirement.

Safe route-level tests using runtime-only mocks found that the route returns HTTP 200 even when analysis reports failure, accepts empty and whitespace-only questions, creates independent records for repeated requests, and propagates retrieval, LLM, and conversation-creation failures as HTTP 500. The existing TEST database also contains one conversation without a corresponding analysis for the Cola tenant.

**Final classification: FAIL**

## 2. Test Results

| Test | Result | Key Finding |
| --- | --- | --- |
| Normal chat | BLOCKED | Real LLM and analysis provider configuration resolves from non-TEST `.env`; no real provider request was sent. |
| Conversation persistence | BLOCKED | End-to-end creation was not run; route-level mock confirmed the persistence call receives tenant/user and response metadata. |
| Analysis persistence | FAIL | TEST database contains 4 Cola conversations and 3 analyses; no orphan analyses were found. |
| Analysis failure | FAIL | Route returns HTTP 200 and the answer when `analysis_process` reports failure; the return value is ignored. |
| Retrieval failure | FAIL | A retrieval exception produces HTTP 500 with no structured application response; real database effects were not created in the isolated test. |
| LLM failure | FAIL | An LLM exception produces HTTP 500 with no structured application response; real database effects were not created in the isolated test. |
| Authentication | PASS | Missing and invalid tokens return HTTP 401; both TEST employee accounts authenticated successfully and returned their own tenant identity. |
| Tenant isolation | BLOCKED | No conversation retrieval or mutation endpoints were present to exercise cross-tenant access through real endpoints. |
| User isolation | BLOCKED | No conversation retrieval or mutation endpoints were present to exercise another-user access. |
| ID integrity | FAIL | Existing conversations have company/user IDs, but the analysis table has no company/user columns; one conversation is missing analysis. |
| Edge cases | FAIL | Empty and whitespace-only questions returned HTTP 200 in the route-level test and proceeded through retrieval, persistence, and analysis calls. |
| Duplicate requests | PASS (observed) | Two identical route calls were treated independently; each created a separate conversation call/session. |
| DB failure | FAIL | A conversation-create failure shaped as `{success: false}` is not recognized by the route and results in HTTP 500 after a missing-key error. |
| Transaction behavior | BLOCKED | Real destructive failure injection was not performed; source inspection shows conversation and analysis are committed in separate database operations. |
| Response consistency | FAIL | HTTP 200 is returned when analysis reports failure, so the response can claim success while analysis is absent. |
| Logging | PASS with limitation | Observed auth logs contain provider errors but not credentials or token values; a complete TEST log export was not available. |

## 3. Evidence Records

### TEST 1 — Normal Chat Flow

- **Test ID/name:** TEST 1 — Normal Chat Flow
- **Endpoint/function:** `/employee/question` (there is no `/chat` route); `employee_chat`
- **Authenticated user/company:** TEST employee accounts were verified separately; no real chat request was sent.
- **Input:** Not sent because the configured provider path is not TEST-safe.
- **Expected:** Successful retrieval, LLM response, conversation persistence, analysis persistence, and HTTP success.
- **Actual:** BLOCKED before request execution.
- **HTTP status:** Not applicable.
- **Database state:** Existing TEST data was read only; no test record was created.
- **Pinecone state:** Read-only queries against the TEST index succeeded for namespaces `cola` and `pepsi`, returning three matches each.
- **Analysis state:** Not exercised end-to-end.
- **Evidence:** `analysis_model.py` constructs its OpenAI client with `OPENROUTE_API_KEY`; that key is present in `.env`, not `.env.test`. The route is defined at `app/routes/employee_assistant_route.py:20`.

### TEST 2/3 — Conversation and Analysis Persistence

- **Endpoint/function:** `employee_chat`, `create_conversation`, `analysis_process`, `insert_conversation_analysis`
- **Expected:** Exactly one conversation and one related analysis per successful request.
- **Actual:** The TEST database currently contains 10 conversations and 9 analyses. Cola has 4 conversations and 3 analyses; Pepsi has 6 conversations and 6 analyses.
- **Database state:** One conversation lacks analysis; zero analysis rows reference a missing conversation.
- **Evidence:** Read-only aggregate query joining `conversations` to `conversation_analysis`.
- **Integrity impact:** Yes; one existing conversation is incomplete.

### TEST 4 — Analysis Failure Handling

- **Input:** Safe runtime-mocked successful retrieval/LLM response; `analysis_process` returned `{"status": false, ...}`.
- **Expected:** The HTTP response should accurately represent missing analysis, or the operation should roll back/return an error according to the intended transaction policy.
- **Actual:** HTTP 200 with the normal `answer`, `confidence`, and `session_id`; the route ignores the analysis return value.
- **Database state:** The isolated test used mocks and created no database rows.
- **Evidence:** `employee_chat` calls `analysis_process(...)` and immediately returns success without inspecting its result. `analysis_process` catches exceptions and returns a failure-shaped dictionary.

### TEST 5/6/13/14 — Retrieval, LLM, and Database Failure Handling

- **Endpoint/function:** `/employee/question`
- **Expected:** Structured error response and no misleading success or partial state.
- **Actual:** Runtime-isolated tests observed HTTP 500 for retrieval exceptions, LLM exceptions, and a conversation-create return of `{"success": false, ...}`. The latter is not treated as failure because the route checks only `is False` and then indexes `conversation_id`.
- **Database state:** No real rows were written by these mocked tests.
- **Transaction evidence:** `create_conversation` commits its own insert, and `insert_conversation_analysis` commits separately. No shared transaction spans both operations.

### TEST 7 — Invalid Authentication

- **Endpoints:** `/employee/question`, `/analysis`, `/analysis_dashboard`
- **Inputs:** Missing token and malformed bearer token.
- **Actual:** All tested endpoints returned HTTP 401. No retrieval or LLM call was reached.
- **Evidence:** Real TEST Supabase auth provider was contacted for the malformed token; the application returned `Invalid or expired token` without exposing the token in the response.

### TEST 8/9 — Tenant and User Isolation

- **Actual:** BLOCKED for conversation access because no application routes for retrieving, modifying, or deleting conversations or conversation analyses were found. The available `/analysis` endpoints require HR/admin roles and return company analytics, not conversation-by-ID access.
- **Verified identity facts:** The two TEST employees authenticated to distinct companies:
  - Cola employee: company `07855ba0-dd90-4d87-8cbd-fc7de445401e`
  - Pepsi employee: company `2568d8c-1455-4b21-9b55-30d3b49a6752`
- **Security limitation:** Cross-tenant conversation access cannot be confirmed or rejected through absent endpoints.

### TEST 10 — ID Integrity

- **Actual:** Conversation rows contain `company_id` and `user_id`. The analysis schema contains only `conversation_id` for relationship integrity and no independent `company_id` or `user_id`.
- **Expected:** Analysis tenant/user identity should be directly verifiable or enforced through the relationship.
- **Finding:** Direct analysis-level tenant/user checks are not possible from the current schema/API surface. One conversation-analysis relationship is missing in TEST data.

### TEST 11 — Empty/Missing Data

- **Inputs:** `question=""` and `question="   "` through the real route with runtime-only dependency mocks.
- **Actual:** Both returned HTTP 200 and invoked retrieval, conversation persistence, document persistence, and analysis calls.
- **Missing question:** Not separately sent because FastAPI parameter validation rejects a missing required query parameter before the handler; this was not a data-mutating test.
- **Finding:** Empty and whitespace-only input is not rejected at the route boundary.

### TEST 12 — Duplicate Requests

- **Input:** Repeated route calls with the same question under the same mocked user.
- **Actual:** Each call received a distinct generated `session_id`; the mocked conversation persistence function was called once per request.
- **Finding:** Requests are treated independently; deduplication was not observed.

### TEST 15 — Response Consistency

- **Actual:** A mocked analysis failure still produced HTTP 200 and the normal answer payload. This is inconsistent if analysis persistence is part of successful chat completion.
- **Evidence:** Same isolated route test as TEST 4.

### Logging Check

- **Observed:** Authentication failure logging records the provider exception and endpoint URL, but the captured output did not contain the bearer token value.
- **Source inspection:** Chat analysis logs use generic exception messages. The route does not log full question/answer content.
- **Limitation:** No complete centralized TEST log export was available, so this is not a full log-retention audit.

## 4. Confirmed PASS Areas

- TEST Supabase project health endpoint was reachable.
- Both existing TEST employee accounts signed in successfully.
- `/company/users/me` returned the authenticated user ID, company ID, and employee role for each account.
- Logout succeeded for both temporary sessions.
- Missing and invalid authentication were rejected with HTTP 401 on tested protected endpoints.
- Read-only Pinecone queries against the TEST index returned matches in both TEST namespaces.
- No orphan `conversation_analysis` rows were found.
- Invalid-token response did not expose the submitted token.

## 5. Failures

1. **Missing analysis record in existing TEST data**
   - **Behavior:** Cola has four conversations but only three related analyses.
   - **Expected:** Every successful conversation has one corresponding analysis.
   - **Affected area:** Conversation/analysis persistence pipeline.
   - **Severity:** High.
   - **Evidence:** Read-only aggregate query.
   - **Data integrity:** Affected; one conversation is incomplete.

2. **Analysis failure is swallowed**
   - **Behavior:** HTTP 200 is returned after analysis reports failure.
   - **Expected:** Error/partial status or rollback consistent with the transaction policy.
   - **Affected function:** `employee_chat`.
   - **Severity:** High.
   - **Evidence:** Runtime-mocked route test and source inspection.
   - **Data integrity:** Potentially affected; conversation may exist without analysis.

3. **Failure responses are unstructured**
   - **Behavior:** Retrieval, LLM, and conversation-create failures produced HTTP 500 in isolated route tests.
   - **Expected:** Explicit API error behavior and no misleading partial success.
   - **Affected function:** `employee_chat`.
   - **Severity:** Medium.
   - **Evidence:** Runtime-mocked failure probes.
   - **Data integrity:** Not established by these mock-only tests.

4. **Empty questions are accepted**
   - **Behavior:** Empty and whitespace-only questions returned HTTP 200 and proceeded through the pipeline.
   - **Expected:** Reject invalid input without creating meaningless records.
   - **Affected endpoint:** `/employee/question`.
   - **Severity:** Medium.
   - **Evidence:** Runtime-mocked route test.
   - **Data integrity:** Potentially affected in a real request.

5. **TEST environment database loader mismatch**
   - **Behavior:** Existing integration test failed because `db_connection.DATABASE_URL` was `None` while the fixture set `DATABASE_URL` from `.env.test`.
   - **Expected:** Application database loader uses the explicitly selected TEST database.
   - **Affected module:** `app/database/db_connection.py`.
   - **Severity:** High.
   - **Evidence:** `tests/integration/test_environment.py`: 1 failed, 3 passed.
   - **Data integrity:** Prevented reliable end-to-end database testing.

## 6. Implementation Gaps

- No `/chat` endpoint exists; the implemented employee chat route is `/employee/question`.
- No conversation-by-ID or analysis-by-ID application endpoints were found, so tenant/user access control could not be exercised through real endpoints.
- No TEST-only LLM/provider configuration is present for the analysis path.
- Existing failure-path tests for chat, retrieval, and analysis are absent.
- The database schema does not duplicate tenant/user identity on `conversation_analysis`, limiting direct integrity assertions.

## 7. Security Findings

- Authentication rejection for missing and malformed tokens passed in the tested endpoints.
- Both TEST users resolved to distinct tenant IDs through the authenticated identity endpoint.
- Cross-tenant and cross-user conversation access could not be assessed because the relevant endpoints are absent; this is an unverified security area, not evidence of a bypass.
- The chat route obtains `company_id` from the server-side user record rather than a client-provided company ID in the observed code path.
- No credentials, bearer token values, or API keys are included in this report.

## 8. Data Integrity Findings

- One existing Cola conversation has no corresponding analysis.
- No orphan analysis rows were found.
- The route does not enforce atomicity between conversation creation and analysis creation.
- A successful HTTP response can coexist with missing analysis.
- Existing conversation rows include company and user IDs; analysis rows are related only by conversation ID.

## 9. Recommended Next Actions

1. Provide a dedicated TEST-safe LLM and conversation-analysis provider configuration, separate from `.env`.
2. Resolve the TEST database loader mismatch before relying on integration results.
3. Define and test the intended transaction/rollback policy for conversation plus analysis persistence.
4. Make analysis failure visible in the API response or enforce rollback, then add a regression test.
5. Reject empty and whitespace-only questions before retrieval.
6. Add real endpoint tests for conversation and analysis retrieval/modification isolation, if those capabilities are intended.
7. Investigate and reconcile the existing Cola conversation without analysis.
8. Add failure-injection tests for retrieval, LLM, conversation persistence, and analysis persistence.

## 10. Final Classification

**Initial run: FAIL**

The initial classification reflected the pre-remediation TEST evidence:
missing analysis data, swallowed analysis failure, accepted empty input, and
the database-loader import-order defect.

**Re-test classification: PASS WITH REMEDIATION**

The re-test verified the route safeguards and TEST database configuration,
but the existing Cola missing-analysis record, unavailable TEST employee
sign-in, absent conversation access endpoints, and non-atomic conversation
then-analysis persistence remain documented limitations.
