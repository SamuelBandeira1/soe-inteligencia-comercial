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
    pause
    exit /b 1
)

echo  Branch atual: !BRANCH!
echo.
echo  Arquivos de codigo modificados:
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
echo  [1/3] Commitando e enviando codigo para GitHub...
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
::  PASSO 2 - Commit de CODIGO + DADOS para HF Spaces
::  Forcamos os parquets que estao no .gitignore
:: =========================================================
echo.
echo  [2/3] Preparando dados para HF Spaces...

if not exist "data\processed\vendas_filtrada.parquet" (
    echo  [ERRO] vendas_filtrada.parquet nao encontrado.
    echo  Rode o ATUALIZAR_E_RODAR.bat primeiro.
    pause
    exit /b 1
)

git add -f data\processed\vendas_filtrada.parquet
if exist "data\processed\meta_semanal.parquet" (
    git add -f data\processed\meta_semanal.parquet
)
if exist "data\processed\vendas_unificada.parquet" (
    git add -f data\processed\vendas_unificada.parquet
)

git commit -m "dados atualizados %date%"

echo  Enviando para HF Spaces (main)...
git push hf !BRANCH!:main
if errorlevel 1 (
    echo  [ERRO] Falha no push para HF Spaces.
    :: Desfaz o commit de dados antes de sair
    git reset HEAD~1
    pause
    exit /b 1
)
echo  [OK] HF Spaces atualizado - rebuild iniciado!

:: =========================================================
::  PASSO 3 - Desfaz o commit de dados localmente
::  Os parquets voltam a ser ignorados pelo .gitignore
::  O GitHub nao recebe os dados em hipotese alguma
:: =========================================================
echo.
echo  [3/3] Limpando commit de dados do historico local...
git reset HEAD~1
echo  [OK] Historico local limpo. Dados nao foram para o GitHub.

echo.
echo  ========================================================
echo   Tudo pronto!
echo   - Codigo atualizado no GitHub
echo   - Codigo + Dados atualizados no HF Spaces
echo   - Rebuild do dashboard iniciado
echo  ========================================================
echo.
pause
endlocal
