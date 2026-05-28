import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
df = pd.read_parquet(ROOT / "data/processed/vendas_filtrada.parquet")

print("=== ESTRUTURA ===")
print(f"Linhas: {len(df):,}")
print(f"Periodo: {df['data'].min().date()} -> {df['data'].max().date()}")
print(f"Colunas: {list(df.columns)}")

print("\n=== VOL_TON stats ===")
print(df["vol_ton"].describe().round(2))

print("\n=== Outliers vol_ton ===")
for q in [0.95, 0.99, 0.999]:
    print(f"  p{q*100:.1f} = {df['vol_ton'].quantile(q):.1f} ton")
outliers = df[df["vol_ton"] > df["vol_ton"].quantile(0.99)]
print(f"  Registros acima p99: {len(outliers):,} ({len(outliers)/len(df)*100:.2f}%)")

print("\n=== Nulos por coluna ===")
nulos = df.isnull().sum()
print(nulos[nulos > 0] if nulos.any() else "  Nenhum nulo encontrado")

print("\n=== Fontes ===")
print(df["fonte"].value_counts())

print("\n=== Top 15 linhas por volume total ===")
print(df.groupby("linha")["vol_ton"].sum().sort_values(ascending=False).head(15).round(0))

print("\n=== Volume mensal total (ultimos 12 meses) ===")
df["ano_mes"] = df["data"].dt.to_period("M")
ultimos12 = df[df["data"] >= df["data"].max() - pd.DateOffset(months=12)]
print(ultimos12.groupby("ano_mes")["vol_ton"].sum().round(0))

print("\n=== Clientes distintos por fonte ===")
print(df.groupby("fonte")["cd_cliente"].nunique())

print("\n=== Empresas distintas ===")
print(df["empresa"].value_counts())

print("\n=== Val_mm zerado mas vol_ton > 0 (suspeitos) ===")
suspeitos = df[(df["vol_ton"] > 0) & (df["val_mm"].fillna(0) == 0)]
print(f"  {len(suspeitos):,} registros ({len(suspeitos)/len(df)*100:.1f}%)")
