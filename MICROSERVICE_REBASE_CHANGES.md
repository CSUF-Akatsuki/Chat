# Microservice Rebase — Change Log

This document tracks changes made to the `refactor-to-microservice-and-lambda` branch (originally authored by teammate) during integration with `main`. The goal is full transparency on every modification to that branch's files.

## Background

- The `refactor-to-microservice-and-lambda` branch was originally forked from `main` *before* the AWS deployment work landed.
- Phase 2/3 AWS hardening (RDS SSL, Redis SSL, CloudFront CORS origin, DB initializer SSL) was committed on `phase-2-code-modifications` and is now being merged into `main`.
- The microservice branch must be rebased onto the new `main` so it inherits the AWS-hardened baseline before further work.

## Branches involved

| Branch | Role |
|--------|------|
| `main` | Target. After the phase-2 PR merges, contains AWS-hardened code currently running in production. |
| `refactor-to-microservice-and-lambda` | Source of microservice/Cognito work. To be rebased onto `main`. |

## Planned changes to `refactor-to-microservice-and-lambda`

### 1. Rebase onto new `main`

The branch will be rebased (not merge-committed) onto `main` after the phase-2 PR lands. Conflict resolution rules:

| File | Conflict Reason | Resolution Strategy |
|------|-----------------|---------------------|
| `backend/shared/db/database.py` (or `server/app/db/database.py`) | Phase-2 adds `sslmode=require`; refactor branch is clean | Keep phase-2 SSL config; integrate into refactor branch's structure |
| `backend/shared/config.py` (or `server/app/core/config.py`) | Phase-2 has CloudFront CORS origin; refactor branch hardcodes localhost | Keep phase-2 CORS origin; merge with refactor branch's Cognito config additions |
| `backend/shared/redis_service.py` (or `server/app/core/redis_service.py`) | Phase-2 has `ssl=True` and cert handling | Keep phase-2 Redis SSL; preserve refactor branch's any Redis logic |
| `requirements.txt` / `pyproject.toml` | Both branches add deps | Union of both — keep phase-2 deps and add `pycognito`, `aws-lambda-powertools` |
| `Dockerfile` | Both modified | Verify entrypoint compatibility; favor phase-2 if conflict on AWS-specific lines |
| `client/src/api/axiosInstance.ts` and friends | Phase-2 has axios baseURL changes | Keep phase-2 axios config |

### 2. Bug fixes on rebased branch

After rebase, the following bugs (identified during code review) will be fixed in dedicated commits:

#### 2a. Database schema mismatch (`backend/shared/db/database.py`, `backend/lambdas/lib.py`)
- Schema declares `cognito_id UUID PRIMARY KEY` but lambda queries reference integer `id` and `username`.
- `lib.py:28` has a `# Handle schema variance between id and cognito_id` comment confirming the inconsistency.
- **Fix:** Standardize on Cognito `sub` (UUID) as PK across schema, queries, and lambda payloads. Remove the variance handling.

#### 2b. Lambda import paths (`backend/lambdas/friends_lambda.py`, `backend/lambdas/message_lambda.py`)
- Currently use `from backend.lambdas.auth_lambda import ...` which won't resolve in Lambda runtime.
- **Fix:** Convert to relative imports or restructure deployment package so the lambda zip root contains the modules at the expected paths.

#### 2c. Placeholder env values (`backend/env.json`)
- Contains `"XXXXX"` placeholders for Cognito pool/client IDs.
- **Fix:** Replace with real values, OR remove from repo and document in `README` how to populate locally. Ensure not committed to repo if real values are sensitive.

### 3. Out of scope (deferred to separate PRs)

- **Frontend Cognito migration** — `client/src/store/auth-slice/index.ts` still calls custom JWT endpoints. Will be migrated to AWS Amplify SDK in its own PR after backend lands.
- **API Gateway / IAM / VPC config** — will be provided by the Terraform requirement (project requirement #2). The microservice branch does not need to ship infra.
- **Production deployment of lambdas** — depends on Terraform completion.

## Change log (actual)

Listed in commit order. SHAs are short refs from `git log main..refactor-to-microservice-and-lambda`.

### Stage 1 — Pre-merge lambda-only fixes (2026-04-28)

| SHA | Change | Files |
|-----|--------|-------|
| `4553db2` | Standardize lambda import paths (drop broken `backend.` prefix) | `friends_lambda.py`, `message_lambda.py` |
| `34f848e` | Rename `env.json` → `env.json.example`, gitignore real config | `env.json`, `.gitignore`, `README.md` |
| `a26d962` | Replace `get_or_create_event_loop` with `asyncio.run` (60 lines removed) | `auth_lambda.py`, `friends_lambda.py`, `message_lambda.py`, `lib.py` |
| `a104400` | Add `_response()` helper, standardize all 16 handler returns; fix plain-string-body bugs in `auth_lambda` and the Token positional-arg inconsistency in `endpoint_refresh` | `auth_lambda.py`, `friends_lambda.py`, `message_lambda.py`, `lib.py` |
| `e34afd7` | Harden `extract_user_from_event` against missing authorizer; introduce `AuthError` | `lib.py` |

### Stage 2 — Merge main into branch (2026-04-28)

Originally planned as a rebase. Aborted mid-rebase after the first of his 10 commits produced a modify/delete on `server/app/main.py` plus rename-conflicts that would have compounded on each subsequent commit. Switched to `git merge main` for a single conflict-resolution session.

| SHA | Change | Files |
|-----|--------|-------|
| `7d2e045` | Merge commit. Resolved `.gitignore` (combined both versions, deduped). Accepted deletion of `server/app/main.py` (his refactor moved entry point to `backend/websocket_server.py`); phase-2 additions there ported in next commit. Verified auto-merged shared files preserved phase-2 SSL: `backend/shared/db/database.py`, `redis_service.py`, `config.py` all retain `ssl='require'` / `rediss://` / `?ssl=require`. | many |

### Stage 3 — Post-merge shared-file fixes (2026-04-28)

| SHA | Change | Files |
|-----|--------|-------|
| `89e07c8` | Port phase-2 CloudFront CORS origin and `/health` endpoint from deleted `server/app/main.py` to `backend/websocket_server.py` | `backend/websocket_server.py` |
| `4d69d80` | DB schema standardization: rename `cognito_id` → `cognito_sub`, fix INTEGER → UUID type mismatch on every user-FK column, remove the schema-variance workaround in `lib.py:28`, update lambda queries and pydantic models accordingly | `database.py`, `lib.py`, `friends_lambda.py`, `message_lambda.py`, `models/friends.py`, `models/messages.py`, `models/users_model.py` |
| `adaeccd` | WebSocket Cognito JWT verification using PyJWT's `PyJWKClient` to fetch and cache User Pool JWKs; `LOCAL_AUTH_MODE=true` env-var fallback to legacy `SECRET_KEY` HS256 path for offline development | `backend/websocket_server.py` |

### Out of scope (deferred to separate PRs)

- **Frontend Cognito migration** — `client/src/store/auth-slice/*` still calls the custom-JWT endpoints. The auth-success WebSocket payload now ships `user.cognito_sub` (UUID) instead of `user.id` (integer), which the frontend currently doesn't handle. Frontend Cognito migration is its own PR.
- **Secrets Manager fallback in `config.py`** — pydantic Settings still reads from env vars only. Decision: skip this code change. Terraform will inject Secrets Manager values into Lambda env vars at deploy time, which is sufficient.
- **Terraform / API Gateway / IAM / VPC** — project requirement #2.
- **Cleanup of `backend/old_code/`** — archive directory, not imported, but still has stale schema references. Leave for a future cleanup commit.
- **Pre-existing frontend TS errors** — 6 unused `import React` and 1 unused `wsError` variable. Not introduced by this PR; tackle alongside the frontend Cognito migration.

## Validation summary

| Check | Result |
|-------|--------|
| `python3 -m py_compile` on all current backend Python | ✅ pass |
| `pytest backend/tests/` | ⏭ skipped (needs `aws_lambda_powertools` in venv; tests are stubs per audit) |
| `cd client && npm run build` | ❌ fails on 6 pre-existing unused-import errors, not from this PR |
| Docker compose smoke | ⏭ skipped (no useful local AWS deps without Cognito User Pool) |

## Approval

Teammate (original author of `refactor-to-microservice-and-lambda`) authorized the rebase approach as of 2026-04-28 and is unavailable for ~2 days, so admin (Josh) drove the merge and post-merge fixes.
