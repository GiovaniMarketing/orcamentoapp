# Tutorial - Venda do App Orçamento Familiar pela Kiwify

## 1. Entendimento correto do fluxo

A Kiwify processa pagamentos de produtos digitais. O cliente paga por Pix, cartão ou boleto, e a venda recebe um status dentro da plataforma.

Para o App Orçamento Familiar, a entrega deve acontecer quando a compra estiver aprovada, porque o cliente espera acessar o produto logo após pagar.

O prazo de liberação do saldo para você sacar não deve ser usado como prazo de entrega ao cliente. Esse prazo é financeiro, entre Kiwify e produtor.

## 2. O que vender na Kiwify

Produto principal:

**App Orçamento Familiar - Licença Anual**

Descrição curta:

Aplicativo local para controle financeiro familiar, com receitas, despesas, metas, investimentos, relatórios, backup e licença de uso anual.

Modelo de pagamento recomendado no início:

- Pagamento único.
- Licença válida por 1 ano.
- Renovação vendida como nova compra ou link específico de renovação.
- Não oferecer trial pela Kiwify.

Neste canal, a Kiwify deve vender somente o plano anual. O trial fica fora do fluxo principal de venda.

## 3. Formato de entrega recomendado

### Fase 1 - Manual assistida

Use este modelo para começar com segurança:

1. Cliente compra pela Kiwify.
2. Kiwify aprova o pagamento.
3. Você recebe a notificação da venda.
4. Você entra no Admin de Vendas do Orçamento Familiar.
5. Cadastra o cliente.
6. Gera a licença anual individual.
7. Envia para o cliente por e-mail, WhatsApp ou área de entrega definida.

Vantagem:

- Menos risco técnico no começo.
- Você valida o processo comercial antes de automatizar.

Desvantagem:

- Não é entrega totalmente imediata.

Texto sugerido para a página de obrigado:

Obrigado pela compra. Seu pagamento foi aprovado e sua licença será preparada. Você receberá as instruções de instalação pelo e-mail/WhatsApp informado na compra.

### Fase 2 - Automática

Use este modelo quando quiser entrega imediata:

1. Cliente compra pela Kiwify.
2. Evento de compra aprovada dispara um webhook.
3. Um serviço online recebe o webhook.
4. Esse serviço gera ou solicita a licença.
5. O cliente recebe a licença e instruções automaticamente.

Importante:

O painel admin atual roda localmente no seu computador. Para automação por webhook, será necessário criar um pequeno serviço online seguro, porque a Kiwify precisa chamar uma URL pública.

## 4. O que configurar na Kiwify

### Cadastro do produto

1. Acesse sua conta Kiwify.
2. Vá em Produtos.
3. Clique em Criar produto.
4. Escolha pagamento único.
5. Escolha o formato de entrega mais adequado:
   - Área de membros da Kiwify, se a Kiwify for entregar o instalador ou um arquivo com link de download.
   - Área de membros externa, se for usar automação por webhook.
   - Quero apenas aceitar pagamentos, se a entrega será totalmente manual assistida.
6. Preencha nome, preço, descrição e página/site obrigatório.
7. Personalize o checkout.
8. Copie o link de checkout na aba Links.

### Dados importantes do produto

Nome:

App Orçamento Familiar - Licença Anual

Preço:

Definir conforme sua estratégia comercial.

Suporte:

WhatsApp: (12) 98161-2085

Entrega:

Instalador/base do app e instruções de instalação. A licença anual deve ser individual por cliente.

Garantia/reembolso:

Definir conforme sua política comercial e regras da plataforma.

## 5. Imagens recomendadas para a Kiwify

Use uma identidade visual simples e confiável.

Imagem principal:

- Formato quadrado.
- Nome: App Orçamento Familiar.
- Subtítulo: Organize sua vida financeira em casa.
- Elementos: família, notebook, gráfico financeiro ou painel do app.

Imagens complementares:

- Print do resumo financeiro.
- Print das receitas e despesas.
- Print do guia de uso.
- Mockup com notebook mostrando o app.

Evite:

- Imagem poluída.
- Texto pequeno demais.
- Promessas exageradas de enriquecimento.
- Aparência de golpe financeiro.

## 6. Entrega manual pelo Admin de Vendas

### Venda anual pela Kiwify

1. Confirme a venda aprovada na Kiwify.
2. Abra o Admin de Vendas.
3. Cadastre o cliente como PAGO.
4. Se a Kiwify já entregou o instalador/base, escolha Somente licença: cliente já possui instalação/base.
5. Gere a licença anual.
6. Envie somente o `license.key` ou o ZIP de ativação.

Se você preferir que a Kiwify não entregue o instalador, gere a instalação completa pelo Admin de Vendas e envie o ZIP ao cliente. Essa alternativa dá mais controle, mas não é tão imediata.

## 7. Como fazer a Kiwify entregar o instalador

Pelo suporte da Kiwify, anexos na área de membros têm limite de até 10 arquivos, com até 100 MB cada.

Por isso, existem dois caminhos:

### Caminho A - Instalar direto pela Kiwify

Use este caminho somente se o ZIP final couber no limite da Kiwify.

1. Cadastre o produto como Área de membros da Kiwify.
2. Crie um módulo chamado Download do App.
3. Crie um conteúdo chamado Instalador App Orçamento Familiar.
4. Em Anexos, envie o ZIP do instalador/base.
5. Na descrição, explique que a licença anual será enviada individualmente.

### Caminho B - Kiwify entrega um arquivo com link externo

Use este caminho se o ZIP do app passar de 100 MB.

1. Hospede o instalador/base em local externo seguro.
2. Crie um arquivo pequeno chamado `LEIA-ME_DOWNLOAD_APP_ORCAMENTO.pdf` ou `.html`.
3. Coloque nesse arquivo:
   - link de download do instalador;
   - instruções de instalação;
   - aviso da janela preta do sistema;
   - informação de que a licença é individual.
4. Anexe esse arquivo pequeno na área de membros da Kiwify.

Esse é o caminho mais provável para o App Orçamento Familiar, porque o pacote do executável tende a ser grande.

## 8. Entrega automática por webhook

Para automatizar, será necessário criar um serviço intermediário.

Esse serviço deve:

- Receber webhook de compra aprovada.
- Validar se o evento veio da Kiwify.
- Gravar a venda em uma base online ou acionar seu painel.
- Gerar uma licença anual.
- Enviar e-mail ou WhatsApp ao cliente.
- Registrar tudo para auditoria.

Cuidados importantes:

- Evitar gerar licença duplicada para o mesmo pedido.
- Guardar o ID da venda da Kiwify.
- Validar reembolso/cancelamento, se desejar bloquear renovação futura.
- Não depender do seu computador pessoal ligado para entrega automática.

## 9. Política de entrega recomendada

Texto para checkout ou página de obrigado:

Após a confirmação do pagamento, você terá acesso ao instalador/base do App Orçamento Familiar pela área de membros da Kiwify ou pelo link de download informado. A licença anual é individual e será enviada conforme o processo de ativação informado na compra.

## 10. Checklist antes de vender

- Produto cadastrado na Kiwify.
- Link de checkout testado.
- Preço definido.
- Página de vendas ou perfil informado.
- Imagem principal criada.
- Texto de descrição revisado.
- Política de suporte definida.
- Admin de Vendas funcionando.
- Base cliente atualizada.
- Guia do cliente incluído no pacote.
- Instalação/base sem licença paga genérica.
- Processo de geração de licença anual individual testado.
- Processo de envio testado com uma venda simulada.

## 11. Recomendação prática

Comece vendendo o plano anual pela Kiwify, sem trial.

A Kiwify pode entregar o instalador/base. O seu painel admin continua responsável pela licença individual.

Depois que houver volume, automatize a geração da licença com webhook.

O ideal final é:

Compra aprovada na Kiwify -> cliente baixa o instalador/base -> licença individual gerada automaticamente -> cliente ativa o app.
