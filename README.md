# App Orcamento Familiar

Aplicativo local para controle financeiro familiar, com receitas, despesas, investimentos simples, relatorio de imposto de renda e licenciamento para trial/pago.

## Recursos do app

- Controle de receitas, despesas, recorrências e status pago/a vencer.
- Painel com alertas do mes, contas vencendo, sobra prevista e maior categoria de gasto.
- Metas financeiras com progresso.
- Importação opcional de extratos `.csv` e `.ofx`.
- Backup local do banco `budget_app.db`.
- Relatórios mensal, semestral e anual em HTML imprimível/salvável em PDF.
- Exportação anual para apoio na declaração de imposto de renda.
- Modo privacidade para ocultar valores na tela.
- Status de licença visível no painel.
- Guia de uso completo acessível dentro do painel e incluído nos pacotes comerciais.
- Aviso no topo do painel para manter aberta a janela preta do sistema, quando ela aparecer.

## Estrutura principal

- `main_cliente.py`: versao cliente licenciada com PySide6.
- `main_personal.py`: versao interna/pessoal.
- `admin_vendas.py`: painel local para controle de clientes, vendas, vencimentos e renovacoes.
- `licenciamento.py`: geracao e validacao de licencas.
- `criar_pasta_trial.py`: prepara a base reutilizavel do aplicativo cliente.
- `base_cliente`: base local ignorada pelo Git, usada para gerar entregas exclusivas.
- `E:\App Orcamento Familiar Comercial\pacotes_temporarios`: armazenamento externo temporario dos pacotes gerados.
- `templates/` e `static/`: painel web local carregado pelo app desktop.

## Arquivos gerados

Executaveis, bancos, zips, backups, builds e ambiente virtual nao entram no Git. Gere localmente quando necessario.

## Trial e venda

O cliente usa o mesmo aplicativo no trial e na versao paga. A ativacao anual acontece substituindo o arquivo `license.key`, preservando o banco `budget_app.db`.

O Admin de Vendas gera pastas exclusivas com ID e nome do cliente:

- `0001_joao_simone_trial`: aplicativo completo com licenca de avaliacao por 7 dias.
- `0002_joao_simone_vendido`: aplicativo completo para venda direta.
- `0003_joao_simone_ativacao`: somente `license.key` para ativar trial ou renovar.

Vendas pagas ficam com status `AGUARDANDO_PIX`. A licenca anual so e gerada depois da confirmacao manual do pagamento no extrato.

Depois de enviar um pacote, use `Excluir apos envio` no Admin de Vendas. O painel preserva a licenca no banco e permite `Gerar novamente` quando necessario. Pacotes temporarios com mais de 15 dias sao removidos automaticamente.

Para encerrar o servidor administrativo, use `Finalizar painel` no topo da tela.
