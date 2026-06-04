# PRD 04: Motor de Extração

## Objetivo

Extrair informações de documentos heterogêneos com alto nível de precisão e baixo custo.

## Estratégia

1. Análise técnica do arquivo.
2. Extração de texto digital quando possível.
3. OCR apenas quando necessário.
4. Classificação documental por sinais.
5. Segmentação de ocorrências.
6. Extração determinística de campos formais.
7. Uso seletivo de LLM para campos semânticos.
8. Validação formal.
9. Evidência por campo.

## Campos determinísticos

CPF, CNPJ, placa, data, hora, CEP, RENAVAM, chassi, valores monetários e número do BO.

## Campos semânticos

Tipo de sinistro, mercadoria em narrativa, seleção do motorista, seleção do veículo sinistrado, embarcador em narrativa, objeto material e resumo operacional.

## Critérios de aceite

1. PDF digital processado.
2. PDF escaneado processado com OCR.
3. Imagens processadas com OCR.
4. DOCX com múltiplos BOs segmentado.
5. Campos automáticos com evidência.
6. Campo ausente vira pendência.
