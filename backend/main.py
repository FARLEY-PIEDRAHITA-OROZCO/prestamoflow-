from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core import app, frontend_dist
from routers import auth, catalog

app.include_router(auth.router)
app.include_router(catalog.router)

_dist = frontend_dist()
if (_dist / "index.html").exists():
    if (_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        return FileResponse(_dist / "index.html")