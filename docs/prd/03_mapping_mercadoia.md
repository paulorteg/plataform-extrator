# PRD 03: Mapping MercadoIA

## Objetivo

Transformar dados do Modelo Canônico nos campos exigidos pelo template MercadoIA.

## Princípios

1. O template não conhece o BO original.
2. Campo obrigatório ausente não é inventado.
3. Todo campo automático deve ter evidência.
4. Mapping deve ser declarativo e versionado em JSON.
5. Campo manual prevalece sobre automático.
6. Fallback deve ser explícito.

## Campos obrigatórios prioritários

1. CNPJ Vítima
2. Tipo Sinistro
3. Data Evento
4. Cidade Evento
5. UF Evento
6. Evento ou Natureza
7. Mercadoria
8. Data Embarque
9. CPF Motorista
10. Placa veículo Sinistrado
11. Cidade Emplacamento
12. UF Emplacamento

## Saída por campo

Cada campo mapeado deve conter template_field, value, status, source_status, confidence, evidence_id, validation_status, requires_review e review_reason.

## Critérios de aceite

1. Mapping JSON criado.
2. Loader implementado.
3. Validador implementado.
4. Obrigatórios ausentes geram pendência.
5. Campo inválido bloqueia aprovação.
