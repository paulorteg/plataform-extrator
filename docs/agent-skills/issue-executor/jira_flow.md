# Jira Flow

## Locate Card

1. Search by technical issue title, for example `Issue 016: Criar Permission Guard no backend`.
2. Do not rely only on Jira issue key or board order.
3. If multiple cards match, report candidates and ask the human to choose.
4. If no card matches, report that Jira card was not found and continue only if the user allows implementation without Jira linkage.

## Move To Em Andamento

Move the card to Em andamento only when:

1. The user authorized it.
2. The card was matched by technical issue title.
3. Implementation is about to start.

Do not change sprint, assignee, description, labels, fields or acceptance criteria.

## Start Comment

Add a start comment only when authorized.

Template:

```text
Execução iniciada pelo Codex.

Issue técnica:
<issue number and title>

Fonte da verdade técnica:
Repositório.

Observação:
Jira será usado apenas para gestão e evidências.
```

## Final Evidence Comment

Add a final evidence comment only after human approval, commit and push.

Template:

```text
<issue number> implementada e revisada pela Tech Lead Reviewer Skill.

Resumo:
<short implementation summary>

Testes:
<focused tests result>
<full test result>
<compile or build result>

Commit:
<commit hash and message>

Status:
Aguardando ou executando movimentação autorizada do card.
```

## Move To Itens Concluidos

Move the card to Itens concluídos only when explicitly authorized after:

1. Implementation completed.
2. Tech Lead Reviewer approved.
3. Human approved.
4. Commit succeeded.
5. Push succeeded.
6. Final evidence comment was added or explicitly skipped by the human.

## Forbidden Jira Actions

Codex must not:

1. Use Jira as technical source of truth.
2. Change technical scope based only on Jira.
3. Edit description.
4. Edit acceptance criteria.
5. Change sprint.
6. Change assignee.
7. Create new Jira issues.
8. Delete or archive issues.
9. Move card to Itens concluídos without human approval.
10. Decide the next issue from Jira alone.
