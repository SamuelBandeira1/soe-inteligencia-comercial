# Cria atalhos na Área de Trabalho para o sistema S&OE
# Execute uma vez: .\venv\Scripts\python.exe -c "import subprocess; subprocess.run(['powershell', '-File', 'scripts/criar_atalhos_desktop.ps1'])"

$desktop   = [System.Environment]::GetFolderPath("Desktop")
$projetoDir = Split-Path -Parent $PSScriptRoot
$wsh       = New-Object -ComObject WScript.Shell

# ── Atalho 1: Atualizar Dados + Rodar ────────────────────────────────────────
$atalho1 = $wsh.CreateShortcut("$desktop\🔄 SOE — Atualizar e Rodar.lnk")
$atalho1.TargetPath       = "$projetoDir\ATUALIZAR_E_RODAR.bat"
$atalho1.WorkingDirectory = $projetoDir
$atalho1.Description      = "Processa novos dados CSV e inicia o Dashboard S&OE"
$atalho1.WindowStyle      = 1
$atalho1.Save()
Write-Host "✅ Atalho criado: Área de Trabalho\🔄 SOE — Atualizar e Rodar"

# ── Atalho 2: Só o Dashboard ──────────────────────────────────────────────────
$atalho2 = $wsh.CreateShortcut("$desktop\📊 SOE — Dashboard.lnk")
$atalho2.TargetPath       = "$projetoDir\SÓ_RODAR_DASHBOARD.bat"
$atalho2.WorkingDirectory = $projetoDir
$atalho2.Description      = "Inicia o Dashboard S&OE (sem reprocessar dados)"
$atalho2.WindowStyle      = 1
$atalho2.Save()
Write-Host "✅ Atalho criado: Área de Trabalho\📊 SOE — Dashboard"

Write-Host ""
Write-Host "Pronto! Dois atalhos criados na Área de Trabalho."
