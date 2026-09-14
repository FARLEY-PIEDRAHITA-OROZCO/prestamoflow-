import json, re, sys, threading, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from core import data_dir

router = APIRouter(prefix="/api", tags=["updates"])

REPO = "FARLEY-PIEDRAHITA-OROZCO/prestamoflow-"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
CACHE_TTL = timedelta(hours=6)

_cache = {"at": None, "data": None}
_downloading = False
_lock = threading.Lock()


def current_version():
    """Versión de la app. En el bundle se lee de 'version.txt' (incluido en el
    build por PrestamoFlow.spec); en desarrollo devuelve 'dev' (sin avisos)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    try:
        v = Path(base, "version.txt").read_text(encoding="utf-8").strip()
        return v or "dev"
    except OSError:
        return "dev"


def _semver(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v).lstrip("v"))[:3]) or (0,)


def fetch_latest():
    """Consulta la release 'latest' del repositorio (sin autenticación, con
    caché de 6 h). Devuelve tag, html_url y la URL del instalador .exe."""
    now = datetime.now(timezone.utc)
    with _lock:
        if _cache["data"] and _cache["at"] and now - _cache["at"] < CACHE_TTL:
            return _cache["data"]
    data = {"tag": "", "url": "", "html_url": ""}
    try:
        req = urllib.request.Request(
            LATEST_URL,
            headers={"User-Agent": "PrestamoFlow", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            body = json.load(r)
        data["tag"] = str(body.get("tag_name", ""))
        data["html_url"] = str(body.get("html_url", ""))
        for a in body.get("assets", []):
            name = str(a.get("name", ""))
            if name.startswith("PrestamoFlow-Setup-") and name.endswith(".exe"):
                data["url"] = str(a.get("browser_download_url", ""))
                break
    except (OSError, ValueError):
        pass
    with _lock:
        _cache.update(at=now, data=data)
    return data


@router.get("/updates")
def updates():
    v = current_version()
    latest = fetch_latest()
    newer = bool(latest["tag"] and v != "dev" and _semver(latest["tag"]) > _semver(v))
    return {
        "version": v,
        "latest": latest["tag"],
        "update": newer,
        "url": latest["url"] if newer else "",
        "html_url": latest["html_url"] if newer else "",
        "downloading": _downloading,
    }


@router.post("/updates/download")
def download():
    global _downloading
    if _downloading:
        raise HTTPException(409, "Una descarga ya está en curso")
    latest = fetch_latest()
    url = latest["url"]
    if not url:
        raise HTTPException(409, "El instalador de la nueva versión aún no está publicado")
    if not url.startswith("https://") or not url.lower().endswith(".exe"):
        raise HTTPException(409, "Dirección de descarga no válida")
    target_dir = data_dir() / "updates"
    try:
        target_dir.mkdir(exist_ok=True)
    except OSError:
        raise HTTPException(500, "No se pudo crear la carpeta de descargas")
    name = url.split("/")[-1]
    _downloading = True
    threading.Thread(target=_worker, args=(url, target_dir / name, name), daemon=True).start()
    return {"ok": True, "file": name}


def _worker(url, target, name):
    global _downloading
    import subprocess
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PrestamoFlow"})
        with urllib.request.urlopen(req, timeout=600) as r, open(target, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        subprocess.Popen([str(target)], cwd=str(target.parent))
    except (OSError, ValueError):
        pass
    finally:
        with _lock:
            _downloading = False