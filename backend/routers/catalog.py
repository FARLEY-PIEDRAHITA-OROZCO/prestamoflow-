import os, sqlite3, tempfile
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from core import (db, pesos, aud, current_user,
                  PersonaIn, PrestamoIn, PagoIn, EditarPagoIn)

router = APIRouter(prefix="/api", tags=["catalog"])


# ---------- dashboard ----------
@router.get("/dashboard")
def dashboard(user=Depends(current_user)):
    c = db()
    rows = c.execute("""SELECT p.monto monto_c,p.tasa,p.vencimiento,
      COALESCE((SELECT SUM(pa.monto) FROM pagos pa WHERE pa.prestamo_id=p.id AND pa.activo=1),0) pagado_c
      FROM prestamos p""").fetchall()
    lent_c = sum(r["monto_c"] for r in rows)
    interest_c = sum(int(round(r["monto_c"] * r["tasa"] / 100)) for r in rows)
    paid_c = c.execute("SELECT COALESCE(SUM(monto),0)v FROM pagos WHERE activo=1").fetchone()["v"]
    active = 0
    in_mora = 0
    hoy = date.today()
    for r in rows:
        if r["monto_c"] + int(round(r["monto_c"]*r["tasa"]/100)) - r["pagado_c"] > 0:
            active += 1
            if r["vencimiento"]:
                try:
                    if date.fromisoformat(r["vencimiento"]) < hoy:
                        in_mora += 1
                except ValueError:
                    pass
    people = c.execute("SELECT COUNT(*)v FROM personas WHERE activa=1").fetchone()["v"]
    c.close()
    return {"total_lent": pesos(lent_c), "total_interest": pesos(interest_c), "total_paid": pesos(paid_c),
            "total_balance": pesos(sum(max(0, r["monto_c"] + int(round(r["monto_c"]*r["tasa"]/100)) - r["pagado_c"]) for r in rows)),
            "active_loans": active, "in_mora": in_mora, "people": people}


# ---------- personas ----------
@router.get("/personas")
def personas(incluir_archivadas: bool = False, user=Depends(current_user)):
    c = db()
    sql = "SELECT id,nombre,created_at,activa FROM personas"
    if not incluir_archivadas:
        sql += " WHERE activa=1"
    rows = c.execute(sql + " ORDER BY nombre").fetchall()
    c.close()
    return [{"id": x["id"], "nombre": x["nombre"], "created_at": x["created_at"],
             "activa": bool(x["activa"])} for x in rows]


@router.post("/personas", status_code=201)
def crear_persona(x: PersonaIn, user=Depends(current_user)):
    name = x.nombre.strip()
    if not name:
        raise HTTPException(400, "El nombre es obligatorio")
    c = db()
    cur = c.execute("INSERT INTO personas(nombre,created_at) VALUES(?,?)",
                    (name, datetime.now().isoformat(timespec="seconds")))
    aud(c, user["usuario"], "crear_persona", f"{name} (id {cur.lastrowid})")
    c.commit()
    out = {"id": cur.lastrowid, "nombre": name}
    c.close()
    return out


@router.put("/personas/{id}")
def editar_persona(id: int, x: PersonaIn, user=Depends(current_user)):
    name = x.nombre.strip()
    if not name:
        raise HTTPException(400, "El nombre es obligatorio")
    c = db()
    old = c.execute("SELECT nombre FROM personas WHERE id=?", (id,)).fetchone()
    cur = c.execute("UPDATE personas SET nombre=? WHERE id=?", (name, id))
    if cur.rowcount == 0:
        c.close(); raise HTTPException(404, "La persona no existe")
    aud(c, user["usuario"], "editar_persona", f"{old['nombre']} -> {name} (id {id})")
    c.commit(); c.close()
    return {"id": id, "nombre": name}


@router.delete("/personas/{id}")
def archivar_persona(id: int, user=Depends(current_user)):
    c = db()
    n = c.execute("""SELECT COUNT(*)v FROM prestamos p WHERE p.persona_id=? AND p.monto+CAST(ROUND(p.monto*p.tasa/100) AS INTEGER)>
      COALESCE((SELECT SUM(pa.monto) FROM pagos pa WHERE pa.prestamo_id=p.id AND pa.activo=1),0)""", (id,)).fetchone()["v"]
    if n:
        c.close(); raise HTTPException(400,
            f"No se puede archivar: la persona tiene {n} préstamo(s) pendiente(s) de pago")
    row = c.execute("SELECT nombre FROM personas WHERE id=? AND activa=1", (id,)).fetchone()
    cur = c.execute("UPDATE personas SET activa=0 WHERE id=? AND activa=1", (id,))
    if cur.rowcount == 0:
        c.close(); raise HTTPException(404, "La persona no existe o ya está archivada")
    aud(c, user["usuario"], "archivar_persona", f"{row['nombre']} (id {id})")
    c.commit(); c.close()
    return {"id": id, "activa": False}


@router.post("/personas/{id}/restaurar")
def restaurar_persona(id: int, user=Depends(current_user)):
    c = db()
    row = c.execute("SELECT nombre FROM personas WHERE id=? AND activa=0", (id,)).fetchone()
    cur = c.execute("UPDATE personas SET activa=1 WHERE id=? AND activa=0", (id,))
    if cur.rowcount == 0:
        c.close(); raise HTTPException(404, "La persona no existe o no está archivada")
    aud(c, user["usuario"], "restaurar_persona", f"{row['nombre']} (id {id})")
    c.commit(); c.close()
    return {"id": id, "activa": True}


# ---------- auditoría ----------
@router.get("/auditoria")
def auditoria(limite: int = 100, usuario: str | None = None, user=Depends(current_user)):
    c = db()
    sql = "SELECT id,usuario,accion,detalle,created_at FROM auditoria"
    params = []
    if usuario:
        sql += " WHERE usuario=?"
        params.append(usuario)
    sql += " ORDER BY id DESC LIMIT " + str(min(max(int(limite), 1), 1000))
    rows = c.execute(sql, params).fetchall()
    c.close()
    return [{"id": x["id"], "usuario": x["usuario"], "accion": x["accion"],
             "detalle": x["detalle"], "created_at": x["created_at"]} for x in rows]


@router.get("/backup")
def backup_db(user=Depends(current_user)):
    from core import db_path
    src = sqlite3.connect(db_path())
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    dst = sqlite3.connect(tmp)
    src.backup(dst)
    dst.close(); src.close()
    return FileResponse(tmp, filename=f"respaldo-prestamosflow-{date.today().isoformat()}.db",
                        media_type="application/x-sqlite3",
                        background=BackgroundTask(os.unlink, tmp))


# ---------- préstamos ----------
def _loan_view(r):
    interest_c = int(round(r["monto_c"] * r["tasa"] / 100))
    total_c = r["monto_c"] + interest_c
    paid_c = r["pagado_c"]
    mora_dias = 0
    hoy = date.today()
    if r["vencimiento"] and total_c - paid_c > 0:
        try:
            v = date.fromisoformat(r["vencimiento"])
            if v < hoy:
                mora_dias = (hoy - v).days
        except ValueError:
            pass
    return {"id": r["id"], "persona_id": r["persona_id"], "person": r["person"],
            "person_active": bool(r["active_person"]), "date": r["fecha"],
            "vencimiento": r["vencimiento"], "mora_dias": mora_dias,
            "amount": pesos(r["monto_c"]), "tasa": r["tasa"], "interest": pesos(interest_c),
            "total": pesos(total_c), "paid": pesos(paid_c),
            "balance": pesos(max(0, total_c - paid_c))}


@router.get("/prestamos")
def prestamos(estado: str = "todos", user=Depends(current_user)):
    c = db()
    rows = c.execute("""SELECT p.id,p.persona_id,pe.nombre person,pe.activa active_person,p.fecha,p.monto monto_c,p.tasa,p.vencimiento,
      COALESCE((SELECT SUM(pa.monto) FROM pagos pa WHERE pa.prestamo_id=p.id AND pa.activo=1),0) pagado_c
      FROM prestamos p JOIN personas pe ON pe.id=p.persona_id ORDER BY p.id DESC""").fetchall()
    c.close()
    view = [_loan_view(r) for r in rows]
    if estado == "mora":
        return [v for v in view if v["mora_dias"] > 0]
    if estado == "en_curso":
        return [v for v in view if v["balance"] > 0 and v["mora_dias"] == 0]
    if estado == "pagados":
        return [v for v in view if v["balance"] <= 0]
    return view


@router.post("/prestamos", status_code=201)
def crear_prestamo(x: PrestamoIn, user=Depends(current_user)):
    c = db()
    if not c.execute("SELECT 1 FROM personas WHERE id=?", (x.persona_id,)).fetchone():
        c.close(); raise HTTPException(404, "La persona no existe")
    venc = (x.vencimiento or "").strip() or None
    try:
        if venc:
            date.fromisoformat(venc)
    except ValueError:
        c.close(); raise HTTPException(400, "La fecha de vencimiento no es válida")
    monto_c = int(round(x.monto * 100))
    cur = c.execute("INSERT INTO prestamos(persona_id,fecha,monto,tasa,vencimiento) VALUES(?,?,?,?,?)",
                    (x.persona_id, datetime.now().strftime("%Y-%m-%d"), monto_c, x.tasa, venc))
    aud(c, user["usuario"], "crear_prestamo",
        f"Préstamo {cur.lastrowid} por {pesos(monto_c)} (persona {x.persona_id}, tasa {x.tasa}%)")
    c.commit(); c.close()
    return {"id": cur.lastrowid}


@router.get("/prestamos/{id}/pagos")
def pagos(id: int, user=Depends(current_user)):
    c = db()
    if not c.execute("SELECT 1 FROM prestamos WHERE id=?", (id,)).fetchone():
        c.close(); raise HTTPException(404, "Préstamo no existe")
    rows = c.execute("SELECT id,fecha,monto FROM pagos WHERE prestamo_id=? AND activo=1 ORDER BY id DESC", (id,)).fetchall()
    c.close()
    return [{"id": x["id"], "fecha": x["fecha"], "monto": pesos(x["monto"])} for x in rows]


@router.post("/pagos", status_code=201)
def crear_pago(x: PagoIn, user=Depends(current_user)):
    c = db()
    r = c.execute("""SELECT p.monto monto_c,p.tasa,COALESCE((SELECT SUM(pa.monto) FROM pagos pa
      WHERE pa.prestamo_id=p.id AND pa.activo=1),0) pagado_c FROM prestamos p WHERE p.id=?""", (x.prestamo_id,)).fetchone()
    if not r:
        c.close(); raise HTTPException(404, "Préstamo no existe")
    saldo_c = r["monto_c"] + int(round(r["monto_c"] * r["tasa"] / 100)) - r["pagado_c"]
    monto_c = int(round(x.monto * 100))
    if monto_c <= 0:
        c.close(); raise HTTPException(400, "El monto debe ser mayor que cero")
    if monto_c > saldo_c:
        c.close(); raise HTTPException(400, f"El pago supera el saldo pendiente de {pesos(saldo_c):.2f}")
    fecha = x.fecha or datetime.now().strftime("%Y-%m-%d")
    try:
        date.fromisoformat(fecha)
    except ValueError:
        c.close(); raise HTTPException(400, "La fecha del pago no es válida")
    cur = c.execute("INSERT INTO pagos(prestamo_id,fecha,monto) VALUES(?,?,?)",
                    (x.prestamo_id, fecha, monto_c))
    aud(c, user["usuario"], "crear_pago",
        f"{monto_c} centavos aplicados al préstamo {x.prestamo_id}")
    c.commit()
    out = {"id": cur.lastrowid, "balance": pesos(saldo_c - monto_c)}
    c.close()
    return out


@router.post("/pagos/{id}/anular")
def anular_pago(id: int, user=Depends(current_user)):
    c = db()
    row = c.execute("SELECT id,prestamo_id,fecha,monto FROM pagos WHERE id=? AND activo=1", (id,)).fetchone()
    if not row:
        c.close(); raise HTTPException(404, "El pago no existe o ya fue anulado")
    c.execute("UPDATE pagos SET activo=0 WHERE id=?", (id,))
    aud(c, user["usuario"], "anular_pago",
        f"Pago {id} por {pesos(row['monto'])} anulado del préstamo {row['prestamo_id']}")
    c.commit(); c.close()
    return {"id": id, "activo": False}


@router.put("/pagos/{id}")
def editar_pago(id: int, x: EditarPagoIn, user=Depends(current_user)):
    c = db()
    row = c.execute("SELECT id,prestamo_id,fecha,monto FROM pagos WHERE id=? AND activo=1", (id,)).fetchone()
    if not row:
        c.close(); raise HTTPException(404, "El pago no existe o fue anulado")
    p = c.execute("""SELECT p.monto monto_c,p.tasa,
      COALESCE((SELECT SUM(pa.monto) FROM pagos pa WHERE pa.prestamo_id=p.id AND pa.activo=1),0) pagado_c
      FROM prestamos p WHERE p.id=?""", (row["prestamo_id"],)).fetchone()
    total_c = p["monto_c"] + int(round(p["monto_c"] * p["tasa"] / 100))
    otros_c = p["pagado_c"] - row["monto"]
    nuevo_c = int(round(x.monto * 100))
    if nuevo_c <= 0:
        c.close(); raise HTTPException(400, "El monto debe ser mayor que cero")
    if nuevo_c > total_c - otros_c:
        c.close(); raise HTTPException(400,
            "El nuevo monto excede el saldo pendiente del préstamo "
            f"({pesos(total_c - otros_c):.2f})")
    cambios = []
    if nuevo_c != row["monto"]:
        cambios.append(f"monto {pesos(row['monto'])} -> {pesos(nuevo_c)}")
    nueva_fecha = (x.fecha or "").strip() or row["fecha"]
    try:
        date.fromisoformat(nueva_fecha)
    except ValueError:
        c.close(); raise HTTPException(400, "La fecha no es válida")
    if nueva_fecha != row["fecha"]:
        cambios.append(f"fecha {row['fecha']} -> {nueva_fecha}")
    c.execute("UPDATE pagos SET monto=?, fecha=? WHERE id=?", (nuevo_c, nueva_fecha, id))
    if cambios:
        aud(c, user["usuario"], "editar_pago",
            f"Pago {id} (préstamo {row['prestamo_id']}): " + ", ".join(cambios))
    c.commit(); c.close()
    return {"id": id, "monto": pesos(nuevo_c), "fecha": nueva_fecha}