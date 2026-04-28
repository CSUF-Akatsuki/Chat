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

## Change log (updated as work proceeds)

| Date | Change | File(s) | Author |
|------|--------|---------|--------|
| 2026-04-28 | Document created | `MICROSERVICE_REBASE_CHANGES.md` | Josh |
| _pending_ | Rebase onto new main | (entire branch) | Josh |
| _pending_ | Fix DB schema mismatch | `database.py`, `lib.py` | Josh |
| _pending_ | Fix lambda import paths | `friends_lambda.py`, `message_lambda.py` | Josh |
| _pending_ | Sanitize env.json | `env.json` | Josh |

## Approval

Teammate (original author of `refactor-to-microservice-and-lambda`) has approved the rebase approach as of 2026-04-28.
