# App Orcamento Familiar - Fluxo comercial anual

## Modelo atual

O foco comercial atual e vender somente a licenca anual do App Orcamento Familiar.

- Produto: App Orcamento Familiar - Licenca Anual.
- Validade: 12 meses a partir da implantacao ou renovacao.
- Entrega: instalacao completa ou somente `license.key` quando o cliente ja recebeu a base.
- Trial: fora do fluxo principal de venda.

## Pastas principais

- `base_cliente`: base interna reutilizavel para montar entregas. Nao enviar diretamente.
- `E:\App Orcamento Familiar Comercial\pacotes_temporarios`: pastas e ZIPs exclusivos gerados temporariamente para cada cliente.
- `backups`: copias de seguranca de bancos importantes.

## Preparar a base cliente

Depois de gerar o executavel cliente, execute:

`venv_app\Scripts\python.exe criar_pasta_trial.py --somente-base`

Esse comando prepara `base_cliente`, usada internamente pelo Admin de Vendas.

## Venda anual direta

1. Informe o meio de pagamento ao cliente.
2. Confira o recebimento no extrato.
3. Abra `abrir_admin_vendas.bat`.
4. Cadastre a venda anual.
5. Escolha `Instalacao completa`.
6. Clique em `Confirmar pagamento e gerar licenca anual`.
7. Envie o ZIP exclusivo do cliente.
8. Depois do envio, use `Excluir apos envio` para liberar espaco.

## Venda anual pela Kiwify

1. A Kiwify entrega o instalador/base ou um arquivo com link de download.
2. Confirme se a venda esta aprovada na Kiwify.
3. Abra o Admin de Vendas.
4. Cadastre a venda anual.
5. Escolha `Somente licenca: cliente ja possui instalacao/base`.
6. Clique em `Confirmar pagamento e gerar licenca anual`.
7. Envie o ZIP de licenca ao cliente.

## Renovacao anual

Depois de conferir o pagamento da renovacao, localize o cliente ativo e clique em `Confirmar pagamento e renovar 1 ano`.

O painel gera uma nova licenca anual e cria um pacote somente com a licenca.

## Espaco em disco

Os pacotes ficam fora do projeto em:

`E:\App Orcamento Familiar Comercial\pacotes_temporarios`

Pacotes completos ocupam aproximadamente 210 MB antes de compactar e devem ser apagados depois do envio.

O painel oferece:

- `Excluir apos envio`
- `Gerar novamente`
- `Excluir pacotes com mais de 15 dias`

Ao abrir o Admin de Vendas, pacotes temporarios com mais de 15 dias tambem sao removidos automaticamente.

## Cuidados comerciais

- Nunca liberar licenca paga somente com base em comprovante enviado pelo cliente.
- Confirmar o recebimento diretamente no extrato ou na plataforma.
- Registrar informacoes importantes nas observacoes comerciais.
- Manter backup do banco administrativo `admin_vendas.db`.
- Nao enviar `license.key` generico.

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
