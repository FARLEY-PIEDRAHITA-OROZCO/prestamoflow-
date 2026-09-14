import os, sys, tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ["PRESTAMOS_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")

import main  # noqa: E402
import core  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    core._rate.clear()
    yield
    c = core.db()
    for t in ("pagos", "prestamos", "personas", "auditoria", "usuarios"):
        c.execute(f"DELETE FROM {t}")
    c.commit()
    c.close()


@pytest.fixture
def client():
    with TestClient(main.app) as tc:
        yield tc


@pytest.fixture
def au(client):
    """Cliente autenticado: registra la primera cuenta y devuelve headers de token."""
    r = client.post("/api/auth/registro", json={
        "usuario": "admin", "nombre": "Admin Test", "password": "clave1234",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def mgr(client, au, nombre):
    r = client.post("/api/personas", json={"nombre": nombre}, headers=au)
    assert r.status_code == 201, r.text
    return r.json()["id"]