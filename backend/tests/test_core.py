from datetime import date

from conftest import mgr


def test_interes_total_saldo(client, au):
    pid = mgr(client, au, "Carlos")
    r = client.post("/api/prestamos", json={"persona_id": pid, "monto": 1_000_000, "tasa": 20}, headers=au)
    assert r.status_code == 201, r.text
    lid = r.json()["id"]

    rows = client.get("/api/prestamos", headers=au).json()
    loan = next(x for x in rows if x["id"] == lid)
    assert loan["amount"] == 1_000_000
    assert loan["interest"] == 200_000
    assert loan["total"] == 1_200_000
    assert loan["paid"] == 0
    assert loan["balance"] == 1_200_000

    r = client.post("/api/pagos", json={"prestamo_id": lid, "monto": 500_000}, headers=au)
    assert r.status_code == 201 and r.json()["balance"] == 700_000, r.text

    r = client.post("/api/pagos", json={"prestamo_id": lid, "monto": 700_000}, headers=au)
    assert r.status_code == 201 and r.json()["balance"] == 0

    loan = next(x for x in client.get("/api/prestamos", headers=au).json() if x["id"] == lid)
    assert loan["balance"] == 0 and loan["paid"] == 1_200_000


def test_pago_excede_saldo(client, au):
    pid = mgr(client, au, "Ana")
    lid = client.post("/api/prestamos", json={"persona_id": pid, "monto": 100_000, "tasa": 0}, headers=au).json()["id"]
    r = client.post("/api/pagos", json={"prestamo_id": lid, "monto": 150_000}, headers=au)
    assert r.status_code == 400


def test_exactitud_centavos(client, au):
    pid = mgr(client, au, "Beto")
    monto = 123_456.78
    lid = client.post("/api/prestamos", json={"persona_id": pid, "monto": monto}, headers=au).json()["id"]
    r = client.post("/api/pagos", json={"prestamo_id": lid, "monto": monto}, headers=au)
    assert r.status_code == 201 and r.json()["balance"] == 0.0, r.text
    loan = next(x for x in client.get("/api/prestamos", headers=au).json() if x["id"] == lid)
    assert loan["balance"] == 0.0 and loan["paid"] == 123_456.78


def test_interes_decimal_redondeado(client, au):
    pid = mgr(client, au, "Dani")
    lid = client.post("/api/prestamos", json={"persona_id": pid, "monto": 100_000, "tasa": 12.5}, headers=au).json()["id"]
    loan = next(x for x in client.get("/api/prestamos", headers=au).json() if x["id"] == lid)
    assert loan["interest"] == 12_500 and loan["total"] == 112_500


def test_tasa_maxima_validada(client, au):
    pid = mgr(client, au, "Eli")
    r = client.post("/api/prestamos", json={"persona_id": pid, "monto": 10_000, "tasa": 150}, headers=au)
    assert r.status_code == 422


def test_dashboard_global(client, au):
    pid = mgr(client, au, "Fer")
    lid = client.post("/api/prestamos", json={"persona_id": pid, "monto": 1_000_000, "tasa": 10}, headers=au).json()["id"]
    client.post("/api/pagos", json={"prestamo_id": lid, "monto": 200_000}, headers=au)
    d = client.get("/api/dashboard", headers=au).json()
    assert d["total_lent"] == 1_000_000
    assert d["total_interest"] == 100_000
    assert d["total_paid"] == 200_000
    assert d["total_balance"] == 900_000
    assert d["active_loans"] == 1 and d["people"] == 1


def test_esquema_migrado_a_centavos(client, au):
    pid = mgr(client, au, "Gus")
    client.post("/api/prestamos", json={"persona_id": pid, "monto": 5.5}, headers=au)
    c = __import__("core").db()
    monto = c.execute("SELECT monto FROM prestamos").fetchone()["monto"]
    ver = c.execute("PRAGMA user_version").fetchone()[0]
    c.close()
    assert ver >= 3
    assert monto == 550


def test_anular_pago_recupera_saldo(client, au):
    pid = mgr(client, au, "Ida")
    lid = client.post("/api/prestamos", json={"persona_id": pid, "monto": 100_000, "tasa": 0}, headers=au).json()["id"]
    p1 = client.post("/api/pagos", json={"prestamo_id": lid, "monto": 40_000}, headers=au).json()["id"]
    p2 = client.post("/api/pagos", json={"prestamo_id": lid, "monto": 30_000}, headers=au).json()["id"]

    r = client.post(f"/api/pagos/{p1}/anular", headers=au)
    assert r.status_code == 200, r.text

    loan = next(x for x in client.get("/api/prestamos", headers=au).json() if x["id"] == lid)
    assert loan["paid"] == 30_000 and loan["balance"] == 70_000

    hist = {x["id"] for x in client.get(f"/api/prestamos/{lid}/pagos", headers=au).json()}
    assert p1 not in hist and p2 in hist

    r = client.post(f"/api/pagos/{p1}/anular", headers=au)
    assert r.status_code == 404

    c = __import__("core").db()
    accion = c.execute("SELECT accion FROM auditoria WHERE accion='anular_pago'").fetchone()
    c.close()
    assert accion


def test_auditoria_endpoint(client, au):
    mgr(client, au, "Juli")
    rows = client.get("/api/auditoria", headers=au).json()
    assert rows and rows[0]["accion"] == "crear_persona"
    assert all("created_at" in r and "usuario" in r for r in rows)
    assert client.get("/api/auditoria").status_code == 401


def test_vencimiento_y_mora(client, au):
    from datetime import date, timedelta
    pid = mgr(client, au, "Kevin")
    pasado = (date.today() - timedelta(days=5)).isoformat()
    futuro = (date.today() + timedelta(days=10)).isoformat()
    l1 = client.post("/api/prestamos", json={"persona_id": pid, "monto": 100_000, "vencimiento": pasado}, headers=au).json()["id"]
    l2 = client.post("/api/prestamos", json={"persona_id": pid, "monto": 100_000, "vencimiento": futuro}, headers=au).json()["id"]

    loans = {x["id"]: x for x in client.get("/api/prestamos", headers=au).json()}
    assert loans[l1]["mora_dias"] == 5 and loans[l1]["vencimiento"] == pasado
    assert loans[l2]["mora_dias"] == 0

    assert {x["id"] for x in client.get("/api/prestamos?estado=mora", headers=au).json()} == {l1}
    assert {x["id"] for x in client.get("/api/prestamos?estado=en_curso", headers=au).json()} == {l2}

    client.post("/api/pagos", json={"prestamo_id": l1, "monto": 100_000}, headers=au)
    loans = {x["id"]: x for x in client.get("/api/prestamos", headers=au).json()}
    assert loans[l1]["mora_dias"] == 0
    assert client.get("/api/dashboard", headers=au).json()["in_mora"] == 0

    r = client.post("/api/prestamos", json={"persona_id": pid, "monto": 10_000, "vencimiento": "31-12-2026"}, headers=au)
    assert r.status_code == 400


def test_backup_db(client, au):
    mgr(client, au, "Backup")
    r = client.get("/api/backup", headers=au)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/x-sqlite3")
    assert r.content[:16] == b"SQLite format 3\x00"
    assert client.get("/api/backup").status_code == 401


def test_editar_pago(client, au):
    pid = mgr(client, au, "Leo")
    lid = client.post("/api/prestamos", json={"persona_id": pid, "monto": 100_000, "tasa": 0}, headers=au).json()["id"]
    pid_pago = client.post("/api/pagos", json={"prestamo_id": lid, "monto": 40_000}, headers=au).json()["id"]
    client.post("/api/pagos", json={"prestamo_id": lid, "monto": 30_000}, headers=au)

    r = client.put(f"/api/pagos/{pid_pago}", json={"monto": 50_000, "fecha": "2026-09-10"}, headers=au)
    assert r.status_code == 200, r.text
    assert r.json()["monto"] == 50_000 and r.json()["fecha"] == "2026-09-10"

    loan = next(x for x in client.get("/api/prestamos", headers=au).json() if x["id"] == lid)
    assert loan["paid"] == 80_000 and loan["balance"] == 20_000

    hist = {x["id"]: x for x in client.get(f"/api/prestamos/{lid}/pagos", headers=au).json()}
    assert hist[pid_pago]["monto"] == 50_000 and hist[pid_pago]["fecha"] == "2026-09-10"

    r = client.put(f"/api/pagos/{pid_pago}", json={"monto": 100_000}, headers=au)
    assert r.status_code == 400

    client.post(f"/api/pagos/{pid_pago}/anular", headers=au)
    r = client.put(f"/api/pagos/{pid_pago}", json={"monto": 5_000}, headers=au)
    assert r.status_code == 404

    c = __import__("core").db()
    accion = c.execute("SELECT accion FROM auditoria WHERE accion='editar_pago'").fetchone()
    c.close()
    assert accion
