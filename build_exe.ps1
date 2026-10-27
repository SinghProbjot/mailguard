# Builds dist\MailGuard.exe (single file). Run from the repository root:  .\build_exe.ps1
Set-Location $PSScriptRoot
python -c "from mailguard.make_icon import make; make()"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name MailGuard `
  --icon "mailguard\assets\icon.ico" `
  --add-data "mailguard\config.default.json;mailguard" `
  --add-data "mailguard\assets\icon.png;mailguard\assets" `
  --collect-data tldextract `
  --hidden-import pystray._win32 --hidden-import win32timezone --hidden-import winotify `
  --exclude-module laya --exclude-module torch --exclude-module transformers `
  MailGuard.py
if ($LASTEXITCODE -eq 0) { Write-Host "`nReady: dist\MailGuard.exe" } else { Write-Host "`nBuild failed" }
