"""
incrementa_vendas_diario.py
────────────────────────────
Substitui o mes atual na base principal pelo arquivo mensal atualizado.

Por que mensal?
  Cancelamentos e ajustes retroativos fazem a base do mes ser reescrita
  todos os dias. O arquivo diario contem o mes completo e atualizado.

Fluxo
─────
1. Localiza o arquivo mensal em data/raw/ com o padrao vendas_soe_mes_YYYY-MM.csv
   (usa ano/mes corrente por padrao, ou recebe --mes YYYY-MM)
2. Le o arquivo mensal e valida colunas e tipos
3. Confirma que o arquivo so contem dados do mes esperado
4. Remove da base todos os registros daquele ano+mes (se existirem)
5. Concatena o arquivo mensal ao final da base
6. Salva a base de volta em data/raw/base_vendas_soe.csv

Uso
───
  python scripts/incrementa_vendas_diario.py              # usa mes corrente
  python scripts/incrementa_vendas_diario.py --mes 2026-05
  python scripts/incrementa_vendas_diario.py --dry-run    # so valida, nao salva
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

# ── Caminhos ──────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
BASE    = RAW_DIR / "base_vendas_soe.csv"

ENCODING = "utf-8-sig"
SEP      = ","

# Colunas obrigatorias e tipos esperados
COLUNAS_ESPERADAS = {
    "data":             "object",
    "empresa":          "object",
    "cd_cliente":       "int64",
    "nome_cliente":     "object",
    "telefone_cliente": "object",
    "vendedor":         "object",
    "linha":            "object",
    "vol_ton":          "float64",
    "valor_venda_mil":  "float64",
    "valor_liquido":    "float64",
    "valor_imposto":    "float64",
    "ano":              "int64",
    "mes":              "int64",
    "semana_mes":       "int64",
    "gerencia":         "object",
    "uf":               "object",
    "familia":          "object",
    "grupo":            "object",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    safe = msg.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8", errors="replace"
    )
    print(safe, flush=True)


def _validar_colunas(df: pd.DataFrame, nome: str) -> None:
    faltando = [c for c in COLUNAS_ESPERADAS if c not in df.columns]
    extras   = [c for c in df.columns if c not in COLUNAS_ESPERADAS]
    if faltando:
        raise ValueError(
            f"[{nome}] Colunas faltando: {faltando}\n"
            f"  Encontradas: {df.columns.tolist()}"
        )
    if extras:
        _log(f"  [!] [{nome}] Colunas extras (serao mantidas): {extras}")


def _validar_tipos(df: pd.DataFrame, nome: str) -> None:
    erros = []
    for col, tipo_esp in COLUNAS_ESPERADAS.items():
        if col not in df.columns:
            continue
        tipo_real = str(df[col].dtype)
        ok = (
            tipo_real == tipo_esp
            or (tipo_esp == "int64"   and tipo_real in ("int32", "int64", "Int64"))
            or (tipo_esp == "float64" and tipo_real in ("float32", "float64"))
            or (tipo_esp == "object"  and tipo_real == "object")
        )
        if not ok:
            erros.append(f"  '{col}': esperado {tipo_esp}, encontrado {tipo_real}")
    if erros:
        raise TypeError(f"[{nome}] Tipos incompativeis:\n" + "\n".join(erros))


def _carregar(path: Path, nome: str) -> pd.DataFrame:
    _log(f"  Lendo {nome}: {path.name} ...")
    df = pd.read_csv(path, encoding=ENCODING, sep=SEP, low_memory=False)
    _log(f"    -> {len(df):,} linhas x {len(df.columns)} colunas")
    return df


def _mes_do_arquivo(path: Path) -> tuple[int, int] | None:
    """Extrai (ano, mes) do nome vendas_soe_mes_YYYY-MM.csv. None se nao casar."""
    try:
        ym = path.stem.split("vendas_soe_mes_")[1]
        ano, mes = ym.split("-")
        ano, mes = int(ano), int(mes)
        return (ano, mes) if 1 <= mes <= 12 else None
    except (IndexError, ValueError):
        return None


def _resolver_mes_automatico() -> tuple[int, int, str] | None:
    """
    Decide o mes alvo quando nenhum --mes foi passado.

    Regra: usa o mes corrente se houver arquivo dele. Caso contrario (ex.: virou
    o mes mas ainda estamos fechando o anterior), usa o arquivo mensal
    'vendas_soe_mes_*.csv' modificado mais recentemente -- ou seja, o que voce
    acabou de atualizar. Retorna None se nao houver nenhum arquivo mensal.
    """
    hoje = date.today()
    atual = RAW_DIR / f"vendas_soe_mes_{hoje.year}-{hoje.month:02d}.csv"
    if atual.exists():
        return hoje.year, hoje.month, (
            f"  [auto] Usando o mes corrente: {hoje.year}-{hoje.month:02d}"
        )

    candidatos = sorted(
        RAW_DIR.glob("vendas_soe_mes_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for p in candidatos:
        ym = _mes_do_arquivo(p)
        if ym:
            ano, mes = ym
            return ano, mes, (
                f"  [auto] Mes corrente ({hoje.year}-{hoje.month:02d}) nao tem arquivo.\n"
                f"  [auto] Usando o arquivo mensal mais recente modificado:\n"
                f"         {p.name}  ->  alvo {ano}-{mes:02d}"
            )
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main(mes_str: str | None = None, dry_run: bool = False) -> None:

    # 1. Resolve ano/mes alvo
    if mes_str:
        try:
            partes = mes_str.split("-")
            ano_alvo = int(partes[0])
            mes_alvo = int(partes[1])
            if not (1 <= mes_alvo <= 12):
                raise ValueError
        except (ValueError, IndexError):
            _log(f"[ERRO] Mes invalido: '{mes_str}' -- use formato YYYY-MM")
            sys.exit(1)
    else:
        resolvido = _resolver_mes_automatico()
        if resolvido is None:
            hoje = date.today()
            ano_alvo = hoje.year
            mes_alvo = hoje.month
        else:
            ano_alvo, mes_alvo, motivo = resolvido
            _log(motivo)

    mes_fmt = f"{ano_alvo}-{mes_alvo:02d}"
    arquivo_mensal = RAW_DIR / f"vendas_soe_mes_{mes_fmt}.csv"

    _log(f"\n{'='*60}")
    _log(f"  Mes alvo  : {mes_fmt}  (ano={ano_alvo}, mes={mes_alvo})")
    _log(f"  Arquivo   : {arquivo_mensal.name}")
    _log(f"  Dry-run   : {'SIM (nao salva)' if dry_run else 'NAO (salva)'}")
    _log(f"{'='*60}\n")

    # 2. Verifica existencia
    if not arquivo_mensal.exists():
        _log(f"[ERRO] Arquivo mensal nao encontrado: {arquivo_mensal}")
        _log(f"       Copie vendas_soe_mes_{mes_fmt}.csv para data/raw/")
        sys.exit(1)

    if not BASE.exists():
        _log(f"[ERRO] Base principal nao encontrada: {BASE}")
        sys.exit(1)

    # 3. Carrega
    _log("[>] Carregando arquivos ...")
    df_mensal = _carregar(arquivo_mensal, "mensal")
    df_base   = _carregar(BASE, "base")

    # 4. Valida estrutura
    _log("\n[?] Validando estrutura do arquivo mensal ...")
    _validar_colunas(df_mensal, "mensal")
    _validar_tipos(df_mensal, "mensal")
    _log("  [OK] Colunas OK")
    _log("  [OK] Tipos OK")

    # Confirma que o arquivo mensal so tem o ano+mes esperado
    combinacoes = df_mensal.groupby(["ano", "mes"]).size().reset_index()
    combinacoes_lista = [(int(r["ano"]), int(r["mes"])) for _, r in combinacoes.iterrows()]
    if combinacoes_lista != [(ano_alvo, mes_alvo)]:
        _log(f"  [!] Combinacoes ano/mes no arquivo: {combinacoes_lista}")
        _log(f"      Esperado apenas: [({ano_alvo}, {mes_alvo})]")
        resposta = input("  Continuar mesmo assim? (s/N): ").strip().lower()
        if resposta != "s":
            _log("Operacao cancelada pelo usuario.")
            sys.exit(0)

    # 5. Remove o mes atual da base, se existir
    _log(f"\n[?] Verificando se {mes_fmt} ja existe na base ...")
    mask_mes = (df_base["ano"] == ano_alvo) & (df_base["mes"] == mes_alvo)
    linhas_existentes = int(mask_mes.sum())

    if linhas_existentes > 0:
        _log(f"  [!] Encontradas {linhas_existentes:,} linhas de {mes_fmt} na base")
        _log("  [>] Removendo para substituir pela versao atualizada ...")
        vol_anterior = float(df_base.loc[mask_mes, "vol_ton"].sum())
        df_base = df_base[~mask_mes].copy()
        _log(f"  [OK] Removidas. Base agora com {len(df_base):,} linhas")
    else:
        vol_anterior = 0.0
        _log(f"  [OK] Mes {mes_fmt} nao encontrado -- insercao limpa")

    # 6. Alinha colunas
    colunas_base = df_base.columns.tolist()
    extras_mensal = [c for c in df_mensal.columns if c not in colunas_base]
    if extras_mensal:
        _log(f"  [!] Colunas extras no mensal ignoradas: {extras_mensal}")
    df_mensal_alin = df_mensal[[c for c in colunas_base if c in df_mensal.columns]]

    # 7. Concatena
    _log(f"\n[+] Concatenando {len(df_mensal_alin):,} linhas do mes {mes_fmt} ...")
    df_final = pd.concat([df_base, df_mensal_alin], ignore_index=True)
    _log(f"  [OK] Base final: {len(df_final):,} linhas")

    # 8. Sanity checks
    _log("\n[?] Sanity checks ...")
    _log(f"  Periodo total  : {df_final['data'].min()} -> {df_final['data'].max()}")

    meses_na_base = df_final.groupby(["ano", "mes"])["vol_ton"].sum()
    vol_mes_novo  = float(df_mensal_alin["vol_ton"].sum())
    _log(f"  Volume {mes_fmt}   : {vol_mes_novo:,.1f} ton "
         f"({len(df_mensal_alin):,} linhas)")

    # Compara volume com o que existia antes (se existia)
    if linhas_existentes > 0:
        delta_vol = vol_mes_novo - vol_anterior
        _log(f"  Volume anterior: {vol_anterior:,.1f} ton -> {vol_mes_novo:,.1f} ton "
             f"({delta_vol:+,.1f})")
        _log(f"  Linhas: {linhas_existentes:,} -> {len(df_mensal_alin):,} "
             f"({len(df_mensal_alin) - linhas_existentes:+,})")

    nulos = df_final[["vol_ton", "empresa", "linha", "data"]].isnull().sum()
    if nulos.any():
        _log(f"  [!] Nulos nas colunas criticas:\n{nulos[nulos > 0]}")
    else:
        _log("  [OK] Sem nulos nas colunas criticas")

    if dry_run:
        _log("\n[--] DRY-RUN: nenhum arquivo foi alterado.")
        return

    # 9. Salva
    _log(f"\n[>] Salvando base em {BASE.name} ...")
    df_final.to_csv(BASE, index=False, encoding=ENCODING, sep=SEP)
    _log(f"  [OK] Arquivo salvo: {len(df_final):,} linhas x {len(df_final.columns)} colunas")
    _log(f"\n[DONE] {mes_fmt} atualizado na base com sucesso.\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Substitui o mes atual na base_vendas_soe.csv pelo arquivo mensal atualizado."
    )
    parser.add_argument(
        "--mes", "-m",
        metavar="YYYY-MM",
        help="Mes a atualizar (padrao: mes corrente)",
        default=None,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida e mostra o que faria, sem salvar nada",
    )
    args = parser.parse_args()
    main(mes_str=args.mes, dry_run=args.dry_run)
