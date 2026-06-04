# regression_fixtures_plan.md

## Objetivo

Criar base de BOs sintéticos ou anonimizados para regressão documental.

## Cobertura MVP

SP Polícia Civil, SP Muralha Paulista, RJ Registro de Ocorrência, BA, PE, MG, PRF DAT, BO de trânsito e desconhecido.

## Regras

1. Nenhum dado real não anonimizado entra no repositório.
2. Cada fixture tem expected JSON.
3. Campo inventado é falha crítica.
4. Evidência é validada quando possível.
5. Regressão rápida roda em PR.
6. Regressão completa roda antes de deploy.

## Métricas

field_accuracy, missing_correctness, hallucination_rate, evidence_coverage, segmentation_accuracy e custo por ocorrência.
