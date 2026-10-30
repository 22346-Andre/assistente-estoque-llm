# Assistente de Estoque com LLM

Um assistente em que o gestor de um pequeno comércio pergunta em português
("o que está para vencer?", "o que devo comprar hoje?") e recebe respostas baseadas nos dados reais do estoque.

O LLM não escreve SQL e não enxerga o banco: ele só escolhe entre **ferramentas de leitura** (tool calling),
e o servidor executa a consulta com segurança.

> Projeto de demonstração com **dados 100% fictícios**, inspirado nos conceitos do EstoqueMax
> (controle de lotes por validade FEFO, sugestão de compra com lógica fuzzy e isolamento de dados por empresa).

## Como funciona

```
Pergunta ──► FastAPI ──► identifica a empresa pela X-API-Key (servidor)
                │
                ▼
          LLM (Ollama ou Anthropic) ──pede──► ferramenta ──► SQLite (filtrado por empresa_id)
                ▲                                   │
                └──────────── resultado ◄───────────┘
                │
                ▼
        Resposta em português
```

Ferramentas disponíveis:

| Ferramenta | O que faz |
|---|---|
| `produtos_estoque_baixo` | Produtos abaixo do estoque mínimo |
| `lotes_proximos_vencimento` | Lotes que vencem nos próximos N dias, em ordem FEFO |
| `sugestao_de_compra` | O que comprar e quanto, ordenado por urgência (lógica fuzzy) |

## Decisões de segurança

- O modelo **não gera SQL**: só chama funções pré-definidas e somente leitura.
- O `empresa_id` vem da chave de API validada no servidor. Se o modelo tentar enviar outro `empresa_id`, ele é ignorado (há testes cobrindo isso).
- Todas as consultas filtram por `empresa_id`.
- A chave da API do LLM fica no `.env`, que não vai para o Git.

## Lógica fuzzy (versão simplificada)

A urgência de compra combina **cobertura de estoque** (dias que o estoque dura) e **giro** (venda média diária)
em 9 regras (3x3), com inferência estilo Sugeno. Veja `app/fuzzy.py`.
Não é o motor do EstoqueMax, é uma versão didática para este projeto.

## Como rodar

Requisitos: Python 3.10+ e **um** destes provedores de LLM:

- **Ollama (gratuito, roda no seu computador):** instale em https://ollama.com e rode `ollama pull qwen2.5:7b`.
- **Anthropic (pago por uso):** chave de API em https://console.anthropic.com, com saldo na conta.

A escolha é feita no `.env` com `LLM_PROVIDER=ollama` ou `LLM_PROVIDER=anthropic`. Modelos locais pequenos erram mais que os modelos grandes de API; se a resposta vier estranha, repita a pergunta ou teste um modelo maior.

```bash
# 1. Ambiente virtual
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash)
# source .venv/bin/activate        # Linux/macOS

# 2. Dependências
pip install -r requirements-dev.txt

# 3. Configuração
cp .env.example .env               # edite o .env: escolha o LLM_PROVIDER (e a chave, se usar Anthropic)

# 4. Subir a API (o banco de demonstração é criado sozinho na primeira execução)
uvicorn app.main:app --reload
```

Teste com duas empresas diferentes:

```bash
curl -X POST http://127.0.0.1:8000/perguntar \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key-bompreco" \
  -d '{"pergunta": "O que devo comprar hoje e por quê?"}'

curl -X POST http://127.0.0.1:8000/perguntar \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key-paoquente" \
  -d '{"pergunta": "Tem algum lote perto de vencer?"}'
```

Documentação interativa: http://127.0.0.1:8000/docs

## Testes

```bash
pytest
```

Os testes **não chamam nenhum LLM real**: o LLM é substituído por um cliente falso, então rodam de graça e offline.
Cobrem as ferramentas, a ordem FEFO, a lógica fuzzy, o laço do assistente e o isolamento entre empresas.

## Estrutura

```
app/
  main.py        API FastAPI (/perguntar, /health)
  assistant.py   laço de tool calling (Ollama ou Anthropic)
  tools.py       ferramentas de leitura + schemas
  fuzzy.py       urgência de compra com lógica fuzzy
  db.py, seed.py banco SQLite e dados fictícios
tests/           testes automatizados
```

## Limitações e próximos passos

- Sem memória de conversa (cada pergunta é independente).
- Banco SQLite de demonstração; em produção usaria PostgreSQL.
- Ideias: histórico de conversa, ferramenta de vendas por período, avaliação das respostas com um conjunto de perguntas de teste.
