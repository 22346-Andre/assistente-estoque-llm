"""Ferramentas (somente leitura) que o LLM pode chamar.

Regras de segurança:
  * O modelo NÃO escreve SQL; só escolhe entre estas funções.
  * O empresa_id é injetado pelo servidor. Se o modelo tentar mandar um
    empresa_id nos argumentos, ele é ignorado.
  * Todas as consultas filtram por empresa_id.
"""
import math
import sqlite3
from datetime import date

from app.db import get_conn
from app.fuzzy import nivel, urgencia


def produtos_estoque_baixo(conn, empresa_id, hoje, **_):
    linhas = conn.execute(
        """
        SELECT p.nome, p.estoque_minimo, COALESCE(SUM(l.quantidade), 0) AS estoque_atual
        FROM produtos p LEFT JOIN lotes l ON l.produto_id = p.id
        WHERE p.empresa_id = ?
        GROUP BY p.id
        HAVING estoque_atual < p.estoque_minimo
        ORDER BY estoque_atual * 1.0 / p.estoque_minimo
        """,
        (empresa_id,),
    ).fetchall()
    return [dict(r) for r in linhas]


def lotes_proximos_vencimento(conn, empresa_id, hoje, dias=7, **_):
    try:
        dias = max(1, min(int(dias), 90))
    except (TypeError, ValueError):
        dias = 7
    limite = date.fromordinal(hoje.toordinal() + dias).isoformat()
    linhas = conn.execute(
        """
        SELECT p.nome AS produto, l.quantidade, l.validade
        FROM lotes l JOIN produtos p ON p.id = l.produto_id
        WHERE p.empresa_id = ? AND l.quantidade > 0
          AND l.validade IS NOT NULL AND l.validade <= ?
        ORDER BY l.validade
        """,
        (empresa_id, limite),
    ).fetchall()  # ordenado por validade = FEFO (primeiro que vence, primeiro que sai)
    resultado = []
    for r in linhas:
        restantes = (date.fromisoformat(r["validade"]) - hoje).days
        resultado.append(
            {
                "produto": r["produto"],
                "quantidade": r["quantidade"],
                "validade": r["validade"],
                "dias_restantes": restantes,
                "situacao": "vencido" if restantes < 0 else "a vencer",
            }
        )
    return resultado


def sugestao_compra(conn, empresa_id, hoje, **_):
    """Sugere reposição para cobrir 14 dias de venda (mínimo: 2x o estoque mínimo)."""
    linhas = conn.execute(
        """
        SELECT p.nome, p.estoque_minimo, p.venda_media_diaria,
               COALESCE(SUM(l.quantidade), 0) AS estoque_atual
        FROM produtos p LEFT JOIN lotes l ON l.produto_id = p.id
        WHERE p.empresa_id = ?
        GROUP BY p.id
        """,
        (empresa_id,),
    ).fetchall()
    sugestoes = []
    for r in linhas:
        venda = r["venda_media_diaria"]
        atual = r["estoque_atual"]
        cobertura = atual / venda if venda > 0 else 999.0
        meta = max(r["estoque_minimo"] * 2, math.ceil(venda * 14))
        quantidade = max(0, meta - atual)
        if quantidade == 0:
            continue
        pontuacao = urgencia(cobertura, venda)
        sugestoes.append(
            {
                "produto": r["nome"],
                "estoque_atual": atual,
                "dias_de_cobertura": round(min(cobertura, 999.0), 1),
                "comprar_quantidade": quantidade,
                "urgencia_pontos": pontuacao,
                "urgencia_nivel": nivel(pontuacao),
            }
        )
    sugestoes.sort(key=lambda s: s["urgencia_pontos"], reverse=True)
    return sugestoes


TOOLS = {
    "produtos_estoque_baixo": produtos_estoque_baixo,
    "lotes_proximos_vencimento": lotes_proximos_vencimento,
    "sugestao_de_compra": sugestao_compra,
}

TOOL_SCHEMAS = [
    {
        "name": "produtos_estoque_baixo",
        "description": "Lista os produtos cujo estoque atual está abaixo do estoque mínimo.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "lotes_proximos_vencimento",
        "description": (
            "Lista lotes que vencem nos próximos N dias (ou já vencidos), "
            "ordenados por validade (FEFO)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dias": {
                    "type": "integer",
                    "description": "Janela em dias a partir de hoje (padrão 7, máximo 90).",
                }
            },
        },
    },
    {
        "name": "sugestao_de_compra",
        "description": (
            "Sugere o que comprar e em que quantidade, ordenado por urgência "
            "calculada com lógica fuzzy (cobertura de estoque x giro de vendas)."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


def executar_ferramenta(nome, args, empresa_id, conn=None, hoje=None):
    """Executa uma ferramenta pedida pelo modelo, sempre com o empresa_id do servidor."""
    funcao = TOOLS.get(nome)
    if funcao is None:
        return {"erro": f"ferramenta desconhecida: {nome}"}
    args = dict(args or {})
    args.pop("empresa_id", None)  # nunca confiar no modelo para isso
    hoje = hoje or date.today()
    fechar = conn is None
    conn = conn or get_conn()
    try:
        return funcao(conn, empresa_id, hoje, **args)
    except sqlite3.Error as e:
        return {"erro": f"falha ao consultar o banco: {e}"}
    finally:
        if fechar:
            conn.close()
