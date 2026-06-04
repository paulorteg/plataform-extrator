# PRD 01: Visão Geral da Plataforma

## Objetivo

Criar uma plataforma empresarial capaz de receber BOs e documentos relacionados, extrair informações relevantes, normalizar os dados em um Modelo Canônico, aplicar o Mapping MercadoIA, permitir revisão humana e gerar template padronizado.

## Usuários

1. Analista de sinistro
2. Gestor operacional
3. Administrador da empresa
4. Auditor
5. Administrador global da plataforma

## Fluxo principal

1. Usuário autentica.
2. Usuário envia documento.
3. Sistema valida arquivo e saldo.
4. Sistema armazena arquivo em storage privado.
5. Worker processa o documento.
6. Sistema extrai texto ou OCR.
7. Sistema classifica família documental.
8. Sistema segmenta ocorrências.
9. Sistema extrai campos determinísticos.
10. Sistema usa LLM apenas quando necessário.
11. Sistema cria evidências.
12. Sistema valida dados.
13. Sistema aplica Modelo Canônico e Mapping.
14. Usuário revisa pendências.
15. Usuário aprova ocorrência.
16. Sistema gera template final.

## Requisitos de produto

1. Suportar PDF digital, PDF escaneado, PNG, JPG, JPEG e DOCX.
2. Suportar BOs de diferentes estados e polícias.
3. Suportar DOCX com múltiplos BOs.
4. Ter login e senha.
5. Ter painel admin com usuários, licenças, planos e pacotes.
6. Controlar consumo por ocorrência extraída.
7. Ter evidência por campo.
8. Ter revisão humana.
9. Ter LGPD, auditoria, mascaramento e storage privado.
10. Reduzir custo com LLM usando extração determinística primeiro.

## Critérios de aceite

1. Upload de documento funciona.
2. Pipeline cria ocorrências revisáveis.
3. Campos obrigatórios aparecem em checklist.
4. Dados sensíveis são protegidos.
5. Aprovação só ocorre quando regras são atendidas.
6. Template só é gerado após aprovação.
