# PrestamoFlow — Backend

API REST en FastAPI + SQLite. Préstamos personales con intereses, pagos (editar/anular), mora, auditoría y respaldo.

La documentación completa del sistema está en [`../README.md`](../README.md).

## Arranque rápido (desarrollo)

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --port 8001
```

- API: `http://127.0.0.1:8001`
- Docs interactivas: `http://127.0.0.1:8001/docs`
- Healthcheck: `http://127.0.0.1:8001/api/health`

Para la versión de escritorio sin Python/Node: compilar el frontend (`npm run
build` en `frontend/`) y empaquetar con `pyinstaller PrestamoFlow.spec`. El
resultado es `dist/PrestamoFlow/PrestamoFlow.exe`, que sirve la API y la
interfaz en un solo proceso (ver README principal).

## Tests

```
.venv\Scripts\python.exe -m pytest -q
```

## Módulos

- `main.py` — crea la app, monta los routers y sirve la SPA compilada (`/assets` + `/`).
- `serve.py` — arranque standalone (modo escritorio): uvicorn embebido, abre el navegador y registra en `prestamosflow.log`. Puerto configurable con `PRESTAMOS_PORT`.
- `core.py` — app FastAPI, conexión a SQLite, rutas de datos estables (`data_dir`), modelos Pydantic, JWT, bcrypt, rate limiting, migraciones y respaldo diario.
- `routers/auth.py` — autenticación y recuperación de acceso.
- `routers/catalog.py` — dashboard, personas, préstamos, pagos, auditoría y backup.
- `PrestamoFlow.spec` — spec PyInstaller para empaquetar la app con el frontend incluido.
- `tests/` — suite pytest (usa una base temporal).

## Datos

En desarrollo los datos se guardan en este directorio (`prestamos.db`, `.secret`,
`backups/`). Cuando se ejecuta el ejecutable compilado, se guardan **junto al
ejecutable**.