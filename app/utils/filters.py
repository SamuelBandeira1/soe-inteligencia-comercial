"""
Filtragem de DataFrames de vendas por seleções da interface.

A função apply_filters aplica um conjunto de filtros multi-seleção
(empresa, linha, região, UF) a um DataFrame, seguindo a semântica:

  - Lista NÃO-vazia  → mantém apenas as linhas cujo valor está na lista
  - Lista vazia       → não filtra naquela coluna (mantém tudo)

Mapeamento chave (plural) → coluna do DataFrame:
  empresas → empresa
  linhas   → linha
  regioes  → regiao
  ufs      → uf

O DataFrame de entrada nunca é mutado — retorna-se sempre uma cópia.
Colunas ausentes no DataFrame são ignoradas silenciosamente.
"""
from __future__ import annotations

import pandas as pd

# Mapeamento das chaves do dict de filtros para as colunas do DataFrame
_CHAVE_COLUNA = {
    "empresas": "empresa",
    "linhas": "linha",
    "regioes": "regiao",
    "ufs": "uf",
}


def apply_filters(df: pd.DataFrame, filtros: dict[str, list]) -> pd.DataFrame:
    """
    Aplica filtros multi-seleção a um DataFrame de vendas.

    Parameters
    ----------
    df : DataFrame com as colunas empresa, linha, regiao, uf (ausências toleradas)
    filtros : dict com chaves plurais (empresas, linhas, regioes, ufs),
              cada uma mapeando para uma lista de valores selecionados

    Returns
    -------
    Cópia do DataFrame com apenas as linhas que atendem a todos os filtros.
    Listas vazias não restringem a coluna correspondente.
    """
    resultado = df.copy()
    for chave, coluna in _CHAVE_COLUNA.items():
        valores = filtros.get(chave)
        if valores and coluna in resultado.columns:
            resultado = resultado[resultado[coluna].isin(valores)]
    return resultado
