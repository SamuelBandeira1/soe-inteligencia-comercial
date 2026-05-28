import pandas as pd

ROOT = "C:/Users/samuel.bandeira/Desktop/soe-inteligencia-comercial"

for emp in ["ACC", "ACI", "SIN"]:
    df = pd.read_csv(f"{ROOT}/data/raw/base_vendas_{emp}.csv",
                     sep=";", encoding="utf-8-sig", decimal=",",
                     dtype={"ID_CLIENTE": str, "ID_FORNECEDOR": str})
    df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True)
    v = df["Vendas Vol.Ton"]
    ger_nulos = df["CD_GERENCIA"].isnull().sum()
    print(f"=== {emp} ===")
    print(f"  Linhas   : {len(df):,}")
    print(f"  Periodo  : {df['DATA'].min().date()} -> {df['DATA'].max().date()}")
    print(f"  Gerencia nula: {ger_nulos:,} ({ger_nulos/len(df)*100:.1f}%)")
    print(f"  Gerencias: {sorted(df['CD_GERENCIA'].dropna().unique())}")
    print(f"  Vol p50={v.median():.2f}  p99={v.quantile(0.99):.1f}  max={v.max():.1f}")
    print(f"  Zeros/neg: {(v <= 0).sum():,}")
    print()

df_n = pd.read_csv(f"{ROOT}/data/raw/base_vendas_nova.csv",
                   sep=";", encoding="utf-8-sig", decimal=",",
                   dtype={"codigo_cliente": str, "codigo_cliente_antigo": str,
                          "codigo_fornecedor": str})
df_n["data_criacao"] = pd.to_datetime(df_n["data_criacao"], dayfirst=True)
v = df_n["VEND_Vol.Ton"]
ger_nulos = df_n["descricao_gerencia_2"].isnull().sum()
ant_nulos = df_n["codigo_cliente_antigo"].isnull().sum()
print("=== NOVA ===")
print(f"  Linhas   : {len(df_n):,}")
print(f"  Periodo  : {df_n['data_criacao'].min().date()} -> {df_n['data_criacao'].max().date()}")
print(f"  Gerencia nula: {ger_nulos:,} ({ger_nulos/len(df_n)*100:.1f}%)")
print(f"  Gerencias: {sorted(df_n['descricao_gerencia_2'].dropna().unique())}")
print(f"  codigo_cliente_antigo nulo (novos IDs): {ant_nulos:,} ({ant_nulos/len(df_n)*100:.1f}%)")
print(f"  Vol p50={v.median():.2f}  p99={v.quantile(0.99):.1f}  max={v.max():.1f}")
print(f"  Zeros/neg: {(v <= 0).sum():,}")
print()

# Previsoes
df_pa = pd.read_csv(f"{ROOT}/data/raw/base_previsao_antiga.csv",
                    sep=";", encoding="utf-8-sig", decimal=",")
df_pa["DATA"] = pd.to_datetime(df_pa["DATA"], dayfirst=True)
ger_nulos = df_pa["CD_GERENCIA"].isnull().sum()
print("=== PREVISAO ANTIGA ===")
print(f"  Linhas   : {len(df_pa):,}")
print(f"  Periodo  : {df_pa['DATA'].min().date()} -> {df_pa['DATA'].max().date()}")
print(f"  Gerencia nula: {ger_nulos:,} ({ger_nulos/len(df_pa)*100:.1f}%)")
print(f"  Gerencias: {sorted(df_pa['CD_GERENCIA'].dropna().unique())}")
print()

df_pn = pd.read_csv(f"{ROOT}/data/raw/base_previsao_nova.csv",
                    sep=";", encoding="utf-8-sig", decimal=",")
print("=== PREVISAO NOVA ===")
print(f"  Linhas   : {len(df_pn):,}")
print(f"  Colunas  : {list(df_pn.columns)}")
ger_nulos = df_pn["Gerencia"].isnull().sum() if "Gerencia" in df_pn.columns else "col ausente"
print(f"  Gerencia nula: {ger_nulos}")
print(f"  Semanas distintas: {df_pn.iloc[:,0].nunique()}")
print(f"  Semana min: {df_pn.iloc[:,0].dropna().iloc[0]}")
print(f"  Semana max: {df_pn.iloc[:,0].dropna().iloc[-1]}")
