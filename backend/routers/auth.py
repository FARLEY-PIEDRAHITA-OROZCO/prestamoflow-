import bcrypt
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request

from core import (db, aud, check_rate, gen_recovery, hash_recovery, make_token,
                  current_user, TOKEN_HORAS, RegIn, AuthIn, PassIn, RecoveryIn)

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/auth/estado")
def estado():
    c = db()
    n = c.execute("SELECT COUNT(*)v FROM usuarios").fetchone()["v"]
    c.close()
    return {"tiene_usuarios": n > 0}


@router.post("/auth/registro", status_code=201)
def registro(x: RegIn, request: Request):
    check_rate("registro", request)
    c = db()
    if c.execute("SELECT COUNT(*)v FROM usuarios").fetchone()["v"] > 0:
        c.close(); raise HTTPException(403, "El sistema ya tiene una cuenta registrada")
    if c.execute("SELECT 1 FROM usuarios WHERE usuario=?", (x.usuario.strip(),)).fetchone():
        c.close(); raise HTTPException(409, "El usuario ya existe")
    pw = bcrypt.hashpw(x.password.encode(), bcrypt.gensalt()).decode()
    rec = gen_recovery()
    cur = c.execute("INSERT INTO usuarios(usuario,nombre,password_hash,recovery_hash,created_at) VALUES(?,?,?,?,?)",
        (x.usuario.strip(), x.nombre.strip(), pw, hash_recovery(rec), datetime.now().isoformat(timespec="seconds")))
    aud(c, x.usuario.strip(), "registro", "Cuenta creada")
    c.commit()
    token = make_token(cur.lastrowid, x.usuario.strip(), x.nombre.strip())
    c.close()
    return {"token": token, "expires_in": TOKEN_HORAS * 3600, "usuario": x.usuario.strip(),
            "nombre": x.nombre.strip(), "recovery": rec}


@router.post("/auth/login")
def login(x: AuthIn, request: Request):
    check_rate("login", request)
    c = db()
    row = c.execute("SELECT id,usuario,nombre,password_hash FROM usuarios WHERE usuario=?", (x.usuario.strip(),)).fetchone()
    if not row or not bcrypt.checkpw(x.password.encode(), row["password_hash"].encode()):
        aud(c, x.usuario.strip(), "login_fallido", "Credenciales incorrectas")
        c.commit(); c.close()
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    aud(c, row["usuario"], "login", "Inicio de sesión")
    token = make_token(row["id"], row["usuario"], row["nombre"])
    c.commit(); c.close()
    return {"token": token, "expires_in": TOKEN_HORAS * 3600, "usuario": row["usuario"], "nombre": row["nombre"]}


@router.post("/auth/olvide_password")
def olvide_password(x: RecoveryIn, request: Request):
    check_rate("olvide_password", request)
    import time
    codigo = x.codigo.replace("-", "").strip().upper()
    c = db()
    row = c.execute("SELECT id,recovery_hash FROM usuarios WHERE usuario=?", (x.usuario.strip(),)).fetchone()
    if not row or not row["recovery_hash"] or not bcrypt.checkpw(codigo.encode(), row["recovery_hash"].encode()):
        c.close(); time.sleep(0.6)
        raise HTTPException(401, "Usuario o clave de recuperación incorrectos")
    pw = bcrypt.hashpw(x.nueva.encode(), bcrypt.gensalt()).decode()
    c.execute("UPDATE usuarios SET password_hash=?, recovery_hash=NULL WHERE id=?", (pw, row["id"]))
    aud(c, x.usuario.strip(), "recuperacion", "Contraseña restablecida con clave de recuperación")
    c.commit(); c.close()
    return {"ok": True}


@router.post("/auth/regenerar_clave")
def regenerar_clave(request: Request, user=Depends(current_user)):
    check_rate("regenerar_clave", request)
    rec = gen_recovery()
    c = db()
    c.execute("UPDATE usuarios SET recovery_hash=? WHERE id=?", (hash_recovery(rec), user["id"]))
    aud(c, user["usuario"], "regenerar_clave", "Nueva clave de recuperación generada")
    c.commit(); c.close()
    return {"recovery": rec}


@router.get("/auth/mi")
def mi(user=Depends(current_user)):
    return user


@router.post("/auth/cambiar_password")
def cambiar_password(x: PassIn, user=Depends(current_user)):
    c = db()
    row = c.execute("SELECT password_hash FROM usuarios WHERE id=?", (user["id"],)).fetchone()
    if not row or not bcrypt.checkpw(x.actual.encode(), row["password_hash"].encode()):
        c.close(); raise HTTPException(401, "La contraseña actual no es correcta")
    pw = bcrypt.hashpw(x.nueva.encode(), bcrypt.gensalt()).decode()
    c.execute("UPDATE usuarios SET password_hash=? WHERE id=?", (pw, user["id"]))
    aud(c, user["usuario"], "cambiar_password", "Contraseña actualizada")
    c.commit(); c.close()
    return {"ok": True}