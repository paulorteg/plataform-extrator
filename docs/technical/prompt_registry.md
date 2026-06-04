# prompt_registry.md

## Princípios

1. LLM é seletivo.
2. LLM não valida CPF, CNPJ, placa ou data.
3. LLM não inventa dados.
4. Toda resposta útil precisa de evidência.
5. Prompt é versionado.
6. Output schema é obrigatório.

## Prompts V1

1. semantic_claim_type_v1
2. semantic_goods_extraction_v1
3. semantic_driver_selection_v1
4. semantic_damaged_vehicle_selection_v1
5. semantic_occurrence_summary_v1
6. semantic_shipper_extraction_v1
7. semantic_criminal_object_v1

## Critérios de rejeição

Resposta fora do schema, sem evidência, com dado inventado, com categoria fora da lista, com dados formais sem fonte literal ou com múltiplas ocorrências misturadas.
