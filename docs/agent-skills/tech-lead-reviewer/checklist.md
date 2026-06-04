# Tech Lead Reviewer Checklist

## Scope

- [ ] Issue number and requested scope are clear.
- [ ] No next issue was implemented.
- [ ] No unrelated refactor was added.
- [ ] Every changed file belongs to the issue or has a documented reason.
- [ ] Existing user changes were preserved.

## Supabase First

- [ ] Supabase Auth remains responsible for login, password, password recovery and session.
- [ ] FastAPI remains responsible for business rules and internal authorization.
- [ ] No password auth was implemented in FastAPI.
- [ ] No `password_hash`, `hash_password` or `verify_password` was added.
- [ ] Service role key is not used in frontend.
- [ ] RLS is treated as defense in depth and not as a backend validation replacement.
- [ ] No real RLS policy was created unless explicitly approved.

## Security And LGPD

- [ ] No real secret, token or credential was added.
- [ ] No `.env` file was committed.
- [ ] No real non-anonymized BO data was added.
- [ ] Sensitive data is masked in tests, examples and docs.
- [ ] Private documents remain private.
- [ ] No permanent public document URL was introduced.
- [ ] Admin/global access does not bypass sensitive BO access rules.

## Database And Migrations

- [ ] Every schema change has an Alembic migration.
- [ ] Migration was validated with local or configured database.
- [ ] Existing migrations were not deleted.
- [ ] No product table was added outside scope.
- [ ] `organization_id` is present for operational tables when applicable.
- [ ] RLS policy changes are only present in explicit RLS issues.

## Seeds

- [ ] Seeds are idempotent.
- [ ] Seeds do not insert real data.
- [ ] Seed keys are stable or deterministic when appropriate.
- [ ] Seed execution was tested or manually validated.
- [ ] Re-running seed does not duplicate rows.

## Tests

- [ ] Automated tests were added or updated when behavior changed.
- [ ] Database constraints are covered by tests or migration validation.
- [ ] Security decisions are covered by tests when feasible.
- [ ] Test command was run.
- [ ] Test result is reported.
- [ ] If tests were not run, reason and residual risk are documented.

## Logs

- [ ] Logs do not include `Authorization` header.
- [ ] Logs do not include request body by default.
- [ ] Logs do not include tokens, secrets or signed URLs.
- [ ] Logs do not include full OCR, full prompt or full narrative.
- [ ] Errors preserve `request_id` when applicable.

## Documentation

- [ ] README or technical docs were updated when architecture, env vars, migrations, seeds or commands changed.
- [ ] Issue backlog reflects adapted Supabase First scope when relevant.
- [ ] Plans are clearly marked as plans when implementation is not authorized.
- [ ] Documentation does not include real secrets or real sensitive data.

## Before Commit

- [ ] `git status` or equivalent scoped check was reviewed.
- [ ] Staged files match the issue scope.
- [ ] No unrelated local files are staged.
- [ ] Commit message matches the issue.
- [ ] Push is not performed without explicit human request.

## Automatic Rejection

- [ ] No real secret was added.
- [ ] No unjustified out-of-scope change exists.
- [ ] No authentication own logic was added in MVP.
- [ ] No `password_hash` exists.
- [ ] No `hash_password` or `verify_password` exists.
- [ ] No `Authorization` header is logged.
- [ ] No full request body is logged by default.
- [ ] No full OCR, prompt or narrative is logged.
- [ ] No permanent public URL for private documents exists.
- [ ] No service role key is used in frontend.
- [ ] No RLS real policy exists outside specific approved issue.
- [ ] No migration lacks test or validation.
- [ ] No seed is non-idempotent.
- [ ] No private endpoint lacks auth after auth exists.
- [ ] No operational endpoint lacks organization validation after organization middleware exists.
- [ ] No incomplete Permission Guard exists for authorization issue.
- [ ] No LLM call bypasses LLM Gateway.
- [ ] No OCR call bypasses OCR Provider Interface.
- [ ] No automatic next issue was implemented.
- [ ] No push was performed without human authorization.
