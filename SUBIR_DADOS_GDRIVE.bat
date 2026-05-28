@echo off
chcp 65001 >nul
title Upload Dados para Google Drive

cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   Upload dos Dados para o Google Drive               ║
echo  ║   (necessario apos rodar ATUALIZAR_E_RODAR.bat)      ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  Abrindo os arquivos para upload manual...
echo.
echo  Arquivos a enviar:
echo    data\processed\vendas_filtrada.parquet
echo    data\processed\meta_semanal.parquet
echo.
echo  Passos:
echo    1. Faca upload de cada arquivo no Google Drive
echo    2. Clique com botao direito no arquivo - Compartilhar
echo    3. Mude para "Qualquer pessoa com o link pode visualizar"
echo    4. Copie o ID da URL e atualize o secrets no Streamlit Cloud
echo.

explorer data\processed

echo  Pasta aberta. Faca o upload manualmente no Google Drive.
echo.
pause
