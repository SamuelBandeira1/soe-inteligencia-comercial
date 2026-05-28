@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title SOE - Push GitHub + HF Spaces

cd /d "%~dp0"

echo.
echo  ========================================================
echo   S^&OE - Subir versao para GitHub e HF Spaces
echo  ========================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo  [ERRO] Ambiente virtual nao encontrado em venv\
    pause
    exit /b 1
)

:: Detecta branch atual
for /f "tokens=*" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set BRANCH=%%b
if "!BRANCH!"=="" (
    echo  [ERRO] Nao foi possivel detectar o branch git.
    pause
    exit /b 1
)

echo  Branch atual: !BRANCH!
echo.
echo  Arquivos modificados:
git status --short
echo.

set /p CONFIRM="  Confirma o push? (S/N): "
if /i not "!CONFIRM!"=="S" (
    echo  Cancelado.
    pause
    exit /b 0
)

:: =========================================================
::  PASSO 1 - Push de CODIGO para GitHub
:: =========================================================
echo.
echo  [1/2] Enviando codigo para GitHub...
git add -A
git commit -m "atualizacao %date%"
if errorlevel 1 (
    echo  [!] Nada novo para commitar.
)
git push origin !BRANCH!
if errorlevel 1 (
    echo  [ERRO] Falha no push para GitHub.
    pause
    exit /b 1
)
echo  [OK] GitHub atualizado.

:: =========================================================
::  PASSO 2 - Push de CODIGO para HF Spaces
:: =========================================================
echo.
echo  [2/2] Enviando codigo para HF Spaces...
git push hf !BRANCH!:main --force
if errorlevel 1 (
    echo  [ERRO] Falha no push para HF Spaces.
    pause
    exit /b 1
)
echo  [OK] HF Spaces atualizado!

echo.
echo  ========================================================
echo   Codigo publicado com sucesso!
echo.
echo   LEMBRE: para atualizar os DADOS no HF,
echo   suba os parquets manualmente no Google Drive:
echo     data\processed\vendas_filtrada.parquet
echo     data\processed\meta_semanal.parquet
echo   (use o SUBIR_DADOS_GDRIVE.bat para abrir a pasta)
echo  ========================================================
echo.
pause
endlocal
