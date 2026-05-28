"""
upload_dados_hf.py
──────────────────
Envia os parquets processados para o HF Spaces.
Usa delete + add explicito para garantir que o commit seja criado
mesmo que o HF ache que os arquivos nao mudaram.

Token e repo_id lidos automaticamente da URL do remote 'hf'.
"""

import subprocess
import sys
import re
from datetime import datetime
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
        from huggingface_hub import HfApi, CommitOperationAdd, CommitOperationDelete
    except ImportError:
        _log("[ERRO] huggingface_hub nao instalado.")
        sys.exit(1)

    token, repo_id = _obter_token_e_repo()
    api = HfApi()

    _log(f"\n  Destino : {repo_id} (HF Spaces)")
    _log(f"  Pasta   : data/processed/\n")

    # ── Verifica quais arquivos existem atualmente no HF ──────────────────────
    try:
        arquivos_no_hf = set(api.list_repo_files(
            repo_id=repo_id, repo_type="space", token=token
        ))
    except Exception as e:
        _log(f"  [ERRO] Nao foi possivel listar arquivos do HF: {e}")
        sys.exit(1)

    # ── Monta operacoes: delete dos existentes + add dos novos ────────────────
    operacoes = []
    total_mb  = 0.0

    for fname in ARQUIVOS:
        path = PROCESSED / fname
        if not path.exists():
            _log(f"  [!] {fname} nao encontrado localmente, pulando...")
            continue

        repo_path = f"data/processed/{fname}"
        mb = path.stat().st_size / 1024 ** 2
        total_mb += mb

        # Remove o arquivo existente no HF antes de re-adicionar
        # Isso garante que o commit seja criado mesmo com conteudo igual
        if repo_path in arquivos_no_hf:
            operacoes.append(CommitOperationDelete(path_in_repo=repo_path))
            _log(f"  ~ {fname} (substituindo versao existente, {mb:.1f} MB)")
        else:
            _log(f"  + {fname} (novo, {mb:.1f} MB)")

        operacoes.append(
            CommitOperationAdd(
                path_in_repo=repo_path,
                path_or_fileobj=str(path),
            )
        )

    # Arquivo de timestamp para registrar a ultima atualizacao
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ts_path = "data/processed/.last_updated"
    if ts_path in arquivos_no_hf:
        operacoes.append(CommitOperationDelete(path_in_repo=ts_path))
    operacoes.append(
        CommitOperationAdd(
            path_in_repo=ts_path,
            path_or_fileobj=ts.encode(),
        )
    )

    if not operacoes:
        _log("[ERRO] Nenhum arquivo encontrado em data/processed/")
        sys.exit(1)

    _log(f"\n  Total   : {len([o for o in operacoes if isinstance(o, CommitOperationAdd) and o.path_in_repo != ts_path])} parquet(s) | {total_mb:.1f} MB")
    _log(f"  Enviando para o HF (aguarde)...\n")

    try:
        commit = api.create_commit(
            repo_id=repo_id,
            repo_type="space",
            operations=operacoes,
            commit_message=f"dados atualizados {ts}",
            token=token,
        )
        _log(f"  [OK] Commit criado: {commit.commit_url}")
    except Exception as e:
        _log(f"  [ERRO] Falha no commit: {e}")
        sys.exit(1)

    _log(f"\n  [DONE] Dados no HF. O Space vai rebuildar automaticamente.\n")


if __name__ == "__main__":
    main()
