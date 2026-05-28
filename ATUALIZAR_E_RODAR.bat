@echo off
chcp 65001 >nul
title Sistema de Inteligência Comercial S^&OE

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   Sistema de Inteligência Comercial  S^&OE           ║
echo  ║   Atualização de Dados + Dashboard                   ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Verifica se o venv existe
if not exist "venv\Scripts\python.exe" (
    echo  [ERRO] Ambiente virtual nao encontrado em venv\
    echo  Execute: python -m venv venv ^& pip install -r requirements.txt
    pause
    exit /b 1
)

echo  [1/2] Processando dados atualizados...
echo  --------------------------------------------------------
echo.
venv\Scripts\python.exe scripts\atualiza_dados.py
if errorlevel 1 (
    echo.
    echo  [ERRO] Falha ao processar os dados.
    echo  Verifique se os CSVs estao em data\raw\
    pause
    exit /b 1
)

echo.
echo  --------------------------------------------------------
echo  [2/2] Iniciando o Dashboard...
echo  Acesse: http://localhost:8501
echo  Para encerrar: feche esta janela ou pressione Ctrl+C
echo  --------------------------------------------------------
echo.

venv\Scripts\python.exe -m streamlit run app\dashboard.py --server.headless false

pause
