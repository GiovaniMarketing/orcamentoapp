# App Orcamento Familiar

Aplicativo local para controle financeiro familiar, com receitas, despesas, investimentos simples, relatorio de imposto de renda e licenciamento para trial/pago.

## Recursos do app

- Controle de receitas, despesas, recorrencias e status pago/a vencer.
- Painel com alertas do mes, contas vencendo, sobra prevista e maior categoria de gasto.
- Metas financeiras com progresso.
- Importacao opcional de extratos `.csv` e `.ofx`.
- Backup local do banco `budget_app.db`.
- Relatorio mensal em HTML imprimivel/salvavel em PDF pelo navegador.
- Exportacao anual para apoio na declaracao de imposto de renda.
- Modo privacidade para ocultar valores na tela.
- Status de licenca visivel no painel.

## Estrutura principal

- `main_cliente.py`: versao cliente licenciada com PySide6.
- `main_personal.py`: versao interna/pessoal.
- `admin_vendas.py`: painel local para controle de clientes, vendas, vencimentos e renovacoes.
- `licenciamento.py`: geracao e validacao de licencas.
- `criar_pasta_trial.py`: gera a pasta e o ZIP trial.
- `templates/` e `static/`: painel web local carregado pelo app desktop.

## Arquivos gerados

Executaveis, bancos, zips, backups, builds e ambiente virtual nao entram no Git. Gere localmente quando necessario.

## Trial e venda

O cliente usa o mesmo aplicativo no trial e na versao paga. A ativacao anual acontece substituindo o arquivo `license.key`, preservando o banco `budget_app.db`.
