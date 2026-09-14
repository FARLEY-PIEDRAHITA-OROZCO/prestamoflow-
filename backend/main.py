from core import app
from routers import auth, catalog

app.include_router(auth.router)
app.include_router(catalog.router)