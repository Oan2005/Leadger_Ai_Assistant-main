# Phase 7B — `/signin` User Lookup Diagnosis

**Date:** 2026-10-03  
**Environment:** TEST only  
**Scope:** `login()` and `get_user_by_id()` database selection and truthiness behavior

## 1. Root Cause

The `if not user_info:` condition was not evaluating a valid application-user
record as false.

The root cause was environment selection:

1. `app/database/db_connection.py` called `load_dotenv()`.
2. When only `TEST_DATABASE_URL` was supplied, `.env` could populate the
   canonical `DATABASE_URL` with the non-TEST database.
3. The application then queried that database.
4. The TEST Auth user ID was absent there, so `get_user_by_id()` returned
   `None`.
5. `if not user_info:` correctly evaluated to `True`.

When the application connection was explicitly pointed at the TEST database,
the same lookup returned a normal non-empty dictionary.

## 2. `get_user_by_id()` Behavior

The function executes a PostgreSQL query selecting:

```text
user_id, company_id, full_name, email, role, phone
```

For an existing row it returns:

```text
type: <class 'dict'>
bool: True
is None: False
```

For no matching row it returns `None`.

For TEST user
`5c1729f4-18c9-4b7a-b7d7-abc629d83357`, the raw TEST database result was a
six-element tuple and `get_user_by_id()` converted it to a dictionary with
the six expected keys.

No falsey response wrapper, custom `__bool__`, Pydantic object, or unusual
result type was involved.

## 3. Fixes

- [db_connection.py](../app/database/db_connection.py)
  - When `TEST_ENV` is enabled, `TEST_DATABASE_URL` takes precedence.
  - If the fixture has injected canonical `DATABASE_URL` instead, that value
    is used as a fallback.
  - Normal non-TEST configuration remains unchanged.

- [users_crud.py](../app/database/crud/users_crud.py)
  - Added the missing module logger so lookup exceptions do not raise a
    secondary `NameError`.

- [test_environment.py](../tests/integration/test_environment.py)
  - Added structural lookup assertions.
  - Added direct login-contract assertions.
  - Added HTTP `/signin` regression coverage for existing and missing
    application users.

The `if not user_info:` condition was not changed because the diagnosis
proved that the intended return contract is `dict` for an existing user and
`None` for a missing user.

## 4. Authentication Results

| Test | Result | Evidence |
|---|---|---|
| Missing token | PASS | Protected endpoint returned HTTP 401. |
| Invalid credentials | PASS | Existing authentication regression tests passed; invalid credentials map to HTTP 401. |
| Valid TEST employee | PASS | Both configured TEST employees signed in with HTTP 200 and `success: true` when TEST DB was selected. |
| Missing application user | PASS | `/signin` returned HTTP 403 for a valid-but-absent application UUID. |

## 5. Real `/employee/question`

**BLOCKED.**

Authentication now succeeds against TEST, but a real chat request was not
sent because the current LLM and conversation-analysis provider configuration
does not provide a dedicated TEST-only provider credential. Sending the
request would risk using the non-TEST `.env` provider configuration, which is
prohibited by the test rules.

No Pinecone, conversation, or analysis data was modified by this phase.

## 6. Regression Results

Latest complete suite after the authentication fix:

```text
67 passed
4 skipped
0 failed
4 warnings
```

Additional focused authentication regression suite:

```text
29 passed
```

Pylance diagnostics for the changed files reported no errors.

## 7. Remaining Issues

- Real `/employee/question` end-to-end verification remains blocked pending a
  TEST-only LLM and conversation-analysis provider configuration.
- Conversation and analysis persistence remain separate commits; analysis
  failure can still leave a conversation without analysis while returning
  HTTP 503.
- The existing TEST Cola data still contains one conversation without a
  corresponding analysis.

## 8. Final Classification

**PASS WITH REMEDIATION**

The `/signin` truthiness diagnosis is confirmed and fixed at the environment
selection root cause. Existing and missing application-user behavior is
covered by regression tests. Real chat remains blocked for TEST-provider
configuration reasons.

## Phase 7C Addendum — Real TEST Chat Validation

The TEST-only OpenRouter credential was subsequently configured in `.env.test`
under `TEST_OPENROUTER_API_KEY`. Its value was not printed or included in
this report.

### Environment safety

- TEST database: confirmed; current database `postgres`, schema `public`.
- TEST Pinecone: confirmed; index `leadger-test`.
- TEST LLM: confirmed; both chat and analysis clients resolved the OpenRouter
  provider using the TEST-scoped credential.
- Production fallback: prevented by `llm_config.get_openrouter_api_key()`,
  which requires `TEST_OPENROUTER_API_KEY` whenever `TEST_ENV=true`.

### Real E2E request

One real request was sent as the Pepsi TEST employee:

- Login: HTTP 200, `success: true`.
- Identity: employee user
  `5c1729f4-18c9-4b7a-b7d7-abc629d83357`, company
  `2568d8c6-1455-4b21-9b55-30d3b49a6752`.
- Endpoint: `POST /employee/question`.
- HTTP status: 200.
- Response keys: `answer`, `confidence`, `session_id`.
- Confidence: `0.95`.
- Answer content: not included; length was 400 characters.
- End-to-end elapsed time: approximately 32.1 seconds.

### Persistence verification

The request created:

- Conversation:
  `81bd887e-d785-4d80-80ae-ed5a67db3887`
- Analysis:
  `f09a920e-d303-4c52-b342-1a03cdea517a`

Conversation verification:

- `user_id` matched the authenticated Pepsi employee.
- `company_id` matched the authenticated Pepsi company.
- Response time: 3453 ms.
- Confidence: 0.95.
- Prompt tokens: 1418.
- Completion tokens: 288.
- Cached: false.
- Three retrieved-document links were persisted.

Analysis verification:

- Analysis existed.
- `conversation_id` matched the new conversation.
- All analysis fields were populated.
- No orphan analysis was created.

### Tenant retrieval verification

Read-only retrieval used the expected TEST namespaces:

- Cola → `cola`
- Pepsi → `pepsi`

The existing ready-status filter remained present:

```python
filter={"status": {"$eq": "ready"}}
```

### Final regression results

```text
Focused Phase 7/authentication tests: 45 passed
Full suite: 69 passed, 4 skipped, 0 failed, 4 warnings
```

No additional application code changes were made for the E2E request.

**Phase 7C classification: PASS WITH REMEDIATION**
