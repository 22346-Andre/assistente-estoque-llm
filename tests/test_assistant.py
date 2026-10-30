"""Testa o laço do assistente SEM chamar a API real (cliente falso)."""
import json
from types import SimpleNamespace

from app.assistant import responder


class ClienteFalso:
    def __init__(self, respostas):
        self.messages = self
        self._respostas = iter(respostas)
        self.chamadas = []

    def create(self, **kwargs):
        self.chamadas.append(kwargs)
        return next(self._respostas)


def _usa_ferramenta(nome, entrada):
    bloco = SimpleNamespace(type="tool_use", id="t1", name=nome, input=entrada)
    return SimpleNamespace(stop_reason="tool_use", content=[bloco])


def _texto(t):
    return SimpleNamespace(
        stop_reason="end_turn", content=[SimpleNamespace(type="text", text=t)]
    )


def test_laco_com_ferramenta_e_isolamento(conn):
    # O "modelo" tenta espionar a empresa 2, mas quem pergunta é a empresa 1.
    cliente = ClienteFalso(
        [
            _usa_ferramenta("produtos_estoque_baixo", {"empresa_id": 2}),
            _texto("Você está com o leite e o pão abaixo do mínimo."),
        ]
    )
    resposta = responder(
        "O que está acabando?", empresa_id=1, client=cliente, provedor="anthropic"
    )
    assert "leite" in resposta.lower()

    ultima = cliente.chamadas[-1]["messages"][-1]["content"][0]
    assert ultima["type"] == "tool_result"
    dados = json.loads(ultima["content"])
    nomes = {d["nome"] for d in dados}
    assert "Pão de forma" in nomes
    assert "Fermento biológico" not in nomes  # dado da empresa 2 não vaza


def test_resposta_direta_sem_ferramenta():
    cliente = ClienteFalso([_texto("Só consigo ajudar com estoque.")])
    assert "estoque" in responder("Qual a capital da França?", 1, client=cliente, provedor="anthropic")
