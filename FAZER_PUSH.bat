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
::  (dados ficam fora pelo .gitignore)
:: =========================================================
echo.
echo  [1/2] Enviando codigo para GitHub...
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
::  PASSO 2 - Envia CODIGO via git + DADOS via API para HF
::  Parquets sao grandes demais para git normal (>10 MB)
::  O script extrai o token automaticamente do remote 'hf'
:: =========================================================
echo.
echo  [2/2] Enviando para HF Spaces...
echo.

echo    [2a] Codigo (git push)...
git push hf !BRANCH!:main
if errorlevel 1 (
    echo  [ERRO] Falha no push de codigo para HF.
    pause
    exit /b 1
)
echo    [OK] Codigo enviado.

echo.
echo    [2b] Dados (API upload - pode demorar)...
%PY% scripts\upload_dados_hf.py
if errorlevel 1 (
    echo  [ERRO] Falha no upload dos dados para HF.
    pause
    exit /b 1
)

echo.
echo  ========================================================
echo   Tudo pronto!
echo   - Codigo atualizado no GitHub
echo   - Codigo + Dados atualizados no HF Spaces
echo   - Dashboard sera reiniciado automaticamente
echo  ========================================================
echo.
pause
endlocal
