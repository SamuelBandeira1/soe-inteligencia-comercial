"""
Carregamento seguro de dados — suporta dois modos:

  LOCAL  → lê os .parquet diretamente de data/processed/ (desenvolvimento)
  CLOUD  → baixa os arquivos do Google Drive via ID configurado em
            .streamlit/secrets.toml (produção no Streamlit Cloud)

Como funciona a detecção automática:
  - Se st.secrets tiver a chave [gdrive], usa o modo CLOUD
  - Caso contrário, usa o modo LOCAL

Configuração para Streamlit Cloud (arquivo .streamlit/secrets.toml):
  [gdrive]
  vendas_id = "ID_DO_ARQUIVO_VENDAS_NO_GDRIVE"
  meta_id   = "ID_DO_ARQUIVO_META_NO_GDRIVE"

Para obter o ID de um arquivo no Google Drive:
  1. Clique com botão direito no arquivo → "Compartilhar"
  2. Mude para "Qualquer pessoa com o link pode visualizar"
  3. O ID está na URL: drive.google.com/file/d/<ID_AQUI>/view
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
import streamlit as st

# Caminho local (usado no modo LOCAL)
_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA = _ROOT / "data" / "processed"


def _is_cloud() -> bool:
    """
    Retorna True apenas se:
      - secrets.toml tiver a chave [gdrive], E
      - os parquets locais NAO existirem (ex.: Streamlit Cloud sem arquivos)
    Se os parquets estiverem presentes localmente (HF Spaces com upload direto),
    usa o modo LOCAL mesmo que secrets exista.
    """
    try:
        if "gdrive" not in st.secrets:
            return False
        # Prefere arquivo local se existir (HF Spaces com parquets no repo)
        if (_DATA / "vendas_filtrada.parquet").exists():
            return False
        return True
    except Exception:
        return False


def _download_gdrive(file_id: str) -> bytes:
    """
    Baixa um arquivo do Google Drive pelo ID (arquivo público ou compartilhado).
    Usa requests — sem necessidade de OAuth para arquivos públicos.
    """
    try:
        import requests
    except ImportError:
        st.error("Pacote 'requests' não encontrado. Adicione ao requirements.txt.")
        st.stop()

    # URL de export direto (funciona para arquivos compartilhados publicamente)
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp = requests.get(url, timeout=60)

    # Arquivos grandes exigem confirmação de vírus do Google
    if "confirm=" in resp.text and len(resp.content) < 10_000:
        import re
        match = re.search(r'confirm=([^&"]+)', resp.text)
        if match:
            confirm = match.group(1)
            url = f"{url}&confirm={confirm}"
            resp = requests.get(url, timeout=120)

    if resp.status_code != 200:
        st.error(f"Falha ao baixar arquivo do Google Drive (ID: {file_id}). "
                 f"Status: {resp.status_code}")
        st.stop()

    return resp.content


@st.cache_data(show_spinner="Carregando dados...", ttl=3600)
def load_vendas() -> pd.DataFrame:
    """Carrega vendas_filtrada.parquet (local ou Google Drive)."""
    if _is_cloud():
        file_id = st.secrets["gdrive"]["vendas_id"]
        raw = _download_gdrive(file_id)
        return pd.read_parquet(io.BytesIO(raw))
    else:
        path = _DATA / "vendas_filtrada.parquet"
        if not path.exists():
            st.error(f"Arquivo não encontrado: {path}\n\n"
                     "Execute os scripts de processamento primeiro.")
            st.stop()
        return pd.read_parquet(path)


@st.cache_data(show_spinner="Carregando dados...", ttl=3600)
def load_meta() -> pd.DataFrame:
    """Carrega meta_semanal.parquet (local ou Google Drive)."""
    if _is_cloud():
        file_id = st.secrets["gdrive"]["meta_id"]
        raw = _download_gdrive(file_id)
        return pd.read_parquet(io.BytesIO(raw))
    else:
        path = _DATA / "meta_semanal.parquet"
        if not path.exists():
            st.error(f"Arquivo não encontrado: {path}\n\n"
                     "Execute os scripts de processamento primeiro.")
            st.stop()
        return pd.read_parquet(path)
