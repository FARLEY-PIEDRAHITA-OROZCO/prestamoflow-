import logging
import os
import sys
import threading
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


if __name__ == "__main__":
    log.info(f"Inicio de PrestamoFlow en {URL}")
    threading.Timer(1.2, open_browser).start()
    try:
        uvicorn.run(app, host=HOST, port=PORT, log_config=None)
    except SystemExit:
        log.info("Servidor detenido")
        sys.exit(0)