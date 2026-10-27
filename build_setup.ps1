# Builds dist\MailGuard-Setup-<version>.exe: first the exe (PyInstaller), then the installer (Inno Setup).
# Requirements: pip install -r requirements.txt ; winget install JRSoftware.InnoSetup --scope user
Set-Location $PSScriptRoot
& .\build_exe.ps1
if (-not (Test-Path "dist\MailGuard.exe")) { Write-Host "Exe not found, build failed"; exit 1 }
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { Write-Host "Inno Setup not found: winget install JRSoftware.InnoSetup --scope user"; exit 1 }
& $iscc /Q "installer.iss"
if ($LASTEXITCODE -eq 0) { Get-ChildItem dist\MailGuard-Setup-*.exe | ForEach-Object { Write-Host "`nReady: dist\$($_.Name) ($([math]::Round($_.Length/1MB,1)) MB)" } } else { Write-Host "`nInstaller failed"; exit 1 }
