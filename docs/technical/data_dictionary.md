# data_dictionary.md

## Campos obrigatórios

| Campo | Grupo | Tipo | Validação | Obrigatório |
|---|---|---|---|---|
| CNPJ Vítima | dados_sinistro | numeric_string | cnpj | sim |
| Tipo Sinistro | dados_sinistro | code | tipo_sinistro | sim |
| Data Evento | dados_sinistro | date | date | sim |
| Cidade Evento | dados_sinistro | text | city | sim |
| UF Evento | dados_sinistro | uf | uf | sim |
| Evento ou Natureza | dados_sinistro | text | natureza_evento | sim |
| Mercadoria | dados_sinistro | text | texto | sim |
| Data Embarque | dados_sinistro | date | date | sim |
| CPF Motorista | motorista | numeric_string | cpf | sim |
| Placa veículo Sinistrado | veiculo_sinistrado | text | placa_brasil | sim |
| Cidade Emplacamento | veiculo_sinistrado | text | city | sim |
| UF Emplacamento | veiculo_sinistrado | uf | uf | sim |

## Status de campo

extraido, inferido, gerado, manual, nao_encontrado, baixa_confianca, inconsistente, invalido, aprovado, nao_aplicavel, justificado, mascarado.

## Sensibilidade

Nível 1: operacional interno.
Nível 2: operacional restrito.
Nível 3: dado pessoal.
Nível 4: altamente restrito.
Nível 5: segredo.

## Regras críticas

1. CPF, CNPJ, placa e data não podem ser inventados.
2. Cidade e UF de emplacamento não devem ser inferidas pela placa.
3. Empresa vítima não deve ser embarcador sem evidência.
4. Campo automático precisa de evidência.
5. Campo obrigatório ausente bloqueia aprovação sem justificativa.
