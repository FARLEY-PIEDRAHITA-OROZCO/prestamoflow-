from conftest import mgr


def _reg(client):
    return client.post("/api/auth/registro", json={
        "usuario": "user", "nombre": "Usuario", "password": "clave1234",
    })


def test_registro_login_recuperacion(client):
    r = _reg(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["recovery"]
    token = body["token"]

    h = {"Authorization": "Bearer " + token}
    assert client.get("/api/auth/mi", headers=h).json()["usuario"] == "user"

    assert client.get("/api/personas").status_code == 401

    r = client.post("/api/auth/login", json={"usuario": "user", "password": "clave1234"})
    assert r.status_code == 200
    assert client.post("/api/auth/login", json={"usuario": "user", "password": "mal"}).status_code == 401

    r = client.post("/api/auth/cambiar_password", json={"actual": "clave1234", "nueva": "nueva1234"}, headers=h)
    assert r.status_code == 200
    assert client.post("/api/auth/login", json={"usuario": "user", "password": "nueva1234"}).status_code == 200
    assert client.post("/api/auth/login", json={"usuario": "user", "password": "clave1234"}).status_code == 401


def test_recuperacion_flujo_completo(client):
    body = _reg(client).json()
    rec = body["recovery"]

    r = client.post("/api/auth/olvide_password", json={
        "usuario": "user", "codigo": rec, "nueva": "restaurada1",
    })
    assert r.status_code == 200, r.text
    assert client.post("/api/auth/login", json={"usuario": "user", "password": "restaurada1"}).status_code == 200

    # la clave queda invalidada tras su uso
    r = client.post("/api/auth/olvide_password", json={
        "usuario": "user", "codigo": rec, "nueva": "otra12345",
    })
    assert r.status_code == 401
    assert client.post("/api/auth/login", json={"usuario": "user", "password": "otra12345"}).status_code == 401


def test_recuperacion_respuesta_uniforme(client):
    rec = _reg(client).json()["recovery"]
    a = client.post("/api/auth/olvide_password", json={"usuario": "user", "codigo": "ZZZZ-ZZZZ-ZZZZ", "nueva": "nueva1234"}).status_code
    b = client.post("/api/auth/olvide_password", json={"usuario": "inexistente", "codigo": rec, "nueva": "nueva1234"}).status_code
    assert a == 401 and b == 401


def test_politica_password_minimo(client):
    r = client.post("/api/auth/registro", json={"usuario": "short", "nombre": "X", "password": "12345"})
    assert r.status_code == 422
    r = client.post("/api/auth/registro", json={"usuario": "user2", "nombre": "X", "password": "12345678"})
    assert r.status_code == 201


def test_solo_primera_cuenta(client):
    assert _reg(client).status_code == 201
    r = _reg(client)
    assert r.status_code == 403


def test_auditoria_registra_eventos(client, au):
    pid = mgr(client, au, "Hugo")
    client.post("/api/personas", json={"nombre": "Otro"}, headers=au)
    client.post("/api/auth/login", json={"usuario": "admin", "password": "clave1234"})
    client.post("/api/auth/login", json={"usuario": "admin", "password": "mala"})

    c = __import__("core").db()
    acciones = {r["accion"] for r in c.execute("SELECT accion FROM auditoria").fetchall()}
    c.close()
    assert {"registro", "crear_persona", "login", "login_fallido"}.issubset(acciones)
