# PRD 02: Modelo Canônico

## Objetivo

Definir uma representação intermediária independente do layout original do BO. O Modelo Canônico permite suportar documentos diferentes e gerar múltiplos templates futuros.

## Estrutura principal

1. Documento de origem
2. Ocorrência
3. Boletim
4. Evento
5. Locais
6. Naturezas
7. Envolvidos
8. Empresas
9. Veículos
10. Cargas
11. Objetos
12. Autoridade policial
13. Evidências
14. Validações
15. Confiança

## Regras

1. Campos ausentes devem ser explícitos quando relevantes.
2. Listas devem preservar múltiplos envolvidos, veículos, empresas e cargas.
3. Campo automático deve conter status, confiança e evidence_id.
4. Campo manual aprovado prevalece.
5. Schema deve ser versionado.

## Status de campo

1. extraido
2. inferido
3. gerado
4. manual
5. nao_encontrado
6. baixa_confianca
7. inconsistente
8. invalido
9. aprovado
10. nao_aplicavel
11. justificado
12. mascarado

## Critérios de aceite

1. JSON Schema criado.
2. Payload válido passa no validador.
3. Payload inválido falha.
4. Ocorrência suporta múltiplos veículos e envolvidos.
5. Evidências podem ser vinculadas por campo.
