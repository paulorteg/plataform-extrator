# PRD 06.1: Auth, Admin, Planos e Consumo

## Objetivo

Definir autenticação, administração de usuários, controle de licenças, planos, pacotes e consumo.

## Autenticação

Login por email e senha, hash seguro, recuperação de senha, convite de usuários, bloqueio de usuários e sessão expirada.

## Admin

Painel para gerenciar organizações, usuários, papéis, planos, pacotes, assinatura e consumo.

## Consumo

Unidade comercial: uma ocorrência extraída com sucesso equivale a uma análise consumida.

## Regras

1. Retry não duplica consumo.
2. Falha técnica sem ocorrência não consome.
3. Documento com múltiplos BOs consome por ocorrência.
4. Organização sem saldo bloqueia processamento, salvo excedente permitido.

## Critérios de aceite

1. Login funciona.
2. Usuários podem ser convidados.
3. Papéis controlam permissões.
4. Saldo é calculado.
5. Consumo é idempotente.
