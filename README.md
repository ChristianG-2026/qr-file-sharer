# QR File Sharer

A small Windows-friendly Python app for sharing a local file through a QR code.

The app starts a tiny HTTP server on your computer and shows a QR code that points to the selected file. It does not upload your file to an external service.

## Features

- GUI for selecting a file and generating a QR code
- Local WLAN sharing via your local IP
- Optional public-IP mode for internet sharing
- Server log popup with copy and clear actions
- Custom app icon
- No cloud upload

## Screenshots

The app icon:

![QR File Sharer icon](assets/qr_file_sharer_icon.png)

## Requirements

- Python 3.11 or newer
- Windows recommended for the packaged EXE

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run From Source

```powershell
python qr_file_sharer_gui.py
```

## Build EXE

```powershell
.\build_exe.ps1
```

The EXE will be created in `dist/`.

## Internet / Public IP Mode

The public-IP mode does not upload files. It creates a QR link using your public IP address.

For people outside your WLAN to access the file, your router and Windows Firewall must allow traffic to the selected port, for example port `8000`.

## Notes

- Keep the app open while sharing. Closing it stops the server.
- Anyone who can access the generated URL can download the selected file.
- The generated QR code is shown in the app only and is not saved automatically.

## License

MIT
