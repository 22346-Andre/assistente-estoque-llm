from app.fuzzy import nivel, urgencia
from app.tools import executar_ferramenta


def nomes(lista, chave="nome"):
    return {item[chave] for item in lista}


def test_estoque_baixo_empresa_1(conn, hoje):
    r = executar_ferramenta("produtos_estoque_baixo", {}, 1, conn, hoje)
    n = nomes(r)
    assert "Leite integral 1L" in n and "Óleo de soja 900ml" in n
    assert "Arroz 5kg" not in n


def test_isolamento_entre_empresas(conn, hoje):
    r1 = executar_ferramenta("produtos_estoque_baixo", {}, 1, conn, hoje)
    r2 = executar_ferramenta("produtos_estoque_baixo", {}, 2, conn, hoje)
    assert "Fermento biológico" not in nomes(r1)
    assert "Pão de forma" not in nomes(r2)
    assert "Fermento biológico" in nomes(r2)


def test_modelo_nao_consegue_trocar_empresa(conn, hoje):
    # Mesmo que o modelo mande empresa_id=2, vale o empresa_id do servidor (1).
    r = executar_ferramenta("produtos_estoque_baixo", {"empresa_id": 2}, 1, conn, hoje)
    assert "Fermento biológico" not in nomes(r)
    assert "Pão de forma" in nomes(r)


def test_vencimento_ordenado_fefo(conn, hoje):
    r = executar_ferramenta("lotes_proximos_vencimento", {"dias": 7}, 1, conn, hoje)
    datas = [i["validade"] for i in r]
    assert datas == sorted(datas)
    assert r[0]["produto"] == "Pão de forma" and r[0]["dias_restantes"] == 2
    assert all(i["dias_restantes"] <= 7 for i in r)


def test_vencimento_argumento_invalido_usa_padrao(conn, hoje):
    r = executar_ferramenta("lotes_proximos_vencimento", {"dias": "abc"}, 1, conn, hoje)
    assert isinstance(r, list)


def test_sugestao_ordenada_por_urgencia(conn, hoje):
    r = executar_ferramenta("sugestao_de_compra", {}, 1, conn, hoje)
    pontos = [i["urgencia_pontos"] for i in r]
    assert pontos == sorted(pontos, reverse=True)
    por_nome = {i["produto"]: i for i in r}
    assert r[0]["produto"] == "Leite integral 1L"  # ~2 dias de cobertura e giro alto
    assert por_nome["Óleo de soja 900ml"]["urgencia_nivel"] == "crítica"  # estoque zerado
    assert "Arroz 5kg" not in nomes(r, "produto")  # estoque confortável


def test_ferramenta_desconhecida(conn, hoje):
    r = executar_ferramenta("apagar_tudo", {}, 1, conn, hoje)
    assert "erro" in r


def test_fuzzy_limites_e_ordem():
    assert urgencia(0, 12) > urgencia(10, 12) > urgencia(30, 12)
    assert urgencia(1, 12) > urgencia(1, 0.5)  # mais giro, mais urgente
    assert 0 <= urgencia(999, 0) <= 100
    assert nivel(90) == "crítica" and nivel(10) == "baixa"
