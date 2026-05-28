"""
upload_dados_hf.py
──────────────────
Envia os parquets processados para o HF Spaces em um unico commit atomico,
depois forca o restart do Space para garantir que os dados novos sejam carregados.

O token e o repo_id sao lidos automaticamente da URL do remote 'hf'.

Uso:
  python scripts/upload_dados_hf.py
"""

import subprocess
import sys
import re
import time
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

ARQUIVOS = [
    "meta_semanal.parquet",
    "vendas_filtrada.parquet",
    "vendas_unificada.parquet",
]


def _log(msg: str) -> None:
    safe = msg.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8", errors="replace"
    )
    print(safe, flush=True)


def _obter_token_e_repo() -> tuple[str, str]:
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "hf"],
            cwd=ROOT, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except subprocess.CalledProcessError:
        _log("[ERRO] Remote 'hf' nao encontrado.")
        sys.exit(1)

    m = re.match(r"https://([^:]+):([^@]+)@huggingface\.co/spaces/(.+)", url)
    if not m:
        _log("[ERRO] URL do remote 'hf' em formato inesperado.")
        sys.exit(1)

    return m.group(2), m.group(3).rstrip("/")


def main() -> None:
    try:
        from huggingface_hub import HfApi, CommitOperationAdd
    except ImportError:
        _log("[ERRO] huggingface_hub nao instalado.")
        _log("  Execute: pip install huggingface_hub")
        sys.exit(1)

    token, repo_id = _obter_token_e_repo()
    api = HfApi()

    _log(f"\n  Destino : {repo_id} (HF Spaces)")
    _log(f"  Pasta   : data/processed/\n")

    # ── Monta operacoes de upload em um unico commit atomico ──────────────────
    operacoes = []
    total_mb  = 0.0

    for fname in ARQUIVOS:
        path = PROCESSED / fname
        if not path.exists():
            _log(f"  [!] {fname} nao encontrado, pulando...")
            continue
        mb = path.stat().st_size / 1024 ** 2
        total_mb += mb
        _log(f"  + {fname} ({mb:.1f} MB)")
        operacoes.append(
            CommitOperationAdd(
                path_in_repo=f"data/processed/{fname}",
                path_or_fileobj=str(path),
            )
        )

    if not operacoes:
        _log("[ERRO] Nenhum arquivo encontrado em data/processed/")
        sys.exit(1)

    _log(f"\n  Total   : {len(operacoes)} arquivo(s) | {total_mb:.1f} MB")
    _log("  Enviando em um unico commit (aguarde)...\n")

    try:
        api.create_commit(
            repo_id=repo_id,
            repo_type="space",
            operations=operacoes,
            commit_message=f"dados atualizados ({len(operacoes)} parquets)",
            token=token,
        )
        _log("  [OK] Commit realizado com sucesso.")
    except Exception as e:
        _log(f"  [ERRO] Falha no commit: {e}")
        sys.exit(1)

    # ── Forca restart do Space para garantir dados novos ─────────────────────
    _log("\n  Reiniciando o Space para carregar os dados novos...")
    time.sleep(3)   # pequena espera para o commit ser processado
    try:
        api.restart_space(repo_id=repo_id, token=token)
        _log("  [OK] Space reiniciado!")
    except Exception as e:
        _log(f"  [!] Restart automatico falhou: {e}")
        _log("      Reinicie manualmente no HF Spaces se necessario.")

    _log(f"\n  [DONE] Dados enviados. Dashboard sera atualizado em ~1 minuto.\n")


if __name__ == "__main__":
    main()
