# OrcamentoApp - Fluxo comercial ponto a ponto

## Pastas principais

- `dist`: sua versão interna atualizada.
- `trial`: pacote de teste para o cliente, com licença obrigatória de 7 dias.
- `pacotes_clientes`: pacotes gerados pelo Admin de Vendas para cada cliente real.
- `backups`: cópias de segurança de bancos importantes.

## Como entregar trial

Envie `OrcamentoApp_TRIAL.zip` ao cliente.

O cliente deve extrair o ZIP em uma pasta própria e executar `OrcamentoApp.exe`.
Os dados do teste ficam no `budget_app.db` dentro da pasta extraída.
Esta mesma instalação trial pode ser ativada depois com uma licença anual, sem trocar o aplicativo nem perder os dados.

## Como registrar venda e gerar licença anual

Execute `abrir_admin_vendas.bat`.

No painel:

1. Cadastre os dados do cliente.
2. Informe a data de implantação.
3. Para venda anual, use tipo `PAGO` e `365` dias de validade.
4. Baixe o pacote gerado ou envie apenas o novo `license.key` para substituir o trial.
5. O cliente deve fechar o app, substituir `license.key` e abrir novamente.

## Renovação

No Admin de Vendas, use `Renovar 1 ano`.

Isso gera uma nova licença paga por 365 dias com base na data de implantação registrada.

## Sugestões para profissionalizar ainda mais

- Assinatura de contrato simples com cliente, CPF/CNPJ, ambiente instalado e política de backup.
- Backup automático do `budget_app.db` antes de cada atualização.
- Instalador Windows com atalho na área de trabalho.
- Versão do app exibida no rodapé e gravada em log para suporte.
- Exportação de backup/importação restaurável direto pelo painel.
- Termo de uso dentro do pacote trial.

## Licenciamento técnico

A versão cliente/trial usa PySide6 em vez de PyQt6.
Mantenha os avisos de bibliotecas na pasta `licenses` do pacote distribuído.

## Recursos incluidos na versao cliente

- Status de licenca no painel.
- Backup manual do banco local.
- Alertas de contas a vencer e sobra prevista.
- Metas financeiras.
- Importacao opcional de extrato CSV/OFX.
- Relatorio mensal em HTML imprimivel.
- Modo privacidade para ocultar valores na tela.
