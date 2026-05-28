@echo off
chcp 65001 >nul
title Dashboard S^&OE

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo  [ERRO] Ambiente virtual nao encontrado.
    pause
    exit /b 1
)

echo.
echo  Iniciando Dashboard... Aguarde.
echo  Acesse: http://localhost:8501
echo  Para encerrar: feche esta janela ou pressione Ctrl+C
echo.

venv\Scripts\python.exe -m streamlit run app\dashboard.py --server.headless false

pause
