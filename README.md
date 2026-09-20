# Frete Estratégico em Dados

Dashboard interativo em Python, com Streamlit, que analisa cotações de frete de lojas virtuais a partir de dados da Sisfrete. O projeto foi desenvolvido pelo Grupo 08 no Hackathon Unimar Tech Summit 2026 e foi o vencedor do evento.

A pergunta que guia a análise é: onde a operação de frete ganha, ou perde, a venda? O dashboard parte da visão da rede em setembro, aproxima uma loja e compara, cotação a cotação, preço, prazo e cobertura de cada transportadora.

## Aviso sobre os dados

Os dados pertencem à Sisfrete e foram cedidos para uso exclusivo no hackathon. Este repositório não contém dados nem credenciais, apenas o código. Para executar a aplicação é necessário ter acesso à API da Sisfrete, com credenciais fornecidas pela organização do evento. O nome e a identidade visual da Sisfrete pertencem à empresa.

## O que o dashboard mostra

1. **A rede em setembro:** volume de cotações por canal de venda, evolução em janelas fixas de 7 dias a partir de 01/09 e as 15 cidades de destino com mais consultas.
2. **Uma loja em detalhe:** a loja é escolhida entre as que têm ao menos 1.000 cotações no mês. O dashboard exibe o total de cotações, o percentual que retornou com opção de frete, os canais, a evolução semanal e as cidades em que a loja pode estar perdendo vendas por ficar sem nenhuma opção de frete.
3. **Transportadoras, preço, prazo e região:** ranking com presença, preço médio, prazo médio e percentual de cotações em que cada transportadora foi a mais barata ou a mais rápida, gráfico de preço por prazo, transportadora vencedora por estado e o custo médio de escolher a opção mais rápida em vez da mais barata.
4. **Conclusões:** resumo em texto gerado a partir dos dados da loja selecionada.

## Decisões técnicas

- **Agregações no servidor:** somas, contagens e rankings são calculados pela própria API sempre que possível.
- **Cruzamento em Python:** o campo com as opções de cada cotação não é do tipo `nested`, então relacionar preço, prazo e região no servidor misturaria opções de cotações diferentes. Por isso, cada cotação é expandida em uma linha por transportadora, e a comparação é feita com pandas.
- **Opção de frete válida:** transportadora informada e valor total maior que zero. O prazo considerado é o máximo (pior caso) e, se estiver zerado, o mínimo.
- **Janelas fixas de 7 dias:** os cortes são feitos de forma explícita a partir de 01/09, porque um histograma de 7 dias no servidor alinharia as janelas à época Unix, e não ao início do mês.
- **Fuso horário:** o horário dos registros está em UTC, e os cortes usam o horário de Brasília (UTC-03:00).
- **Cache e repetição:** as consultas ficam em cache por 10 minutos. Em caso de resposta 429, 502, 503 ou 504, a requisição é repetida até 3 vezes, com espera de 2 e 4 segundos.
- **Compatibilidade de campos:** se a API recusar uma consulta (erro 400), ela é repetida com o sufixo `.keyword` nos campos de texto.
- **Transportadoras:** a base as identifica apenas por código, que aparece como "Transp. código". As com presença muito baixa são ocultadas para evitar conclusões frágeis.
- **Regras do hackathon:** o código consulta apenas os dados de setembro de 2026.

## Tecnologias

- Python
- Streamlit (interface)
- pandas (tratamento e análise dos dados)
- Plotly (gráficos)
- requests (cliente HTTP)
- python-dotenv (leitura das credenciais do arquivo `.env`)

## Estrutura

```
frete-estrategico-dados/
├── .streamlit/
│   └── config.toml
├── .env.example
├── .gitignore
├── app.py
├── dados.py
├── graficos.py
├── requirements.txt
├── tema.py
└── README.md
```

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Interface do dashboard, com as quatro seções |
| `dados.py` | Cliente da API, consultas, cache e funções de análise |
| `graficos.py` | Gráficos Plotly no estilo do dashboard |
| `tema.py` | Estilos, componentes HTML e formatação de números em pt-BR |
| `.streamlit/config.toml` | Tema do Streamlit |

Principais elementos de `dados.py`:

| Elemento | Descrição |
|---|---|
| `ErroAPI` | Exceção com mensagem e código de status HTTP |
| `credenciais_ok()` | Verifica se as credenciais foram configuradas |
| `listar_lojas()` | Lojas com cotações em setembro e o volume de cada uma |
| `resumo_mercado()` | Visão geral da rede: canais, evolução diária e principais cidades |
| `analisar_loja(loja_id, tamanho_amostra)` | Indicadores, cobertura por cidade e cotações recentes de uma loja |
| `analisar_transportadoras(opcoes)` | Ranking, desempenho por estado e comparação entre preço e prazo |
| `agrupar_em_janelas(df_dias)` | Totais diários agrupados em janelas fixas de 7 dias |

## Requisitos

- Python 3.10 ou superior
- Credenciais de acesso à API da Sisfrete

## Como executar

1. Clone o repositório e acesse a pasta:

```bash
git clone https://github.com/samuelr-dev/frete-estrategico-dados.git
cd frete-estrategico-dados
```

2. Crie e ative um ambiente virtual (opcional, mas recomendado):

```bash
python -m venv venv
venv\Scripts\activate
```

No Linux e no macOS, o segundo comando é `source venv/bin/activate`.

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Crie o arquivo `.env` a partir do exemplo:

```bash
copy .env.example .env
```

No Linux e no macOS, use `cp .env.example .env`. Depois, abra o arquivo `.env` e preencha as credenciais:

```
SISFRETE_USUARIO=seu_usuario
SISFRETE_SENHA=sua_senha
```

5. Inicie o dashboard:

```bash
streamlit run app.py
```

A aplicação abre em `http://localhost:8501`.

## Configuração das credenciais

As credenciais são lidas do arquivo `.env`, que está no `.gitignore` e não deve ser enviado ao repositório. Nunca escreva usuário ou senha diretamente no código. Também não versione arquivos com dados exportados: os formatos mais comuns (`.csv`, `.xlsx` e `.parquet`) já estão ignorados.

## Solução de problemas

| Mensagem | O que fazer |
|---|---|
| Credenciais não encontradas | Crie o arquivo `.env` com `SISFRETE_USUARIO` e `SISFRETE_SENHA` |
| Usuário ou senha incorretos (401) | Confira as credenciais no `.env` |
| Acesso negado pela API (403) | A consulta está fora do permitido para a credencial |
| Índice não encontrado (404) | Verifique se existem dados de setembro de 2026 para a credencial |
| A API está sob carga (429) | Aguarde alguns segundos e recarregue a página |
| Nenhuma cotação de setembro de 2026 encontrada | A credencial não tem dados no período consultado |

## Integrantes

Grupo 08 do Hackathon Unimar Tech Summit 2026.

<!-- Adicione aqui os integrantes do grupo -->
- Samuel Rodrigues
- João Pedro D Oliveira
- Samuel Souza
- Miguel Delasare
- Luis Felipe Petkevicius

## Observações

Este repositório reúne o código final do projeto. O histórico de desenvolvimento do grupo durante o hackathon não está incluído.
