# Issue Executor Workflow

## 1. Preparation

1. Confirm required user input:
   - technical issue number
   - technical issue title
   - Jira Em andamento authorization
   - commit authorization after human approval
   - push authorization after human approval
   - Jira Itens concluídos authorization after human approval
2. Run `git status --short`.
3. Identify existing local changes and separate unrelated work.
4. Read all required repository files.
5. Read issue-specific files.
6. Produce a short implementation plan before editing files.

## 2. Jira Em Andamento

1. Locate the Jira card by technical issue title.
2. Confirm the card key, title and current status.
3. If authorized, move only that card to Em andamento.
4. If authorized, add a short start comment.
5. Do not edit scope, description, sprint, assignee or acceptance criteria.

## 3. Implementation

1. Implement only the approved issue scope.
2. Prefer existing project patterns.
3. Keep changes small and reviewable.
4. Do not advance to the next issue.
5. Do not create broad refactors.
6. Do not change migrations, seeds, frontend, storage, OCR, LLM or docs unless required by the current issue.

## 4. Validation

Run applicable checks:

1. Focused tests for the issue.
2. Full API or affected package test suite.
3. `compileall` for Python changes.
4. Frontend tests only when frontend changed.
5. Migration validation when migrations changed.
6. Security searches for secrets, RLS, auth bypasses and unsafe logs.
7. `git status --short` and scoped diff review.

## 5. Tech Lead Review

1. Read and apply `docs/agent-skills/tech-lead-reviewer/SKILL.md`.
2. Use its checklist and report template.
3. If it recommends `reprovado`, stop and report blockers.
4. If it recommends `aprovado` or `aprovado com ressalvas`, continue to the human approval phase.

## 6. Human Approval

Stop after the report unless the user already gave explicit permission for the next action.

Required approvals are separate:

1. Commit.
2. Push.
3. Final Jira evidence comment.
4. Moving Jira card to Itens concluídos.

## 7. Commit And Push

1. Stage files explicitly.
2. Never use `git add .`.
3. Keep unrelated local changes out of the commit.
4. Use the recommended commit message or the user's message.
5. Push only with explicit human approval.

## 8. Jira Evidence

After approval, commit and push:

1. Comment final evidence using the template in `jira_flow.md`.
2. Include summary, tests, commit hash and status.
3. Do not include secrets, tokens or sensitive data.

## 9. Card Completion

Move the Jira card to Itens concluídos only when all are true:

1. Tech Lead Reviewer approved or approved with documented caveats.
2. Human explicitly approved card completion.
3. Commit was created.
4. Push succeeded.
5. Final evidence was commented or the human explicitly skipped it.

## 10. Mandatory Stop

Stop after the current issue.

Do not start the next issue, even when the next Jira card is obvious.
