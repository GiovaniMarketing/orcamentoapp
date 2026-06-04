# App Orcamento Familiar - Fluxo comercial ponto a ponto

## Pastas principais

- `base_cliente`: base interna reutilizavel para montar entregas. Nao enviar diretamente.
- `E:\App Orcamento Familiar Comercial\pacotes_temporarios`: pastas e ZIPs exclusivos gerados temporariamente para cada cliente.
- `backups`: copias de seguranca de bancos importantes.

## Preparar a base cliente

Depois de gerar o executavel cliente, execute:

`venv_app\Scripts\python.exe criar_pasta_trial.py --somente-base`

Isso cria `base_cliente`, usada internamente pelo Admin de Vendas.

## Trial por 7 dias

1. Execute `abrir_admin_vendas.bat`.
2. Cadastre o cliente com tipo `TRIAL`.
3. O painel gera uma pasta exclusiva, como `0001_joao_simone_trial`, e o ZIP correspondente.
4. Envie o ZIP ao cliente.

Os dados do teste ficam em `budget_app.db` dentro da pasta extraida pelo cliente.

Depois de enviar o ZIP, use `Excluir apos envio`. O cadastro e a licenca continuam no banco administrativo.
Se precisar reenviar, use `Gerar novamente`.

## Venda direta

1. Informe o PIX ao cliente.
2. Confira o recebimento no extrato do Mercado Pago.
3. No painel, cadastre o cliente com tipo `PAGO`.
4. Escolha `Instalacao completa`.
5. O cadastro fica com status `AGUARDANDO_PIX`.
6. Clique em `Confirmar PIX e gerar licenca` somente depois de conferir o pagamento.
7. Envie o ZIP da pasta exclusiva, como `0002_joao_simone_vendido`.
8. Depois do envio, use `Excluir apos envio` para liberar espaco.

## Ativacao de cliente que ja usou o trial

1. Confira o PIX no extrato do Mercado Pago.
2. Cadastre uma venda `PAGO`.
3. Escolha `Cliente ja possui trial: somente licenca`.
4. Clique em `Confirmar PIX e gerar licenca`.
5. Envie o ZIP da pasta exclusiva, como `0003_joao_simone_ativacao`.

Essa pasta contem somente `license.key` e instrucoes. O cliente deve:

1. Fechar o aplicativo.
2. Fazer backup de `budget_app.db`.
3. Substituir somente `license.key`.
4. Abrir novamente o aplicativo.

Os dados cadastrados durante o trial permanecem preservados.

## Espaco em disco

Os pacotes ficam fora do projeto em:

`E:\App Orcamento Familiar Comercial\pacotes_temporarios`

Pacotes completos ocupam aproximadamente 210 MB antes de compactar e devem ser apagados depois do envio.
O painel mostra o espaco ocupado e oferece:

- `Excluir apos envio`
- `Gerar novamente`
- `Excluir pacotes com mais de 15 dias`

Ao abrir o Admin de Vendas, pacotes temporarios com mais de 15 dias tambem sao removidos automaticamente.

Para encerrar o servidor administrativo em segundo plano, use `Finalizar painel` no topo da tela.

## Renovacao anual

Depois de conferir o PIX de renovacao, localize o cliente ativo e clique em `Confirmar PIX e renovar 1 ano`.
O painel gera uma nova licenca anual.

## Cuidados comerciais

- Nunca liberar licenca paga somente com base em comprovante enviado pelo cliente.
- Confirmar o recebimento diretamente no extrato do Mercado Pago.
- Registrar a confirmacao do PIX nas observacoes comerciais.
- Manter backup do banco administrativo `admin_vendas.db`.

## Licenciamento tecnico

A versao cliente usa PySide6 em vez de PyQt6.
Mantenha os avisos de bibliotecas na pasta `licenses` do pacote distribuido.

## Recursos incluidos

- Status de licenca no painel.
- Backup manual do banco local.
- Alertas de contas a vencer e sobra prevista.
- Metas financeiras.
- Importacao opcional de extrato CSV/OFX.
- Relatorios mensal, semestral e anual em HTML imprimivel.
- Modo privacidade para ocultar valores na tela.
- Guia de uso completo no arquivo `GUIA_DO_CLIENTE.html` e no botao `Guia de Uso` do painel.
- Aviso para o cliente manter aberta a janela preta do sistema, quando ela aparecer junto com o aplicativo.
