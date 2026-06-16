$ErrorActionPreference = "Stop"

py -3.12 -m pip install -r requirements-dev.txt

py -3.12 -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --collect-all tkinterdnd2 `
  --icon "qr_file_sharer_icon.ico" `
  --add-data "qr_file_sharer_icon.ico;." `
  --name "QR File Sharer" `
  "qr_file_sharer_gui.py"

Write-Host "Build complete: dist\QR File Sharer.exe"
