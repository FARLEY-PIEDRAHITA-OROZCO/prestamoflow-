import json
import logging
import os
import socket
import sys
import threading
import urllib.request
import webbrowser

import uvicorn

from core import data_dir
import main as app_main

app = app_main.app

HOST = "127.0.0.1"
PORT = int(os.environ.get("PRESTAMOS_PORT", "8001"))
URL = f"http://{HOST}:{PORT}"

LOG_FILE = data_dir() / "prestamosflow.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("prestamoflow")


def open_browser():
    try:
        webbrowser.open(URL)
    except Exception:
        log.exception("No se pudo abrir el navegador")


def app_already_running() -> bool:
    """True si en el puerto ya responde otra instancia de PrestamoFlow."""
    try:
        with urllib.request.urlopen(URL + "/api/health", timeout=1.0) as resp:
            data = json.loads(resp.read(512).decode("utf-8", "replace"))
            return resp.status == 200 and data.get("status") == "ok"
    except Exception:
        return False


def port_in_use() -> bool:
    """True si el puerto esta ocupado por algun proceso (cualquiera)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.connect((HOST, PORT))
            return True
        except OSError:
            return False


def alert(title: str, message: str):
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        pass


if __name__ == "__main__":
    if app_already_running():
        log.info(f"PrestamoFlow ya esta en ejecucion en {URL}; abriendo el navegador")
        open_browser()
        sys.exit(0)

    if port_in_use():
        msg = (
            f"El puerto {PORT} esta ocupado por otra aplicacion.\n\n"
            "Cierrala, o ejecuta PrestamoFlow con PRESTAMOS_PORT=<otro puerto> "
            f"y abre http://127.0.0.1:<otro puerto> en el navegador."
        )
        log.warning(msg)
        alert("PrestamoFlow", msg)
        sys.exit(1)

    log.info(f"Inicio de PrestamoFlow en {URL}")
    threading.Timer(1.2, open_browser).start()
    try:
        uvicorn.run(app, host=HOST, port=PORT, log_config=None)
    except SystemExit:
        log.info("Servidor detenido")
        sys.exit(0)