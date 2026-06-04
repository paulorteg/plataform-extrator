# extraction_pipeline.md

## Fluxo

Upload, validação, storage privado, job, análise do arquivo, extração de texto ou OCR, normalização, classificação documental, segmentação, detecção de seções, extração determinística, extração semântica seletiva, evidências, validação, Modelo Canônico, Mapping MercadoIA, consumo, lista, revisão, aprovação e template.

## Princípios

1. Assíncrono.
2. Idempotente.
3. LLM seletivo.
4. OCR apenas quando necessário.
5. Evidência obrigatória.
6. Campo ausente vira pendência.
7. Segurança em todas as etapas.

## Jobs

analyze_file, extract_text, render_pdf_pages, run_ocr, classify_document, segment_occurrences, extract_fields, validate_fields, build_canonical_model, apply_mapping, register_usage e generate_template.

## Consumo

Uma ocorrência extraída com sucesso consome uma análise. Retry não duplica consumo.
