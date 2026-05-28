"""
Constantes de negócio do Sistema de Inteligência Comercial S&OE.

Centraliza aqui tudo que é regra de negócio — linhas excluídas,
mapeamentos de nome, parâmetros do score de propensão.
Constantes visuais (cores, paleta) ficam em utils/visual.py.
"""
from pathlib import Path

# ── Caminhos ──────────────────────────────────────────────────────────────────
ROOT           = Path(__file__).resolve().parent.parent
DATA_PROCESSED = ROOT / "data" / "processed"

# ── Meses em português ────────────────────────────────────────────────────────
MESES = {
    1: "Janeiro",  2: "Fevereiro", 3: "Março",    4: "Abril",
    5: "Maio",     6: "Junho",     7: "Julho",     8: "Agosto",
    9: "Setembro", 10: "Outubro",  11: "Novembro", 12: "Dezembro",
}

# ── Linhas de produto ─────────────────────────────────────────────────────────
# Linhas a excluir de TODAS as visualizações (meta_soe=0, sem produto ativo)
LINHAS_EXCLUIR: set[str] = {
    # Inox — sem meta ativa
    "INOX BARRA", "INOX SUCATA", "INOX TUBO",
    # Alumínio — sem operação ativa
    "ALUMINIO TUBO", "ALUMINIO BARRA", "ALUMINIO CHAPA",
    # Sucata / resíduos
    "SUCATA", "SUCATA FERROSA", "SUCATA NAO FERROSA",
    # Outros sem produto ativo
    "INDEFINIDO", "NAO IDENTIFICADO",
}

# Normaliza nomes de linha entre vendas e meta (ex.: BOBINA → BOBINA SLITTER)
MAPA_NOME_LINHA: dict[str, str] = {
    "BOBINA": "BOBINA SLITTER",
}

# Override de família para linhas com família ausente ou incorreta nas vendas
FAMILIA_OVERRIDE: dict[str, str] = {
    "FM": "LONGOS",
}

# ── Mapeamento de Gerências Comerciais ────────────────────────────────────────
# Comercial INOX: família INOX independe de região (prevalece sobre regional)
# Comercial 1   : Centro-Oeste, Sul, Sudeste
# Comercial 2   : Norte, Nordeste
GERENCIA_CONFIG: dict[str, dict] = {
    "Comercial INOX": {
        "familias_override": {"INOX"},       # família → força esta gerência
        "regioes": set(),                    # sem restrição regional (familia prevalece)
        "cor": "#5C6BC0",                    # azul aço inox
        "emoji": "⚙️",
    },
    "Comercial 1": {
        "familias_override": set(),
        "regioes": {"CENTRO-OESTE", "SUL", "SUDESTE", "CENTRO OESTE"},
        "cor": "#1B2A4A",                    # azul marinho primário
        "emoji": "🏭",
    },
    "Comercial 2": {
        "familias_override": set(),
        "regioes": {"NORTE", "NORDESTE"},
        "cor": "#D96B2D",                    # laranja acento
        "emoji": "🌿",
    },
}

# Rótulo padrão quando a gerência não bate com nenhum mapeamento
GERENCIA_DESCONHECIDA = "Não Classificado"

# ── Mapa UF → Região ─────────────────────────────────────────────────────────
# Usado no ETL para derivar a coluna `regiao` a partir de `uf`
UF_PARA_REGIAO: dict[str, str] = {
    # Nordeste
    "CE": "NORDESTE", "MA": "NORDESTE", "PI": "NORDESTE", "RN": "NORDESTE",
    "PB": "NORDESTE", "PE": "NORDESTE", "AL": "NORDESTE", "SE": "NORDESTE",
    "BA": "NORDESTE",
    # Norte
    "PA": "NORTE", "AM": "NORTE", "TO": "NORTE", "AP": "NORTE",
    "RO": "NORTE", "RR": "NORTE", "AC": "NORTE",
    # Sudeste
    "SP": "SUDESTE", "RJ": "SUDESTE", "MG": "SUDESTE", "ES": "SUDESTE",
    # Sul
    "PR": "SUL", "SC": "SUL", "RS": "SUL",
    # Centro-Oeste
    "GO": "CENTRO-OESTE", "MT": "CENTRO-OESTE", "MS": "CENTRO-OESTE",
    "DF": "CENTRO-OESTE",
}

# ── Normalização de nomes de Gerência (ETL) ───────────────────────────────────
# Mapeia variações de grafia vindas dos sistemas de origem → nome canônico
MAPA_GERENCIA_NORM: dict[str, str] = {
    # sistema novo (base_vendas_soe.csv)
    "comercial i":      "Comercial 1",
    "comercial 1":      "Comercial 1",
    "comercial ii":     "Comercial 2",
    "comercial 2":      "Comercial 2",
    "comercial inox":   "Comercial INOX",
    # previsão (base_previsao.xlsx — uppercase)
    "comercial 3":      "Comercial 2",    # COMERCIAL 3 = extensão do Comercial 2
    "e-commerce":       "Comercial 2",
}

# ── Normalização de nomes de Empresa (ETL) ────────────────────────────────────
MAPA_EMPRESA_NORM: dict[str, str] = {
    "SINOBRAS": "SIN",
}

# Empresas reconhecidas pelo sistema (outras são filtradas com aviso no log)
EMPRESAS_VALIDAS: set[str] = {"ACC", "ACI", "SIN"}

# ── Parâmetros do Score de Propensão ─────────────────────────────────────────
# Penalidades de recência aplicadas sobre o score final
# Formato: (dias_min, dias_max_inclusive, multiplicador)
PENALIDADES_RECENCIA: list[tuple[int, int, float]] = [
    (0,   7,   0.60),   # comprou esta semana — sinaliza "esperar"
    (8,   30,  0.85),   # no ciclo do mês
    (31,  100, 1.00),   # janela normal de recompra B2B
    (101, 180, 0.65),   # quase desativado
    (181, 9999, 0.30),  # desativado
]

# Clientes com primeira compra dentro deste prazo recebem flag NOVO
CLIENTE_NOVO_DIAS: int = 60

# Clientes com inatividade >= este prazo E <= compras_max são "Reativação Profunda"
REATIVACAO_PROFUNDA_DIAS: int = 365
REATIVACAO_PROFUNDA_COMPRAS_MAX: int = 3

# Linhas com menos que este número de meses de histórico recebem tier INDEFINIDO
LINHA_HISTORICO_MIN_MESES: int = 6
