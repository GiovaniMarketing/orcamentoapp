# Modelo Kiwify sem trial

Este é o modelo recomendado para vender pela Kiwify.

## Produto

App Orçamento Familiar - Licença Anual

## O que a Kiwify entrega

A Kiwify deve entregar apenas:

- instalador/base do aplicativo; ou
- arquivo pequeno com link para download do instalador/base.

## O que a Kiwify não deve entregar

- licença paga genérica;
- trial;
- `license.key` anual compartilhado;
- banco de dados com informações de outro cliente.

## O que você entrega individualmente

Após compra aprovada, você gera no Admin de Vendas:

- `license.key` anual individual; ou
- ZIP de ativação contendo a licença individual e instruções.

## Fluxo recomendado

1. Cliente compra o plano anual pela Kiwify.
2. Cliente baixa o instalador/base pela área de membros da Kiwify.
3. Você confirma a compra aprovada.
4. Você gera a licença anual individual.
5. Cliente recebe a licença e ativa o app.

## Automação futura

Quando quiser automatizar:

Compra aprovada na Kiwify -> webhook -> geração automática de `license.key` -> envio automático ao cliente.
