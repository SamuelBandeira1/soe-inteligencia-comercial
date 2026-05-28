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

:: Detecta branch atual
for /f "tokens=*" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set BRANCH=%%b
if "!BRANCH!"=="" (
    echo  [ERRO] Nao foi possivel detectar o branch git.
    echo  Verifique se esta dentro de um repositorio git.
    pause
    exit /b 1
)

echo  Branch atual: !BRANCH!
echo.

:: Mostra o que sera commitado
echo  Arquivos modificados:
git status --short
echo.

set /p CONFIRM="  Confirma o push? (S/N): "
if /i not "!CONFIRM!"=="S" (
    echo.
    echo  Cancelado.
    pause
    exit /b 0
)

:: Commit
echo.
echo  [1/3] Commitando alteracoes...
git add -A
git commit -m "atualizacao %date%"
if errorlevel 1 (
    echo  [!] Nada novo para commitar - ja esta atualizado.
)

:: Push GitHub
echo.
echo  [2/3] Enviando para GitHub (!BRANCH!)...
git push origin !BRANCH!
if errorlevel 1 (
    echo  [ERRO] Falha no push para GitHub.
    pause
    exit /b 1
) else (
    echo  [OK] GitHub atualizado.
)

:: Push HF Spaces
echo.
echo  [3/3] Enviando para HF Spaces (main)...
git push hf !BRANCH!:main
if errorlevel 1 (
    echo  [ERRO] Falha no push para HF Spaces.
    pause
    exit /b 1
) else (
    echo  [OK] HF Spaces atualizado - rebuild iniciado!
)

echo.
echo  ========================================================
echo   Versao publicada com sucesso!
echo  ========================================================
echo.
pause
endlocal
