"""
sync_vault.py — Sincroniza .memory/ do projeto com o vault Obsidian.

Uso:
    python scripts/sync_vault.py

O que faz:
  1. Lê .memory/long-term.md e extrai seções-chave
  2. Atualiza 00 - Projeto/Estado Atual.md (nota gerada automaticamente)
  3. Cria/atualiza nota de sessão no vault baseada nas sessões mais recentes de .memory/session/
  4. Atualiza 03 - Sessoes/INDEX.md com o índice atualizado

O vault é resolvido via SOE_VAULT_ROOT (env) ou cai no default local.
"""

import os
import re
import glob
from datetime import date
from pathlib import Path

# ── Caminhos ────────────────────────────────────────────────────────────────
PROJETO_ROOT = Path(__file__).parent.parent
MEMORY_DIR   = PROJETO_ROOT / ".memory"
SESSION_DIR  = MEMORY_DIR / "session"
VAULT_ROOT   = Path(os.environ.get("SOE_VAULT_ROOT", "D:/brain_organizer/brain_organizer/SOE"))

LONG_TERM    = MEMORY_DIR / "long-term.md"
VAULT_ROOT_NOTE  = VAULT_ROOT / "00 - Projeto" / "Estado Atual.md"
VAULT_SESSIONS   = VAULT_ROOT / "03 - Sessoes" / "INDEX.md"
VAULT_SESSION_DIR = VAULT_ROOT / "03 - Sessoes"
VAULT_ROADMAP    = VAULT_ROOT / "01 - Roadmap" / "Roadmap.md"

TODAY = date.today().isoformat()


# ── Helpers ──────────────────────────────────────────────────────────────────
def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  ✅ {path.relative_to(VAULT_ROOT) if VAULT_ROOT in path.parents else path.name}")


def extract_section(text: str, header: str) -> str:
    """Extrai uma seção ## do markdown até a próxima seção ##."""
    pattern = rf"(?:^|\n)## {re.escape(header)}\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""


# ── 1. Sincronizar nota-raiz ─────────────────────────────────────────────────
def sync_root_note():
    lt = read(LONG_TERM)
    project_notes = extract_section(lt, "Project Notes")
    discovered    = extract_section(lt, "Discovered Issues")
    preferences   = extract_section(lt, "Preferences")

    # Pega sessões mais recentes para o estado atual
    sessions = sorted(SESSION_DIR.glob("*.md"), reverse=True)[:2]
    session_summary = ""
    for s in sessions:
        name = s.stem
        content = read(s)
        status_match = re.search(r"^## Status\s*\n(.+)", content, re.MULTILINE)
        status = status_match.group(1).strip() if status_match else "?"
        session_summary += f"- [[{name}]] — {status}\n"

    content = f"""---
tags: [soe, projeto, estado]
atualizado: {TODAY}
---

# Estado Atual — SOE Inteligência Comercial · Aço Cearense

> ⚙️ Nota gerada automaticamente por `scripts/sync_vault.py` — não editar à mão.
> Entrada principal hand-maintained: [[HOME]].

## Sobre o Projeto

Dashboard Streamlit de Supply Chain com 5 abas:
1. **Visão Geral**
2. **Plano Comercial**
3. **Demand Sensing** (Monte Carlo probabilístico)
4. **Dashboard UF**
5. **Assertividade do Plano**

**Stack:** Python · Streamlit · Plotly · pandas
**Hospedagem:** Hugging Face Spaces
**Dados:** Google Drive (parquets — nunca no repo)

**Raiz local:**
`C:\\Users\\samue\\Desktop\\projeto_claude_soe\\soe-inteligencia-comercial\\soe-inteligencia-comercial\\`

---

## Regras Absolutas

- ❌ NUNCA fazer push sem o usuário pedir explicitamente
- ❌ NUNCA versionar dados (`data/raw/`, `data/processed/`, secrets)
- ✅ Dados chegam ao HF Spaces via Google Drive
- ✅ `FAZER_PUSH.bat` = apenas código

---

## Sessões Recentes

{session_summary.strip()}

---

## Issues Descobertas (dívida técnica)

{discovered if discovered else "_Nenhuma registrada._"}

---

## Links do Vault

- [[HOME]]
- [[INDEX]]
- [[Roadmap]]
- [[Arquitetura Tecnica]]
- [[Agentes - Indice]]
- [[Skills do Sistema]]
- [[README|UI-UX Design Kit]]
"""
    write(VAULT_ROOT_NOTE, content)


# ── 2. Sincronizar sessões ────────────────────────────────────────────────────
def sync_sessions():
    sessions = sorted(SESSION_DIR.glob("*.md"), reverse=True)
    index_rows = []

    for s in sessions:
        content = read(s)
        status_m = re.search(r"^## Status\s*\n(.+)", content, re.MULTILINE)
        date_m   = re.search(r"^## Last Active\s*\n(.+)", content, re.MULTILINE)
        task_m   = re.search(r"^## Current Task\s*\n(.+)", content, re.MULTILINE)

        status = status_m.group(1).strip() if status_m else "?"
        dt     = date_m.group(1).strip()   if date_m   else "?"
        task   = task_m.group(1).strip()   if task_m   else s.stem

        icon = "✅" if status == "done" else "⏸️" if status == "paused" else "🔄"
        index_rows.append(f"| {dt} | [[{s.stem}\\|{s.stem[:60]}]] | {icon} {status} |")

        # Copia/sincroniza a nota de sessão no vault
        vault_session = VAULT_SESSION_DIR / s.name
        if not vault_session.exists():
            # Converte para formato Obsidian com frontmatter
            vault_content = f"""---
tags: [soe, sessão, {status}]
data: {dt}
status: {status}
---

{content}
"""
            write(vault_session, vault_content)

    # Atualiza índice de sessões
    rows_str = "\n".join(index_rows)

    # Detecta pendências urgentes do long-term
    lt = read(LONG_TERM)
    issues = extract_section(lt, "Discovered Issues")
    urgente = ""
    for line in issues.splitlines():
        if "não foi testada" in line.lower() or "urgente" in line.lower() or "pendente" in line.lower():
            urgente += f"- [ ] {line.strip().lstrip('-').strip()}\n"

    index_content = f"""---
tags: [soe, sessões, índice]
atualizado: {TODAY}
---

# Sessões SOE — Índice

Histórico de sessões de desenvolvimento. Ordenado do mais recente para o mais antigo.

## Sessões

| Data | Título | Status |
|------|--------|--------|
{rows_str}

## Pendências Urgentes

{urgente.strip() if urgente else "_Nenhuma._"}

## Links

- [[HOME]]
- [[Roadmap]]
"""
    write(VAULT_SESSIONS, index_content)


# ── 3. Sincronizar Roadmap ────────────────────────────────────────────────────
def sync_roadmap():
    lt = read(LONG_TERM)
    roadmap_section = extract_section(lt, "⚠️ PRIORIDADE ALTA — Roadmap (solicitado por Humberto, gerente)")
    discovered      = extract_section(lt, "Discovered Issues")

    # Extrai itens de dívida técnica
    divida = []
    for line in discovered.splitlines():
        line = line.strip()
        if line.startswith("-") or line.startswith("*"):
            divida.append(f"- [ ] {line.lstrip('-*').strip()}")

    divida_str = "\n".join(divida) if divida else "_Nenhuma registrada._"

    content = f"""---
tags: [soe, roadmap, prioridade]
atualizado: {TODAY}
---

# Roadmap SOE

## 🔴 Prioridade Alta — Variáveis Exógenas no Demand Sensing

> Solicitado por Humberto (gerente) — capturar sinais de mercado que explicam por que clientes não compram.

{roadmap_section if roadmap_section else "_(ver long-term.md)_"}

---

## 🟡 Limpeza Técnica Pendente

Dívida técnica identificada em `assertividade_plano.py`:

{divida_str}

---

## Links

- [[HOME]]
- [[INDEX]]
- [[Arquitetura Tecnica]]
"""
    write(VAULT_ROADMAP, content)


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    if not VAULT_ROOT.exists():
        print(f"\n[AVISO] Vault não encontrado em '{VAULT_ROOT}'.")
        print("        Defina SOE_VAULT_ROOT ou monte o vault. Nada a sincronizar.\n")
        sys.exit(0)

    print(f"\n[SYNC] Sincronizando vault Obsidian com .memory/ -- {TODAY}\n")
    sync_root_note()
    sync_sessions()
    sync_roadmap()
    print("\n[OK] Vault sincronizado com sucesso.")
