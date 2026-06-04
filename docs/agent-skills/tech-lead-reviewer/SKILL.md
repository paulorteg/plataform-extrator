---
name: tech-lead-reviewer
description: Use before concluding any MercadoIA BO issue to perform a Tech Lead review against scope, Supabase First architecture, security, LGPD, migrations, seeds, tests, logs, commits, and push rules.
---

# Tech Lead Reviewer

## Objective

Apply a mandatory Tech Lead review before any issue implemented by Codex is considered complete.

This project is Supabase First and handles sensitive BO data, private documents, authentication, authorization, OCR, LLM, audit logs and LGPD concerns. The review must be conservative and must block unsafe or out-of-scope changes.

## When To Use

Use this skill:

1. Before finalizing any implemented issue.
2. Before recommending commit of an issue.
3. Before saying an issue is complete.
4. When the user asks for review, acceptance check, self-review or Tech Lead review.

Do not use this skill to advance to the next issue. Stop at the end of the current issue and wait for human approval.

## Required Files To Read

Read these before reviewing:

1. `AGENTS.md`
2. `README_TECNICO.md`
3. `docs/technical/issues_iniciais.md`
4. `docs/technical/architecture_decisions.md`
5. `docs/technical/security_matrix.md`
6. `docs/technical/permission_matrix.md`
7. `docs/technical/rls_strategy.md`
8. The issue-specific files changed by the implementation.
9. Any issue-specific plan or technical document referenced by the user.

For detailed review steps, read `checklist.md`.

For the final response format, use `report_template.md`.

## How To Apply

1. Identify the exact issue and requested scope.
2. Read the required files.
3. Compare the implementation with the requested scope.
4. Run or verify applicable tests and validations.
5. Check automatic rejection rules.
6. Produce a final report using `report_template.md`.
7. Stop and wait for human approval.

## Before Implementing

Check:

1. The issue number and scope are clear.
2. The task does not require advancing to another issue.
3. Required docs were read.
4. Supabase First constraints are understood.
5. Security, LGPD, organization and permission rules are known.
6. Migrations, seeds and tests needed by the issue are identified.

## After Implementing

Check:

1. Only scoped files changed, or every exception is justified.
2. Tests and compile checks were run or explicitly marked as not applicable.
3. Migrations were validated when database schema changed.
4. Seeds are idempotent when seeds were added or changed.
5. Logs do not expose sensitive data.
6. No secrets, tokens or real credentials were added.
7. No push was made without human authorization.
8. The final report uses `report_template.md`.

## Automatic Rejection Rules

Recommend `reprovado` if any item is true:

1. Real secret, token or credential was added.
2. Change outside scope lacks clear justification.
3. Authentication own logic was added in the MVP.
4. `password_hash` was added.
5. `hash_password` or `verify_password` was added.
6. `Authorization` header is logged.
7. Full request body is logged by default.
8. Full OCR text, full prompt or full narrative is logged.
9. Permanent public URL is used for private documents.
10. Service role key is used in frontend code.
11. Real RLS policy is created outside a specific approved RLS issue.
12. Migration was added without test or validation.
13. Seed is not idempotent.
14. Private endpoint lacks authentication after auth exists.
15. Operational endpoint lacks `organization_id` validation after organization middleware exists.
16. Permission Guard is incomplete when the issue involves authorization.
17. LLM is called outside the LLM Gateway.
18. OCR is called outside the OCR Provider Interface.
19. Codex advanced automatically to the next issue.
20. Push was made without human authorization.

## Supabase First Rules

1. Supabase Auth owns login, password, password recovery and session.
2. FastAPI validates tokens and applies internal authorization.
3. Do not implement password auth in FastAPI for the MVP.
4. Do not create `password_hash`, `hash_password` or `verify_password`.
5. Supabase Postgres is the primary MVP database.
6. Supabase Storage private buckets are the primary MVP storage.
7. RLS is defense in depth and does not replace backend validation.
8. `SUPABASE_SERVICE_ROLE_KEY` is backend-only and must never reach the frontend.

## Security And LGPD Rules

1. Do not use real BO data unless anonymized.
2. Do not commit `.env`.
3. Do not expose CPF, RG, CNH, phone, email, full address, full narrative, full OCR, prompts, tokens or signed URLs in logs.
4. Treat private documents as sensitive by default.
5. Prefer masked data in tests, docs and examples.

## Migrations Rules

1. Every schema change requires an Alembic migration.
2. Migration must be validated with a local or configured database.
3. Do not delete existing migrations.
4. Do not create product tables outside the issue scope.
5. Do not create RLS policies unless the issue explicitly authorizes RLS.

## Seeds Rules

1. Seeds must be idempotent.
2. Seeds must avoid real data.
3. Seeds must use deterministic or stable keys when possible.
4. Seeds must be tested or manually validated.

## Tests Rules

1. Critical features require tests.
2. Database constraints require tests or migration validation.
3. Security decisions require explicit tests when feasible.
4. If tests are not run, explain why and list residual risk.

## Logs Rules

1. Logs must include technical context without sensitive payloads.
2. Do not log request body by default.
3. Do not log `Authorization`.
4. Do not log full OCR, full prompts, full narratives or temporary URLs.
5. Preserve `request_id` in errors when applicable.

## Commits And Push Rules

1. Recommend commit only after review passes or passes with documented caveats.
2. Stage files explicitly; do not recommend `git add .` when unrelated files exist.
3. Commit message must match the issue scope.
4. Do not push automatically.
5. Push only when the user explicitly asks for it.

## Final Report

Use `report_template.md` for the final issue review report.

The report must state:

1. Recommended status: `aprovado`, `aprovado com ressalvas` or `reprovado`.
2. Scope requested and implemented.
3. Files created and altered.
4. Tests and validation commands.
5. Security checks.
6. Risks and pending items.
7. Whether commit is recommended.
8. Whether push is allowed.

After reporting, stop and wait for human approval.
