---
name: issue-executor
description: Use to execute a MercadoIA BO technical issue with repository-first scope, controlled Jira MCP management, mandatory validations, Tech Lead Reviewer handoff, and human approval gates for commit, push and card completion.
---

# Issue Executor

## Objective

Standardize how Codex executes one technical issue at a time in the MercadoIA BO project.

The repository is the technical source of truth. Jira is only a management and visibility layer.

## When To Use

Use this skill before executing any technical issue, especially when the user asks to run an issue by number and title.

Do not use this skill to infer or start the next issue automatically.

## Required User Input

Before starting, confirm the user supplied:

1. Technical issue number.
2. Technical issue title.
3. Whether Codex is authorized to move the Jira card to Em andamento.
4. Whether Codex is authorized to commit after human approval.
5. Whether Codex is authorized to push after human approval.
6. Whether Codex is authorized to move the Jira card to Itens concluídos after human approval.

If any item is missing, ask for clarification before changing Jira, files or Git state.

## Required Files To Read

Read these before implementation:

1. `AGENTS.md`
2. `README_TECNICO.md`
3. `docs/technical/issues_iniciais.md`
4. `docs/technical/architecture_decisions.md`
5. `docs/technical/security_matrix.md`
6. `docs/technical/permission_matrix.md`
7. `docs/technical/rls_strategy.md`
8. `docs/agent-skills/tech-lead-reviewer/SKILL.md`
9. `docs/agent-skills/tech-lead-reviewer/checklist.md`
10. `docs/agent-skills/tech-lead-reviewer/report_template.md`
11. Issue-specific files, plans, models, services, routes, tests and docs required by the scope.

## Relationship With Tech Lead Reviewer

Issue Executor controls execution flow.

Tech Lead Reviewer is mandatory before any issue is considered complete, before recommending commit, and before final handoff.

If Tech Lead Reviewer recommends `reprovado`, stop and report the blockers. Do not commit, push, comment final evidence or move the Jira card to Itens concluídos.

## Repository Source Of Truth

The technical source of truth is the repository, especially:

1. `AGENTS.md`
2. `docs/technical/issues_iniciais.md`
3. `docs/technical/architecture_decisions.md`
4. `docs/technical/security_matrix.md`
5. `docs/technical/permission_matrix.md`
6. `docs/technical/rls_strategy.md`
7. PRDs and versioned technical docs
8. `docs/agent-skills/tech-lead-reviewer/`

Jira must never replace or redefine repository scope.

## Jira Usage

Use Jira only to:

1. Locate the card corresponding to the technical issue.
2. Move the card to Em andamento when implementation starts, if authorized.
3. Comment that execution started, if authorized.
4. Comment final evidence after implementation, approval, commit and push, if authorized.
5. Move the card to Itens concluídos after human approval, commit and push, if authorized.

Never edit Jira scope, description, sprint, assignee or acceptance criteria without human approval.

For the detailed Jira flow, read `jira_flow.md`.

## Execution Workflow

Read and follow `workflow.md`.

## Final Report

Use `final_report_template.md` for the Issue Executor handoff.

The final report must include the Tech Lead Reviewer result and must clearly say whether commit, push and Jira completion are allowed.

## Example Usage

User request:

```text
Execute a Issue 016: Criar Permission Guard no backend usando a Issue Executor Skill.

Autorizado:
mover card para Em andamento: sim
commitar após aprovação humana: sim
fazer push após aprovação humana: sim
mover para Itens concluídos após aprovação humana: sim

Não autorizado:
avançar para próxima issue
editar escopo no Jira
alterar sprint
alterar responsável
```

Codex must execute only Issue 016, use repository docs for scope, use Jira only as authorized, apply Tech Lead Reviewer, then stop for human approval.

## Stop Rule

After implementation and Tech Lead Reviewer report, stop and wait for human approval.

Do not commit, push, comment final evidence or move to Itens concluídos unless the user explicitly authorizes those actions.
