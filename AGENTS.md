# AGENTS.md

## Missão do agente de código

Implementar a plataforma MercadoIA BO com segurança, rastreabilidade, multiempresa, auditoria, evidência por campo, revisão humana e baixo custo operacional.

## Modo de trabalho

1. Trabalhe incrementalmente, uma issue por vez.
2. Antes de implementar, leia a documentação indicada pela issue.
3. Não avance para issues posteriores sem confirmação explícita.
4. Não crie funcionalidades extras fora do escopo solicitado.
5. Antes de editar arquivos, explique o plano quando solicitado.
6. Preserve alterações existentes que não fazem parte da sua tarefa.
7. Prefira mudanças pequenas, revisáveis e alinhadas à arquitetura documentada.

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

## Regras de segurança e LGPD

1. Não commite `.env`.
2. Não commite BO real não anonimizado.
3. Não use dados reais sensíveis em fixtures, prints, logs ou documentação.
4. Mascare dados pessoais conforme `docs/technical/security_matrix.md`.
5. Trate dados sensíveis como privados por padrão.

## Regras de autorização e multiempresa

1. O backend é a fonte final de autorização.
2. O frontend pode ocultar ações, mas nunca substituir validação no backend.
3. Permissão não substitui entitlement de plano.
4. Entitlement de plano não substitui permissão.
5. Admin global não acessa BO sensível por padrão.
6. Toda operação operacional deve respeitar a organização ativa.

## Regras de processamento documental

1. Extração determinística deve ser tentada antes de LLM.
2. O Modelo Canônico deve existir antes da geração de template.
3. Mapping deve ser declarativo e versionado.
4. Revisão humana faz parte do MVP.
5. Todo valor automático deve manter referência à sua evidência.

## Testes e validação

1. Toda feature crítica exige teste.
2. Toda alteração de banco exige migration.
3. Toda issue deve validar permissões, `organization_id`, auditoria e logs seguros quando aplicável.
4. Alterações documentais devem ser validadas por revisão do conteúdo e diff.
5. Dados reais só podem ser usados se estiverem anonimizados.

## Tech Lead Reviewer Skill

Antes de concluir qualquer issue, o Codex deve ler e aplicar:

`docs/agent-skills/tech-lead-reviewer/SKILL.md`

Essa revisão é obrigatória antes de considerar uma issue concluída, recomendar commit ou entregar relatório final.

Regras:

1. Aplicar o checklist da skill contra escopo, Supabase First, segurança, LGPD, migrations, seeds, testes, logs, commits e push.
2. Usar o template de relatório final da skill quando reportar a conclusão da issue.
3. Parar ao final da issue e aguardar aprovação humana.
4. Não fazer push sem autorização humana explícita.
5. Não avançar automaticamente para a próxima issue.
6. Não aprovar alterações fora do escopo sem justificativa.
7. Não aprovar segredo real, autenticação própria no MVP, `password_hash`, `hash_password` ou `verify_password`.
8. Não aprovar logs de `Authorization`, body completo, OCR completo, prompt completo ou narrativa completa.

## Definition of Done

Uma tarefa só está concluída quando código, testes, permissões, organization_id, auditoria, migrations, logs seguros e documentação relacionada foram tratados conforme o escopo.

## Ao finalizar uma tarefa

Informe arquivos criados, arquivos alterados, testes criados, comandos para rodar testes, migrations, riscos e pendências.
