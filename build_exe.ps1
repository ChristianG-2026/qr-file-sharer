$ErrorActionPreference = "Stop"

python -m pip install -r requirements-dev.txt

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --icon "qr_file_sharer_icon.ico" `
  --add-data "qr_file_sharer_icon.ico;." `
  --name "QR File Sharer" `
  "qr_file_sharer_gui.py"

Write-Host "Build complete: dist\QR File Sharer.exe"
