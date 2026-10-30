"""Urgência de compra com lógica fuzzy (versão SIMPLIFICADA, estilo Sugeno).

Entradas:
  - cobertura (dias de estoque = estoque atual / venda média diária)
  - giro (venda média diária)
Saída: pontuação de urgência de 0 a 100.

É uma versão didática, independente do motor de sugestão do EstoqueMax.
"""


def _esq(x: float, a: float, b: float) -> float:
    """Pertinência 'ombro esquerdo': 1 até a, cai linearmente até 0 em b."""
    if x <= a:
        return 1.0
    if x >= b:
        return 0.0
    return (b - x) / (b - a)


def _dir(x: float, a: float, b: float) -> float:
    """Pertinência 'ombro direito': 0 até a, sobe linearmente até 1 em b."""
    return 1.0 - _esq(x, a, b)


def _tri(x: float, a: float, b: float, c: float) -> float:
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    return (x - a) / (b - a) if x < b else (c - x) / (c - b)


def _cobertura(dias: float) -> dict[str, float]:
    return {
        "baixa": _esq(dias, 3, 7),
        "media": _tri(dias, 3, 7, 14),
        "alta": _dir(dias, 7, 14),
    }


def _giro(venda_diaria: float) -> dict[str, float]:
    return {
        "baixo": _esq(venda_diaria, 1, 3),
        "medio": _tri(venda_diaria, 1, 4, 10),
        "alto": _dir(venda_diaria, 4, 10),
    }


# Base de regras 3x3 = 9 regras: (cobertura, giro) -> urgência (0 a 100)
REGRAS = {
    ("baixa", "alto"): 100,
    ("baixa", "medio"): 85,
    ("baixa", "baixo"): 65,
    ("media", "alto"): 70,
    ("media", "medio"): 50,
    ("media", "baixo"): 30,
    ("alta", "alto"): 25,
    ("alta", "medio"): 10,
    ("alta", "baixo"): 0,
}


def urgencia(cobertura_dias: float, venda_media_diaria: float) -> float:
    cob = _cobertura(cobertura_dias)
    giro = _giro(venda_media_diaria)
    soma_pesos = 0.0
    soma = 0.0
    for (c, g), saida in REGRAS.items():
        forca = min(cob[c], giro[g])  # operador E = mínimo
        soma_pesos += forca
        soma += forca * saida
    return round(soma / soma_pesos, 1) if soma_pesos else 0.0


def nivel(pontuacao: float) -> str:
    if pontuacao >= 75:
        return "crítica"
    if pontuacao >= 50:
        return "alta"
    if pontuacao >= 25:
        return "média"
    return "baixa"
