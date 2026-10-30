"""API FastAPI do assistente de estoque."""
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

from app.assistant import responder  # noqa: E402
from app.db import empresa_por_api_key, get_conn  # noqa: E402

app = FastAPI(title="Assistente de Estoque com LLM", version="0.2.0")


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/perguntar")
def perguntar(corpo: Pergunta, x_api_key: str | None = Header(default=None)):
    conn = get_conn()
    try:
        empresa = empresa_por_api_key(conn, x_api_key)
    finally:
        conn.close()
    if empresa is None:
        raise HTTPException(status_code=401, detail="Chave de API inválida.")
    try:
        resposta = responder(corpo.pergunta, empresa["id"])
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Não consegui falar com o Ollama. Ele está aberto e o modelo "
                "foi baixado (ollama pull)?"
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # erros da API da Anthropic (saldo, chave etc.)
        if e.__class__.__module__.startswith("anthropic"):
            raise HTTPException(
                status_code=502,
                detail=f"Erro na API da Anthropic: {getattr(e, 'message', str(e))}",
            )
        raise
    return {"empresa": empresa["nome"], "resposta": resposta}
