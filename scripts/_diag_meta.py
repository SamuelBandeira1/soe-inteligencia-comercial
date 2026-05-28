import pandas as pd

df = pd.read_parquet("data/processed/meta_semanal.parquet")
m26 = df[(df["ano"]==2026) & (df["mes"]==5)]
print("=== META MAI/2026 (parquet) ===")
print(f"Registros      : {len(m26)}")
print(f"meta_soe total : {m26['meta_soe'].sum():.1f} ton")
print(f"meta_sop total : {m26['meta_sop'].sum():.1f} ton")
print(f"semana_mes     : {sorted(m26['semana_mes'].unique())}")
print()

# Compara com vendas realizadas de mai/2026
dv = pd.read_parquet("data/processed/vendas_filtrada.parquet")
v26 = dv[(dv["ano"]==2026) & (dv["mes"]==5)]
print(f"=== VENDAS MAI/2026 ===")
print(f"vol_ton total : {v26['vol_ton'].sum():.1f} ton")
print(f"semana_mes    : {sorted(v26['semana_mes'].unique())}")
print()

# Checa a previsao nova bruta
raw = pd.read_csv("data/raw/base_previsao_nova.csv", sep=";", encoding="utf-8-sig", decimal=",")
raw = raw.loc[:, ~raw.columns.str.startswith("Unnamed")]
print("=== BASE_PREVISAO_NOVA — colunas ===")
print(list(raw.columns))

prog_col  = [c for c in raw.columns if "programa" in c.lower() or "Programa" in c][0]
plano_col = [c for c in raw.columns if "plano" in c.lower() and "op" in c.lower()][0]
sem_col   = raw.columns[0]

tw_maio = raw[raw[sem_col].astype(str).str.contains("M5 2026", na=False)]
print(f"\nRegistros M5 2026 : {len(tw_maio)}")
print(f"Semanas distintas : {list(tw_maio[sem_col].unique())}")
prog_sum = pd.to_numeric(tw_maio[prog_col], errors="coerce").sum()
plano_sum = pd.to_numeric(tw_maio[plano_col], errors="coerce").sum()
print(f"Soma {prog_col}  : {prog_sum:.1f}")
print(f"Soma {plano_col} : {plano_sum:.1f}")

# Amostra de linhas de volume
print("\nAmostra (top 5 por programa):")
tw_maio_cp = tw_maio.copy()
tw_maio_cp["_prog"] = pd.to_numeric(tw_maio_cp[prog_col], errors="coerce")
print(tw_maio_cp.nlargest(5, "_prog")[[sem_col, "Linha", "Região", "Estado", prog_col, plano_col]].to_string())

# Verifica se semana_mes esta sendo calculado corretamente
print("\n=== semana_mes no parquet — distribuicao para 2026 ===")
print(df[df["ano"]==2026].groupby(["mes","semana_mes"])["meta_soe"].sum().unstack(fill_value=0).round(0))
