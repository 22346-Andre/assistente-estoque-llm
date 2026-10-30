"""Laço de conversa com o LLM usando tool calling.

Provedores suportados (variável LLM_PROVIDER):
  * "anthropic": API da Anthropic (pago por uso)
  * "ollama":    modelo local via Ollama (gratuito, roda no seu computador)
"""
import json
import os

from app.tools import TOOL_SCHEMAS, executar_ferramenta

SYSTEM = (
    "Você é um assistente de gestão de estoque para pequenos comércios. "
    "Responda sempre em português do Brasil, de forma curta e objetiva. "
    "Use SOMENTE as ferramentas disponíveis para obter dados; nunca invente "
    "produtos, quantidades ou datas. Se a pergunta não for sobre o estoque, "
    "diga educadamente que só consegue ajudar com estoque. "
    "Ao sugerir compras, explique em uma frase por que o item é urgente."
)

MSG_SEM_CONCLUSAO = "Não consegui concluir a consulta. Tente reformular a pergunta."


def _provedor() -> str:
    return os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()


def responder(
    pergunta: str,
    empresa_id: int,
    client=None,
    max_rodadas: int = 5,
    provedor: str | None = None,
) -> str:
    """Responde à pergunta usando o provedor configurado.

    `client` permite injetar um cliente falso nos testes.
    """
    provedor = (provedor or _provedor()).lower()
    if provedor == "ollama":
        return _responder_ollama(pergunta, empresa_id, client, max_rodadas)
    if provedor == "anthropic":
        return _responder_anthropic(pergunta, empresa_id, client, max_rodadas)
    raise ValueError(f"LLM_PROVIDER inválido: {provedor!r} (use 'anthropic' ou 'ollama')")


# --------------------------------------------------------------------------
# Anthropic
# --------------------------------------------------------------------------
def _responder_anthropic(pergunta, empresa_id, client, max_rodadas):
    if client is None:
        from anthropic import Anthropic

        client = Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
    modelo = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    mensagens = [{"role": "user", "content": pergunta}]

    for _ in range(max_rodadas):
        resp = client.messages.create(
            model=modelo,
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOL_SCHEMAS,
            messages=mensagens,
        )
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")

        mensagens.append({"role": "assistant", "content": resp.content})
        resultados = []
        for bloco in resp.content:
            if bloco.type == "tool_use":
                saida = executar_ferramenta(bloco.name, bloco.input, empresa_id)
                resultados.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": bloco.id,
                        "content": json.dumps(saida, ensure_ascii=False, default=str),
                    }
                )
        mensagens.append({"role": "user", "content": resultados})

    return MSG_SEM_CONCLUSAO


# --------------------------------------------------------------------------
# Ollama (modelo local)
# --------------------------------------------------------------------------
def _schemas_ollama() -> list[dict]:
    """Converte os schemas das ferramentas para o formato do Ollama."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOL_SCHEMAS
    ]


def _responder_ollama(pergunta, empresa_id, http, max_rodadas):
    if http is None:
        import httpx

        http = httpx
    base = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    modelo = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    mensagens = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": pergunta},
    ]

    for _ in range(max_rodadas):
        r = http.post(
            f"{base}/api/chat",
            json={
                "model": modelo,
                "messages": mensagens,
                "tools": _schemas_ollama(),
                "stream": False,
            },
            timeout=300,
        )
        r.raise_for_status()
        msg = r.json()["message"]
        chamadas = msg.get("tool_calls") or []
        if not chamadas:
            return msg.get("content", "")

        mensagens.append(msg)
        for chamada in chamadas:
            func = chamada["function"]
            args = func.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            saida = executar_ferramenta(func["name"], args, empresa_id)
            mensagens.append(
                {
                    "role": "tool",
                    "tool_name": func["name"],
                    "content": json.dumps(saida, ensure_ascii=False, default=str),
                }
            )

    return MSG_SEM_CONCLUSAO
