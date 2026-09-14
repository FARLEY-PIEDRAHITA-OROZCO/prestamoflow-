# PrestamoFlow — Backend

API REST en FastAPI + SQLite. Préstamos personales con intereses, pagos (editar/anular), mora, auditoría y respaldo.

La documentación completa del sistema está en [`../README.md`](../README.md).

## Arranque rápido

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

## Tests

```
.venv\Scripts\python.exe -m pytest -q
```

## Módulos

- `main.py` — crea la app y monta los routers.
- `core.py` — app FastAPI, conexión a SQLite, modelos Pydantic, JWT, bcrypt, rate limiting, migraciones y respaldo diario.
- `routers/auth.py` — autenticación y recuperación de acceso.
- `routers/catalog.py` — dashboard, personas, préstamos, pagos, auditoría y backup.
- `tests/` — suite pytest (usa una base temporal).