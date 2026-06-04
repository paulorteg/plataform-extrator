# PRD 12: LGPD, Segurança e Auditoria

## Objetivo

Garantir proteção de dados pessoais, documentos oficiais, narrativas e informações sensíveis.

## Controles

1. Login obrigatório
2. Autorização por papel e permissão
3. Isolamento por organização
4. Dados sensíveis mascarados
5. Storage privado
6. URLs temporárias
7. Audit Log separado
8. Logs técnicos minimizados
9. Retenção configurável
10. Dados reais apenas anonimizados em testes

## Dados sensíveis

CPF, CNPJ, RG, CNH, telefone, email, endereço, filiação, nome de envolvidos, narrativa, documento original e template gerado.

## Audit Log obrigatório

Login, falha de login, upload, download, visualização sensível, edição, aprovação, geração de template, alteração de usuário, alteração de plano e exportação de auditoria.

## Critérios de aceite

1. Acesso cruzado bloqueado.
2. Dados sensíveis mascarados.
3. Downloads auditados.
4. Logs sem dados sensíveis completos.
5. Admin global não acessa BOs sensíveis por padrão.
