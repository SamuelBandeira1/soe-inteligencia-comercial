"""
upload_dados_gdrive.py
──────────────────────
Atualiza os parquets no Google Drive (substitui pelo conteudo novo).
O HF Spaces le os dados diretamente do Drive via st.secrets[gdrive].

PRE-REQUISITO (apenas uma vez):
  1. Acesse https://console.cloud.google.com/
  2. Crie um projeto (ou use um existente)
  3. Ative a API "Google Drive API"
  4. Va em "Credenciais" > "Criar credenciais" > "ID do cliente OAuth 2.0"
  5. Tipo: "App para computador"
  6. Baixe o JSON e salve como:
       <raiz do projeto>/credentials_gdrive.json
  7. Adicione ao .gitignore: credentials_gdrive.json e token_gdrive.json
  8. Execute este script uma vez -- vai abrir o navegador para autenticar
     Nas proximas execucoes sera automatico (token salvo em token_gdrive.json)

Uso:
  python scripts/upload_dados_gdrive.py
"""

import sys
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CREDS     = ROOT / "credentials_gdrive.json"
TOKEN     = ROOT / "token_gdrive.json"

# ID da pasta no Google Drive (da URL: drive.google.com/drive/.../folders/<ID>)
FOLDER_ID = "1yDnvK0IRZMlmgI9LFokjieaVagvHyu-2"

# Arquivos a atualizar: nome_local -> nome_no_drive
ARQUIVOS = {
    "vendas_filtrada.parquet": "vendas_filtrada.parquet",
    "meta_semanal.parquet":    "meta_semanal.parquet",
}

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _log(msg: str) -> None:
    safe = msg.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8", errors="replace"
    )
    print(safe, flush=True)


def _autenticar():
    """Autentica via OAuth2. Abre navegador na primeira vez; usa token salvo depois."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        _log("[ERRO] Instale: pip install google-api-python-client google-auth-oauthlib")
        sys.exit(1)

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS.exists():
                _log("[ERRO] Arquivo credentials_gdrive.json nao encontrado!")
                _log(f"  Esperado em: {CREDS}")
                _log("  Veja as instrucoes no topo deste script.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS), SCOPES)
            _log("  Abrindo navegador para autenticacao Google...")
            creds = flow.run_local_server(port=0)

        TOKEN.write_text(creds.to_json(), encoding="utf-8")
        _log("  [OK] Token salvo. Proximas execucoes serao automaticas.")

    return creds


def _listar_arquivos_pasta(service, folder_id: str) -> dict[str, str]:
    """Retorna {nome: file_id} dos arquivos na pasta."""
    result = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name)",
    ).execute()
    return {f["name"]: f["id"] for f in result.get("files", [])}


def main() -> None:
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        _log("[ERRO] Instale: pip install google-api-python-client")
        sys.exit(1)

    _log("\n  Google Drive - Atualizacao de Dados")
    _log("  ====================================\n")

    creds   = _autenticar()
    service = build("drive", "v3", credentials=creds)

    # Lista arquivos existentes na pasta
    _log("  Verificando arquivos na pasta do Drive...")
    arquivos_drive = _listar_arquivos_pasta(service, FOLDER_ID)
    _log(f"  Encontrados: {list(arquivos_drive.keys())}\n")

    atualizados = 0
    for nome_local, nome_drive in ARQUIVOS.items():
        path = PROCESSED / nome_local
        if not path.exists():
            _log(f"  [!] {nome_local} nao encontrado localmente, pulando...")
            continue

        mb = path.stat().st_size / 1024 ** 2
        media = MediaFileUpload(str(path), resumable=True)

        if nome_drive in arquivos_drive:
            # Atualiza arquivo existente (mantem o mesmo ID e link compartilhado)
            file_id = arquivos_drive[nome_drive]
            _log(f"  Atualizando {nome_drive} ({mb:.1f} MB)...")
            service.files().update(
                fileId=file_id,
                media_body=media,
            ).execute()
            _log(f"  [OK] {nome_drive} atualizado (ID mantido: {file_id})")
        else:
            # Cria novo arquivo na pasta
            _log(f"  Criando {nome_drive} ({mb:.1f} MB)...")
            meta = {"name": nome_drive, "parents": [FOLDER_ID]}
            f = service.files().create(
                body=meta, media_body=media, fields="id"
            ).execute()
            _log(f"  [OK] {nome_drive} criado (novo ID: {f['id']})")
            _log(f"  [!] Atualize o secrets do HF Space com o novo ID: {f['id']}")

        atualizados += 1

    _log(f"\n  [DONE] {atualizados} arquivo(s) atualizado(s) no Google Drive.")
    _log("  O HF Spaces vai usar os dados novos no proximo acesso.\n")


if __name__ == "__main__":
    main()
