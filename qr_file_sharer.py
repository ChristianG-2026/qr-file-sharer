#!/usr/bin/env python3
"""
QR Code File Sharer
Generates a QR code that points to a local HTTP server sharing a given file.
Usage: python qr_file_sharer.py <datei-pfad> [port]
"""

import os
import sys
import socket
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import quote

import qrcode
from qrcode.image.pil import PilImage


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def generate_qr(data: str, output_path: str, file_name: str) -> str:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return str(out)


def main():
    if len(sys.argv) < 2:
        print("Usage: python qr_file_sharer.py <datei-pfad> [port]")
        sys.exit(1)

    file_path = Path(sys.argv[1]).resolve()
    if not file_path.exists():
        print(f"Fehler: Datei nicht gefunden: {file_path}")
        sys.exit(1)

    port = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    serve_dir = file_path.parent
    file_name = file_path.name
    file_stem = file_path.stem

    os.chdir(serve_dir)

    class FileHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve_dir), **kwargs)

        def log_message(self, format, *msg):
            print(f"  [HTTP] {self.client_address[0]} - {format % msg}")

    server = HTTPServer(("0.0.0.0", port), FileHandler)
    actual_port = server.server_port
    ip = get_local_ip()
    url = f"http://{ip}:{actual_port}/{quote(file_name)}"

    qr_path = generate_qr(url, str(serve_dir / f"{file_stem}_qr.png"), file_name)

    print(f"\n  Datei:     {file_name}")
    print(f"  Größe:     {file_path.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"  URL:       {url}")
    print(f"  QR-Code:   {qr_path}")
    print(f"\n  Server läuft auf Port {actual_port}")
    print("  Beenden mit Strg+C\n")

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    webbrowser.open(qr_path)

    try:
        server_thread.join()
    except KeyboardInterrupt:
        print("\n  Server gestoppt.")
        server.shutdown()


if __name__ == "__main__":
    main()
