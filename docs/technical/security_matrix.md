# security_matrix.md

## Classificação

1. Operacional interno
2. Operacional restrito
3. Pessoal
4. Altamente restrito
5. Segredo

## Máscaras

CPF: `000*****00`.
CNPJ: `00.***.***/****00`.
Telefone: DDD e últimos dígitos.
Email: parcial.
Endereço: cidade e UF.
Narrativa: não exibir em lista.
Documento original: acessar apenas com permissão.

## Storage

Storage privado, URL temporária, separação por ambiente e organização, criptografia em repouso, audit log em download e retenção configurável.

## Logs

Logs técnicos não podem conter dados sensíveis completos, narrativa, OCR integral, tokens, senhas ou URLs temporárias.

## LLM

Usar mínimo contexto, schema obrigatório, evidência obrigatória, rejeição sem evidência e registro de custo.
