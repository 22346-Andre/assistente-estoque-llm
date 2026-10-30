"""Acesso ao banco SQLite de demonstração (dados 100% fictícios)."""
import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS empresas (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    api_key TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    nome TEXT NOT NULL,
    estoque_minimo INTEGER NOT NULL,
    venda_media_diaria REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    quantidade INTEGER NOT NULL,
    validade TEXT  -- formato ISO: AAAA-MM-DD
);
CREATE INDEX IF NOT EXISTS idx_produtos_empresa ON produtos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_lotes_produto ON lotes(produto_id);
"""


def db_path() -> Path:
    # Lido a cada chamada para facilitar testes com banco temporário.
    return Path(os.environ.get("DB_PATH", "data/estoque.db"))


def get_conn() -> sqlite3.Connection:
    path = db_path()
    novo = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if novo:
        from app.seed import popular

        popular(conn)
    return conn


def empresa_por_api_key(conn: sqlite3.Connection, api_key: str | None):
    """Descobre a empresa a partir da chave enviada na requisição.

    O empresa_id SEMPRE sai daqui (servidor), nunca do texto da pergunta
    nem de algo que o modelo de IA devolva.
    """
    if not api_key:
        return None
    return conn.execute(
        "SELECT id, nome FROM empresas WHERE api_key = ?", (api_key,)
    ).fetchone()
