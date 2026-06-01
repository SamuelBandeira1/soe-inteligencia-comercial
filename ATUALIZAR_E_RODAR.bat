@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title SOE - Inteligencia Comercial

echo.
echo  ========================================================
echo   Sistema de Inteligencia Comercial  S^&OE
echo   Atualizacao Diaria + Dashboard
echo  ========================================================
echo.

cd /d "%~dp0"

:: ---------------------------------------------------------
::  Verifica venv
:: ---------------------------------------------------------
if not exist "venv\Scripts\python.exe" (
    echo  [ERRO] Ambiente virtual nao encontrado em venv\
    echo  Execute no terminal:
    echo    python -m venv venv
    echo    venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

set PY=venv\Scripts\python.exe

:: =========================================================
::  PASSO 1 - Incrementa base de vendas com arquivo mensal
:: =========================================================
echo  [1/3] Incrementando base de vendas mensal...
echo  --------------------------------------------------------
echo.
echo   Qual mes voce quer atualizar?
echo   - Deixe em branco e pressione Enter para deteccao automatica
echo     (usa o mes corrente; se nao houver arquivo dele, usa o
echo      arquivo vendas_soe_mes_*.csv mais recente que voce modificou).
echo   - Ou digite no formato AAAA-MM  (ex.: 2026-05 para maio).
echo.
set "MES="
set /p MES="  Mes a atualizar [Enter = automatico]: "
echo.

if defined MES (
    %PY% scripts\incrementa_vendas_diario.py --mes !MES!
) else (
    %PY% scripts\incrementa_vendas_diario.py
)

if errorlevel 1 (
    echo.
    echo  [AVISO] Nao foi possivel atualizar a base de vendas.
    echo  Verifique se o arquivo vendas_soe_mes_AAAA-MM.csv
    echo  esta dentro da pasta data\raw\
    echo.
    set /p CONT="  Continuar sem atualizar a base? (S/N): "
    if /i not "!CONT!"=="S" (
        echo  Operacao cancelada.
        pause
        exit /b 1
    )
)

:: =========================================================
::  PASSO 2 - ETL: processa raw -> parquet
:: =========================================================
echo.
echo  --------------------------------------------------------
echo  [2/3] Processando dados para o dashboard (ETL)...
echo  --------------------------------------------------------
echo.
%PY% scripts\atualiza_dados.py
if errorlevel 1 (
    echo.
    echo  [ERRO] Falha no processamento dos dados.
    echo  Verifique os arquivos em data\raw\
    pause
    exit /b 1
)

:: =========================================================
::  PASSO 3 - Abre o Dashboard para validacao
:: =========================================================
echo.
echo  --------------------------------------------------------
echo  [3/3] Abrindo Dashboard para validacao...
echo.
echo  Acesse: http://localhost:8501
echo.
echo  Quando terminar a validacao pressione Ctrl+C aqui
echo  --------------------------------------------------------
echo.
%PY% -m streamlit run app\dashboard.py --server.headless false

echo.
echo  Dashboard encerrado.
echo  Para publicar a versao, clique em FAZER_PUSH.bat
echo.
pause
endlocal
