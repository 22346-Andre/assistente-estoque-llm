"""Testa o provedor Ollama com um cliente HTTP falso (sem precisar do Ollama)."""
import json

import pytest

from app.assistant import _schemas_ollama, responder


class RespostaFalsa:
    def __init__(self, corpo):
        self._corpo = corpo

    def raise_for_status(self):
        pass

    def json(self):
        return self._corpo


class HttpFalso:
    def __init__(self, mensagens):
        self._mensagens = iter(mensagens)
        self.chamadas = []

    def post(self, url, json=None, timeout=None):
        # copia para guardar o estado de cada chamada
        self.chamadas.append({"url": url, "json": dict(json), "n": len(json["messages"])})
        return RespostaFalsa({"message": next(self._mensagens)})


def test_formato_das_ferramentas_para_ollama():
    for t in _schemas_ollama():
        assert t["type"] == "function"
        assert {"name", "description", "parameters"} <= set(t["function"])


def test_laco_ollama_com_ferramenta_e_isolamento(conn):
    http = HttpFalso(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "produtos_estoque_baixo", "arguments": {"empresa_id": 2}}}
                ],
            },
            {"role": "assistant", "content": "Leite e pão estão abaixo do mínimo."},
        ]
    )
    resposta = responder("O que está acabando?", 1, client=http, provedor="ollama")
    assert "leite" in resposta.lower()
    assert http.chamadas[0]["url"].endswith("/api/chat")
    assert http.chamadas[0]["json"]["stream"] is False
    assert http.chamadas[1]["n"] == 4  # system, user, assistant(tool_calls), tool

    # o resultado da ferramenta devolvido ao modelo só tem dados da empresa 1
    msg_tool = http.chamadas[1]["json"]["messages"][-1]
    assert msg_tool["role"] == "tool"
    nomes = {d["nome"] for d in json.loads(msg_tool["content"])}
    assert "Pão de forma" in nomes
    assert "Fermento biológico" not in nomes


def test_argumentos_em_texto_json(conn):
    http = HttpFalso(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "lotes_proximos_vencimento", "arguments": json.dumps({"dias": 7})}}
                ],
            },
            {"role": "assistant", "content": "ok"},
        ]
    )
    assert responder("vence o quê?", 1, client=http, provedor="ollama") == "ok"


def test_provedor_invalido():
    with pytest.raises(ValueError):
        responder("oi", 1, provedor="xyz")
