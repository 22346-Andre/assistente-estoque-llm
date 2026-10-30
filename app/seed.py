"""Dados fictícios para demonstração. Nenhum dado real de cliente."""
import sqlite3
from datetime import date, timedelta

from app.db import SCHEMA

EMPRESAS = [
    (1, "Mercadinho Bom Preço", "demo-key-bompreco"),
    (2, "Padaria Pão Quente", "demo-key-paoquente"),
]

# (empresa_id, nome, estoque_minimo, venda_media_diaria, [(quantidade, dias_ate_vencer)])
PRODUTOS = [
    (1, "Leite integral 1L", 40, 12, [(15, 3), (10, 20)]),
    (1, "Arroz 5kg", 20, 4, [(60, 300)]),
    (1, "Feijão carioca 1kg", 30, 6, [(18, 150)]),
    (1, "Iogurte natural", 25, 5, [(20, 5), (8, 12)]),
    (1, "Pão de forma", 15, 3, [(6, 2)]),
    (1, "Refrigerante 2L", 36, 9, [(120, 180)]),
    (1, "Detergente", 20, 2, [(4, 400)]),
    (1, "Queijo mussarela fatiado 200g", 10, 1.5, [(12, 9)]),
    (1, "Óleo de soja 900ml", 24, 5, [(0, 500)]),
    (2, "Farinha de trigo 5kg", 10, 2, [(30, 200)]),
    (2, "Fermento biológico", 12, 3, [(5, 6)]),
    (2, "Manteiga 500g", 8, 1.5, [(6, 4)]),
    (2, "Leite integral 1L", 20, 6, [(40, 10)]),
]


def popular(conn: sqlite3.Connection, hoje: date | None = None) -> None:
    hoje = hoje or date.today()
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT INTO empresas (id, nome, api_key) VALUES (?, ?, ?)", EMPRESAS
    )
    for empresa_id, nome, minimo, venda, lotes in PRODUTOS:
        cur = conn.execute(
            "INSERT INTO produtos (empresa_id, nome, estoque_minimo, venda_media_diaria)"
            " VALUES (?, ?, ?, ?)",
            (empresa_id, nome, minimo, venda),
        )
        for qtd, dias in lotes:
            validade = (hoje + timedelta(days=dias)).isoformat()
            conn.execute(
                "INSERT INTO lotes (produto_id, quantidade, validade) VALUES (?, ?, ?)",
                (cur.lastrowid, qtd, validade),
            )
    conn.commit()
