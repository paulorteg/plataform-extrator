# AGENTS.md

## Missão do agente de código

Implementar a plataforma MercadoIA BO com segurança, rastreabilidade, multiempresa, auditoria, evidência por campo, revisão humana e baixo custo operacional.

## Regras globais obrigatórias

1. Toda rota privada exige autenticação.
2. Toda rota operacional exige organização ativa.
3. Toda consulta operacional filtra por `organization_id`.
4. Toda ação protegida valida permissão no backend.
5. Toda ação crítica gera Audit Log.
6. Todo arquivo original fica em storage privado.
7. Toda URL de arquivo é temporária.
8. Todo campo automático precisa de evidência.
9. Nenhuma chamada de LLM pode ocorrer fora do LLM Gateway.
10. Nenhum OCR pode ocorrer fora da OCR Provider Interface.
11. Campo ausente não deve ser inventado.
12. Campo manual aprovado prevalece sobre automático.
13. Retry não pode duplicar consumo.
14. Template final só pode ser gerado a partir de versão aprovada.
15. Logs técnicos não podem expor senha, token, CPF completo, RG, CNH, telefone, email, endereço completo, narrativa integral, OCR completo ou URL temporária.

## Definition of Done

Uma tarefa só está concluída quando código, testes, permissões, organization_id, auditoria, migrations, logs seguros e documentação relacionada foram tratados conforme o escopo.

## Ao finalizar uma tarefa

Informe arquivos criados, arquivos alterados, testes criados, comandos para rodar testes, migrations, riscos e pendências.
