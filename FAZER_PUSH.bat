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

set PY=venv\Scripts\python.exe

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
::  PASSO 1 - Commit e push de CODIGO para GitHub
:: =========================================================
echo.
echo  [1/3] Enviando codigo para GitHub...
git add -A
git commit -m "atualizacao %date%"
if errorlevel 1 (
    echo  [!] Nada novo para commitar no codigo.
)
git push origin !BRANCH!
if errorlevel 1 (
    echo  [ERRO] Falha no push para GitHub.
    pause
    exit /b 1
)
echo  [OK] GitHub atualizado.

:: =========================================================
::  PASSO 2 - Envia os DADOS para HF via API
::  Feito ANTES do git push para que o rebuild ja encontre
::  os parquets prontos quando o Space reiniciar
:: =========================================================
echo.
echo  [2/3] Enviando dados para HF Spaces (API upload)...
echo         Isso pode demorar alguns minutos...
echo.
%PY% scripts\upload_dados_hf.py
if errorlevel 1 (
    echo  [ERRO] Falha no upload dos dados para HF.
    pause
    exit /b 1
)

:: =========================================================
::  PASSO 3 - Push de CODIGO para HF (dispara o rebuild)
::  Os dados ja estao la -- o rebuild vai encontra-los
:: =========================================================
echo.
echo  [3/3] Enviando codigo para HF Spaces (dispara rebuild)...
git push hf !BRANCH!:main --force
if errorlevel 1 (
    echo  [ERRO] Falha no push de codigo para HF.
    pause
    exit /b 1
)
echo  [OK] HF Spaces atualizado - rebuild iniciado com dados prontos!

echo.
echo  ========================================================
echo   Tudo pronto!
echo   - Codigo atualizado no GitHub
echo   - Dados enviados ao HF antes do rebuild
echo   - Rebuild disparado - dashboard atualizado em ~1 min
echo  ========================================================
echo.
pause
endlocal
