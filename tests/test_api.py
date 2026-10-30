from fastapi.testclient import TestClient

import app.main as main


def test_sem_chave_retorna_401(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "api.db"))
    cliente = TestClient(main.app)
    r = cliente.post("/perguntar", json={"pergunta": "o que comprar?"})
    assert r.status_code == 401


def test_chave_valida_usa_empresa_correta(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "api.db"))
    capturado = {}

    def falso(pergunta, empresa_id, **_):
        capturado["empresa_id"] = empresa_id
        return "ok"

    monkeypatch.setattr(main, "responder", falso)
    cliente = TestClient(main.app)
    r = cliente.post(
        "/perguntar",
        json={"pergunta": "o que comprar?"},
        headers={"X-API-Key": "demo-key-paoquente"},
    )
    assert r.status_code == 200
    assert capturado["empresa_id"] == 2
    assert r.json()["empresa"] == "Padaria Pão Quente"


def test_health():
    assert TestClient(main.app).get("/health").json() == {"status": "ok"}
