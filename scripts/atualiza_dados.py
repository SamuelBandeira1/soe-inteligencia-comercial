"""
Pipeline de atualização de dados — S&OE Inteligência Comercial
==============================================================

Fontes:
  data/raw/base_vendas_soe.csv   — Vendas unificadas (ACC+ACI+SIN), Jan/2024 em diante
  data/raw/base_previsao.xlsx    — Previsão S&OE + S&OP por Semana Técnica (2026)

Saídas:
  data/processed/vendas_unificada.parquet  — dado bruto tratado, histórico completo
  data/processed/vendas_filtrada.parquet   — dado para o dashboard (linhas ativas)
  data/processed/meta_semanal.parquet      — previsão com semana técnica
  data/processed/relatorio_qualidade.txt   — log de qualidade gerado a cada atualização

Regra principal: DADOS HISTÓRICOS SÃO PRESERVADOS INTEGRALMENTE.
  Outliers de volume são FLAGRADOS no relatório mas não são removidos.
  Derivações (gerência, regiao) são registradas como 'imputado' vs 'original'.

Como usar:
  ATUALIZAR_E_RODAR.bat  (duplo clique)
  ou:  python scripts/atualiza_dados.py
"""
from __future__ import annotations

import re
import sys
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

# Adiciona app/ ao path para importar config e utils
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
from config import (
    LINHAS_EXCLUIR, MAPA_NOME_LINHA, FAMILIA_OVERRIDE,
    UF_PARA_REGIAO, MAPA_GERENCIA_NORM, MAPA_EMPRESA_NORM, EMPRESAS_VALIDAS,
)

# ── Caminhos ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
RAW  = ROOT / "data" / "raw"
OUT  = ROOT / "data" / "processed"

# ── Schema canônico de vendas (colunas salvas no parquet) ────────────────────
# Ordem definida aqui — colunas extras da base de origem são descartadas.
COLUNAS_VENDAS_PARQUET = [
    "data", "ano", "mes", "semana_mes",
    "empresa", "gerencia", "gerencia_origem",
    "regiao", "uf",
    "familia", "linha", "grupo",
    "cd_cliente", "nome_cliente", "telefone_cliente", "vendedor",
    "vol_ton", "val_mm", "valor_liquido", "valor_imposto",
    "fonte", "flag_outlier",
]

# Gerências válidas após normalização
_GERENCIAS_VALIDAS = {"Comercial 1", "Comercial 2", "Comercial INOX"}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"  {msg}")


def _invalidar_cache() -> None:
    dirs = [d for d in ROOT.rglob("__pycache__") if "venv" not in str(d)]
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)
    log(f"Cache invalidado ({len(dirs)} diretório(s))")


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZAÇÃO DE DIMENSÕES
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar_empresa(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes de empresa e filtra as desconhecidas com aviso."""
    df = df.copy()
    df["empresa"] = (
        df["empresa"]
        .astype(str).str.strip().str.upper()
        .replace(MAPA_EMPRESA_NORM)
    )
    desconhecidas = df[~df["empresa"].isin(EMPRESAS_VALIDAS)]["empresa"].value_counts()
    if not desconhecidas.empty:
        log(f"  [AVISO] Empresas não reconhecidas (ignoradas): "
            f"{desconhecidas.to_dict()}")
        df = df[df["empresa"].isin(EMPRESAS_VALIDAS)].copy()
    return df


def _derivar_gerencia_por_linha(familia: str, regiao: str) -> tuple[str, str]:
    """
    Deriva gerência a partir de família e região quando o campo não está preenchido.
    Retorna (gerencia, metodo) onde metodo = 'familia' | 'regiao' | 'desconhecido'.
    """
    fam = str(familia).strip().upper() if pd.notna(familia) else ""
    reg = str(regiao).strip().upper()  if pd.notna(regiao)  else ""

    if fam in {"INOX"}:
        return "Comercial INOX", "familia"
    if reg in {"CENTRO-OESTE", "CENTRO OESTE", "SUL", "SUDESTE"}:
        return "Comercial 1", "regiao"
    if reg in {"NORTE", "NORDESTE"}:
        return "Comercial 2", "regiao"
    return "Não Classificado", "desconhecido"


def _normalizar_gerencia(df: pd.DataFrame, col_ger: str) -> pd.DataFrame:
    """
    Normaliza nomes de gerência para o padrão canônico e deriva quando necessário.
    Adiciona colunas 'gerencia' e 'gerencia_origem'.
    Depende de 'regiao' e 'familia' já estarem normalizadas no dataframe.
    """
    df = df.copy()

    # Normaliza via mapa
    df["_ger_norm"] = (
        df[col_ger]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda v: MAPA_GERENCIA_NORM.get(v, v))
    )

    # Marcação de origem
    df["gerencia_origem"] = "original"
    mask_imputar = (
        df[col_ger].isna()
        | (df[col_ger].astype(str).str.strip() == "")
        | (~df["_ger_norm"].isin(_GERENCIAS_VALIDAS))
    )

    if mask_imputar.any():
        derivado = df[mask_imputar].apply(
            lambda r: _derivar_gerencia_por_linha(r.get("familia", ""), r.get("regiao", ""))[0],
            axis=1,
        )
        df.loc[mask_imputar, "_ger_norm"]       = derivado
        df.loc[mask_imputar, "gerencia_origem"] = "imputado"

    df["gerencia"] = df["_ger_norm"].fillna("Não Classificado")
    return df.drop(columns=["_ger_norm"])


def _derivar_regiao(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona coluna 'regiao' mapeando de 'uf' via UF_PARA_REGIAO do config."""
    df = df.copy()
    df["regiao"] = df["uf"].map(UF_PARA_REGIAO).fillna("NÃO IDENTIFICADO")
    return df


def _normalizar_strings_dimensoes(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Aplica strip + upper nas colunas de dimensão informadas.
    Valores nulos/NaN viram 'NÃO CLASSIFICADO' para não aparecerem como 'NAN' nos gráficos.
    """
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("NÃO CLASSIFICADO")
                .astype(str)
                .str.strip()
                .str.upper()
                .replace({"NAN": "NÃO CLASSIFICADO", "NONE": "NÃO CLASSIFICADO", "": "NÃO CLASSIFICADO"})
            )
    return df


def _aplicar_overrides_linha(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica MAPA_NOME_LINHA e FAMILIA_OVERRIDE do config."""
    df = df.copy()
    if MAPA_NOME_LINHA:
        df["linha"] = df["linha"].replace(
            {k.upper(): v.upper() for k, v in MAPA_NOME_LINHA.items()}
        )
    if FAMILIA_OVERRIDE:
        df["familia"] = df.apply(
            lambda r: FAMILIA_OVERRIDE.get(r["linha"], r["familia"]),
            axis=1,
        )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 1 — Leitura e tratamento da base de vendas
# ─────────────────────────────────────────────────────────────────────────────

def _ler_vendas() -> pd.DataFrame:
    """
    Lê base_vendas_soe.csv — base unificada do sistema novo.

    Colunas esperadas na entrada:
      data, empresa, cd_cliente, nome_cliente, telefone_cliente, vendedor,
      linha, vol_ton, valor_venda_mil, valor_liquido, valor_imposto,
      ano, mes, semana_mes, gerencia, uf, familia, grupo
    """
    path = RAW / "base_vendas_soe.csv"
    if not path.exists():
        log(f"[ERRO] {path.name} não encontrado em data/raw/")
        sys.exit(1)

    log(f"Lendo {path.name} ({path.stat().st_size / 1024**2:.0f} MB)...")
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        dtype={"cd_cliente": str},
        parse_dates=["data"],
        dayfirst=False,
    )

    # ── Renomear colunas para schema canônico ──────────────────────────────
    rename = {
        "valor_venda_mil": "val_mm",
    }
    # Compatibilidade: coluna pode vir como 'telefone_cliente' — não precisamos dela
    df = df.rename(columns=rename)

    # ── Normalizar dimensões de texto ──────────────────────────────────────
    df = _normalizar_strings_dimensoes(df, ["empresa", "linha", "familia", "grupo", "uf"])

    # ── Normalizar empresa ────────────────────────────────────────────────
    df = _normalizar_empresa(df)

    # ── Derivar região a partir de UF ─────────────────────────────────────
    df = _derivar_regiao(df)

    # ── Normalizar gerência ────────────────────────────────────────────────
    df = _normalizar_gerencia(df, "gerencia")

    # ── Overrides de linha e família ──────────────────────────────────────
    df = _aplicar_overrides_linha(df)

    # ── Garantir colunas de calendário ────────────────────────────────────
    # A base nova já traz ano, mes, semana_mes — apenas garantimos os tipos
    df["data"] = pd.to_datetime(df["data"], format="mixed")
    df["ano"]  = df["ano"].astype(int)
    df["mes"]  = df["mes"].astype(int)
    df["semana_mes"] = df["semana_mes"].astype(int)

    # ── Garantir colunas de valor ─────────────────────────────────────────
    for col in ["val_mm", "valor_liquido", "valor_imposto"]:
        if col not in df.columns:
            df[col] = np.nan
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── Fonte ──────────────────────────────────────────────────────────────
    df["fonte"] = "sistema_novo"

    # ── Flag de outlier (p99.9 por linha) ────────────────────────────────
    df["flag_outlier"] = False
    for linha, grp in df.groupby("linha"):
        if len(grp) < 10:
            continue
        thr = grp["vol_ton"].quantile(0.999)
        df.loc[grp[grp["vol_ton"] > thr].index, "flag_outlier"] = True

    n_out = df["flag_outlier"].sum()
    log(f"  {len(df):,} linhas | "
        f"período: {df['data'].min().date()} → {df['data'].max().date()}")
    log(f"  Empresas: {df['empresa'].value_counts().to_dict()}")
    log(f"  Gerências: {df['gerencia'].value_counts().to_dict()}")
    if n_out:
        log(f"  [!] Outliers flagados (p99.9 por linha): {n_out:,}")

    return df


def _filtrar_vendas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica filtros de qualidade — retorna base limpa para o dashboard."""
    df = df.copy()

    # Linhas de produto inativas
    linhas_excluir_upper = {l.upper() for l in LINHAS_EXCLUIR}
    antes = len(df)
    df = df[~df["linha"].isin(linhas_excluir_upper)]
    removidos_linha = antes - len(df)

    # Volumes zero (não são vendas reais)
    antes = len(df)
    df = df[df["vol_ton"] > 0].copy()
    removidos_zero = antes - len(df)

    log(f"  Linhas inativas removidas : {removidos_linha:,} registros")
    log(f"  Registros vol_ton=0 remov.: {removidos_zero:,}")
    log(f"  Total filtrado final      : {len(df):,} linhas")
    return df.reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 2 — Leitura e tratamento da previsão
# ─────────────────────────────────────────────────────────────────────────────

def _ler_previsao() -> pd.DataFrame:
    """
    Lê base_previsao.xlsx — previsão por Semana Técnica (formato 2026).

    Colunas esperadas na entrada:
      semana técnica, família, linha, grupo, região, estado, gerência,
      empresa, Programa SOE, Plano S&OP
    """
    path = RAW / "base_previsao.xlsx"
    if not path.exists():
        log(f"[AVISO] {path.name} não encontrado — meta_semanal.parquet não será gerado.")
        return pd.DataFrame()

    log(f"Lendo {path.name}...")
    df = pd.read_excel(path, dtype=str)

    # ── Renomear colunas ──────────────────────────────────────────────────
    # O Excel usa acentos/maiúsculas — normalização via mapa flexível
    def _ascii(s: str) -> str:
        """Remove acentos para comparação de nomes de colunas."""
        return (s.lower().strip()
                .replace("ê", "e").replace("é", "e").replace("è", "e")
                .replace("â", "a").replace("á", "a").replace("à", "a").replace("ã", "a")
                .replace("ô", "o").replace("ó", "o").replace("õ", "o")
                .replace("ú", "u").replace("ü", "u")
                .replace("í", "i").replace("ç", "c"))

    rename = {}
    for col in df.columns:
        cl = _ascii(col)
        if "semana" in cl:                    rename[col] = "semana_tw"
        elif "fam" in cl:                     rename[col] = "familia"
        elif cl == "linha":                   rename[col] = "linha"
        elif cl == "grupo":                   rename[col] = "grupo"
        elif "regiao" in cl or "regi" in cl:  rename[col] = "regiao"
        elif "estado" in cl or cl == "uf":    rename[col] = "uf"
        elif "gerencia" in cl or "gerenci" in cl: rename[col] = "_ger_raw"
        elif "empresa" in cl:                 rename[col] = "empresa"
        elif "programa" in cl:                rename[col] = "meta_soe"
        elif "plano" in cl:                   rename[col] = "meta_sop"
    df = df.rename(columns=rename)

    # ── Normalizar strings ────────────────────────────────────────────────
    df = _normalizar_strings_dimensoes(df, ["empresa", "linha", "familia", "grupo", "uf"])

    # ── Normalizar empresa ────────────────────────────────────────────────
    # PORTO não faz parte das operações monitoradas — filtramos aqui
    df["empresa"] = df["empresa"].str.strip().str.upper().replace(MAPA_EMPRESA_NORM)
    df = df[df["empresa"].isin(EMPRESAS_VALIDAS)].copy()

    # ── Normalizar região (já vem da previsão, mas padronizamos) ─────────
    if "regiao" in df.columns:
        df["regiao"] = (
            df["regiao"]
            .astype(str).str.strip().str.upper()
            .str.replace("CENTRO-OESTE", "CENTRO OESTE", regex=False)
        )

    # ── Normalizar gerência ────────────────────────────────────────────────
    # Previsão usa maiúsculas (COMERCIAL 1, COMERCIAL 3, etc.)
    # Já configurado em MAPA_GERENCIA_NORM do config.py
    df = _normalizar_gerencia(df, "_ger_raw")

    # ── Parse da Semana Técnica → ano, mes, semana_mes ────────────────────
    # Formato: "TW01b M1 2026", "TW05a M1 2026", etc.
    def _parse_tw(s: str) -> tuple[int, int, int]:
        try:
            m = re.match(r"TW(\d+)[abAB]?\s+M(\d+)\s+(\d{4})", str(s).strip())
            if m:
                tw_num = int(m.group(1))
                mes    = int(m.group(2))
                ano    = int(m.group(3))
                # semana_mes: aproximação por posição da TW no mês
                # TW com 'a' = primeira metade do mês, 'b' = segunda metade
                sub = m.group(0)
                semana_mes = _tw_para_semana_mes(tw_num, mes, ano)
                return ano, mes, semana_mes
        except Exception:
            pass
        return 0, 0, 1

    if "semana_tw" in df.columns:
        parsed = df["semana_tw"].apply(_parse_tw)
        df["ano"]        = [p[0] for p in parsed]
        df["mes"]        = [p[1] for p in parsed]
        df["semana_mes"] = [p[2] for p in parsed]
    else:
        df["ano"] = df["mes"] = df["semana_mes"] = 0

    # Garante tipos int
    for col in ["ano", "mes", "semana_mes"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Remove linhas sem calendário válido
    df = df[(df["ano"] > 0) & (df["mes"] > 0)].copy()

    # ── Converte volumes ──────────────────────────────────────────────────
    df["meta_soe"] = pd.to_numeric(df.get("meta_soe", 0), errors="coerce").fillna(0.0)
    df["meta_sop"] = pd.to_numeric(df.get("meta_sop", 0), errors="coerce").fillna(0.0)

    # Remove linhas com meta zero (sem planejamento real)
    df = df[(df["meta_soe"] > 0) | (df["meta_sop"] > 0)].copy()

    # ── Overrides de linha ────────────────────────────────────────────────
    df = _aplicar_overrides_linha(df)

    # ── Linhas inativas ───────────────────────────────────────────────────
    linhas_excluir_upper = {l.upper() for l in LINHAS_EXCLUIR}
    df = df[~df["linha"].isin(linhas_excluir_upper)].copy()

    # ── Data de referência (1º dia do mês) ────────────────────────────────
    df["data"] = pd.to_datetime(
        df[["ano", "mes"]].assign(day=1).rename(columns={"ano": "year", "mes": "month"}),
        errors="coerce",
    )

    log(f"  {len(df):,} linhas | anos: {sorted(df['ano'].unique().tolist())}")
    log(f"  Empresas   : {df['empresa'].value_counts().to_dict()}")
    log(f"  Gerências  : {df['gerencia'].value_counts().to_dict()}")
    log(f"  meta_soe total: {df['meta_soe'].sum():,.1f} ton | "
        f"meta_sop total: {df['meta_sop'].sum():,.1f} ton")
    return df.reset_index(drop=True)


def _tw_para_semana_mes(tw_num: int, mes: int, ano: int) -> int:
    """
    Converte número da semana técnica ISO para semana_mes (1–5).
    Tenta usar calendar_tw.py; cai em aproximação se falhar.
    """
    try:
        from datetime import date, timedelta
        from utils.calendar_tw import day_to_semana_tw
        import calendar as _cal

        jan4    = date(ano, 1, 4)
        w1_mon  = jan4 - timedelta(days=jan4.weekday())
        tw_mon  = w1_mon + timedelta(weeks=tw_num - 1)

        if tw_mon.month == mes:
            dia_ref = tw_mon.day
        else:
            tw_sun = tw_mon + timedelta(days=6)
            if tw_sun.month == mes:
                dia_ref = tw_sun.day
            else:
                return 1

        result = day_to_semana_tw(ano, mes, dia_ref)
        return result if result else 1
    except Exception:
        return 1


# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 3 — Relatório de qualidade
# ─────────────────────────────────────────────────────────────────────────────

def _gerar_relatorio(df_v: pd.DataFrame, df_m: pd.DataFrame) -> str:
    linhas = [
        "=" * 62,
        f"  RELATÓRIO DE QUALIDADE — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "=" * 62,
        "",
        "── VENDAS ──────────────────────────────────────────────────",
        f"  Total de registros  : {len(df_v):,}",
        f"  Período             : {df_v['data'].min().date()} → {df_v['data'].max().date()}",
        f"  Clientes únicos     : {df_v['cd_cliente'].nunique():,}",
        f"  Linhas de produto   : {df_v['linha'].nunique()}",
        "",
        "  Gerência — distribuição:",
    ]
    for ger, cnt in df_v["gerencia"].value_counts().items():
        pct    = cnt / len(df_v) * 100
        n_imp  = (df_v[df_v["gerencia"] == ger]["gerencia_origem"] == "imputado").sum()
        linhas.append(f"    {ger:<22} {cnt:>8,}  ({pct:4.1f}%)  imputado: {n_imp:,}")

    linhas += [
        "",
        "  Volume (vol_ton):",
        f"    Mediana : {df_v['vol_ton'].median():.2f} ton",
        f"    p95     : {df_v['vol_ton'].quantile(0.95):.1f} ton",
        f"    p99     : {df_v['vol_ton'].quantile(0.99):.1f} ton",
        f"    p99.9   : {df_v['vol_ton'].quantile(0.999):.1f} ton",
        f"    Máximo  : {df_v['vol_ton'].max():.1f} ton",
        f"    Outliers: {df_v['flag_outlier'].sum():,} registros flagados (p99.9/linha)",
    ]

    if df_v["flag_outlier"].sum() > 0:
        linhas.append("")
        linhas.append("  Top 10 outliers por volume:")
        top = (
            df_v[df_v["flag_outlier"]]
            .sort_values("vol_ton", ascending=False)
            .head(10)[["data", "empresa", "linha", "cd_cliente", "nome_cliente", "vol_ton"]]
        )
        for _, r in top.iterrows():
            linhas.append(
                f"    {r['data'].date()} | {r['empresa']} | {r['linha']:<20} | "
                f"{r['cd_cliente']} {str(r.get('nome_cliente',''))[:20]:<20} | "
                f"{r['vol_ton']:,.1f} ton"
            )

    # Volume mensal últimos 12 meses
    linhas += ["", "  Volume mensal (últimos 12 meses):"]
    df_v["_ano_mes"] = df_v["data"].dt.to_period("M")
    cutoff = df_v["data"].max() - pd.DateOffset(months=12)
    vol_mensal = (
        df_v[df_v["data"] >= cutoff]
        .groupby("_ano_mes")["vol_ton"].sum()
        .sort_index()
    )
    for periodo, vol in vol_mensal.items():
        linhas.append(f"    {periodo}  {vol:>12,.0f} ton")

    if len(vol_mensal) >= 3:
        media = vol_mensal[:-1].mean()
        for periodo, vol in vol_mensal[:-1].items():
            if vol < media * 0.50:
                linhas.append(
                    f"  [!] ALERTA: {periodo} com {vol:,.0f} ton "
                    f"({vol/media*100:.0f}% da média) — possível gap de dados."
                )

    # Previsão
    linhas += [
        "",
        "── PREVISÃO ────────────────────────────────────────────────",
    ]
    if df_m.empty:
        linhas.append("  (sem dados de previsão)")
    else:
        linhas += [
            f"  Total de registros  : {len(df_m):,}",
            f"  Período             : {df_m['ano'].min()} → {df_m['ano'].max()}",
            f"  Registros S&OE > 0  : {(df_m['meta_soe'] > 0).sum():,}",
            f"  Registros S&OP > 0  : {(df_m['meta_sop'] > 0).sum():,}",
            f"  meta_soe total      : {df_m['meta_soe'].sum():,.1f} ton",
            f"  meta_sop total      : {df_m['meta_sop'].sum():,.1f} ton",
        ]

    linhas += ["", "=" * 62, "  Dados prontos para o dashboard.", "=" * 62, ""]
    return "\n".join(linhas)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    inicio = datetime.now()

    # Força stdout em UTF-8 para evitar erros de encoding no Windows
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print()
    print("=" * 56)
    print("  S&OE Inteligencia Comercial -- Atualizacao de Dados")
    print("=" * 56)
    print()

    # ── VENDAS ────────────────────────────────────────────────────────────────
    print("[ 1/4 ] Lendo base de vendas unificada...")
    df_v = _ler_vendas()

    path_unif = OUT / "vendas_unificada.parquet"
    # Seleciona apenas colunas do schema (descarta extras)
    cols_salvar = [c for c in COLUNAS_VENDAS_PARQUET if c in df_v.columns]
    df_v[cols_salvar].to_parquet(path_unif, index=False)
    log(f"Salvo: {path_unif.name} ({path_unif.stat().st_size/1024**2:.1f} MB)")

    print("\n[ 2/4 ] Filtrando para o dashboard...")
    df_filt = _filtrar_vendas(df_v)

    path_filt = OUT / "vendas_filtrada.parquet"
    cols_filt = [c for c in COLUNAS_VENDAS_PARQUET if c in df_filt.columns]
    df_filt[cols_filt].to_parquet(path_filt, index=False)
    log(f"Salvo: {path_filt.name} ({path_filt.stat().st_size/1024**2:.1f} MB)")

    # ── PREVISÃO ──────────────────────────────────────────────────────────────
    print("\n[ 3/4 ] Processando previsão (S&OE + S&OP)...")
    df_meta = _ler_previsao()

    if not df_meta.empty:
        path_meta = OUT / "meta_semanal.parquet"
        df_meta.to_parquet(path_meta, index=False)
        log(f"Salvo: {path_meta.name} ({path_meta.stat().st_size/1024**2:.1f} MB)")
    else:
        log("[AVISO] Previsão vazia — meta_semanal.parquet não gerado.")

    # ── RELATÓRIO ─────────────────────────────────────────────────────────────
    print("\n[ 4/4 ] Gerando relatório de qualidade...")
    relatorio = _gerar_relatorio(df_filt, df_meta)
    path_rel = OUT / "relatorio_qualidade.txt"
    path_rel.write_text(relatorio, encoding="utf-8")
    log(f"Salvo: {path_rel.name}")
    print()
    print(relatorio)

    _invalidar_cache()

    elapsed = (datetime.now() - inicio).total_seconds()
    print(f"\n  Concluido em {elapsed:.1f}s")
    print("  Reinicie o Streamlit para carregar os novos dados.\n")


if __name__ == "__main__":
    main()
