import os, sys, sqlite3, bcrypt, jwt, secrets, time, random, shutil
from collections import defaultdict, deque
from pathlib import Path
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

def data_dir():
    """Carpeta estable para datos: junto al ejecutable cuando es un bundle
    (PyInstaller) o junto al código en desarrollo. Nunca dentro de _MEIPASS."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


DEFAULT_DB = data_dir() / "prestamos.db"
SECRET_FILE = data_dir() / ".secret"
ALGO = "HS256"
TOKEN_HORAS = 8
SCHEMA_VERSION = 4

def db_path():
    return Path(os.environ.get("PRESTAMOS_DB", str(DEFAULT_DB)))

def get_secret():
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text().strip()
    s = secrets.token_hex(32)
    SECRET_FILE.write_text(s)
    return s

SECRET = get_secret()

app = FastAPI(title="PrestamoFlow API", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
bearer = HTTPBearer(auto_error=False)

_rate = defaultdict(deque)
RATE_LIMIT = 12
RATE_WINDOW = 60

def check_rate(scope: str, request: Request):
    now = time.monotonic()
    key = (scope, request.client.host if request.client else "0.0.0.0")
    q = _rate[key]
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, "Demasiados intentos. Espera un minuto e intenta de nuevo")
    q.append(now)

RECOV_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

def gen_recovery():
    return "-".join("".join(random.SystemRandom().choice(RECOV_CHARS) for _ in range(4)) for _ in range(3))

def hash_recovery(codigo):
    return bcrypt.hashpw(codigo.replace("-", "").upper().encode(), bcrypt.gensalt()).decode()

def db():
    c = sqlite3.connect(db_path())
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def pesos(cents):
    return round(cents / 100, 2)

def aud(c, usuario, accion, detalle=""):
    c.execute("INSERT INTO auditoria(usuario,accion,detalle,created_at) VALUES(?,?,?,?)",
              (usuario, accion, detalle, datetime.now().isoformat(timespec="seconds")))

def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS personas(
      id INTEGER PRIMARY KEY AUTOINCREMENT,nombre TEXT NOT NULL,created_at TEXT NOT NULL,
      activa INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS prestamos(
      id INTEGER PRIMARY KEY AUTOINCREMENT,persona_id INTEGER NOT NULL,fecha TEXT NOT NULL,
      monto REAL NOT NULL CHECK(monto>0),tasa REAL NOT NULL DEFAULT 0,
      FOREIGN KEY(persona_id) REFERENCES personas(id));
    CREATE TABLE IF NOT EXISTS pagos(
      id INTEGER PRIMARY KEY AUTOINCREMENT,prestamo_id INTEGER NOT NULL,fecha TEXT NOT NULL,
      monto REAL NOT NULL CHECK(monto>0),activo INTEGER NOT NULL DEFAULT 1,
      FOREIGN KEY(prestamo_id) REFERENCES prestamos(id));
    CREATE TABLE IF NOT EXISTS usuarios(
      id INTEGER PRIMARY KEY AUTOINCREMENT,usuario TEXT NOT NULL UNIQUE,nombre TEXT NOT NULL,
      password_hash TEXT NOT NULL,recovery_hash TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS auditoria(
      id INTEGER PRIMARY KEY AUTOINCREMENT,usuario TEXT NOT NULL,accion TEXT NOT NULL,
      detalle TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_aud_created ON auditoria(created_at);
    """)
    cols = [r[1] for r in c.execute("PRAGMA table_info(prestamos)")]
    if "tasa" not in cols:
        c.execute("ALTER TABLE prestamos ADD COLUMN tasa REAL NOT NULL DEFAULT 0")
    if "vencimiento" not in cols:
        c.execute("ALTER TABLE prestamos ADD COLUMN vencimiento TEXT")
    cols_p = [r[1] for r in c.execute("PRAGMA table_info(personas)")]
    if "activa" not in cols_p:
        c.execute("ALTER TABLE personas ADD COLUMN activa INTEGER NOT NULL DEFAULT 1")
    cols_u = [r[1] for r in c.execute("PRAGMA table_info(usuarios)")]
    if "recovery_hash" not in cols_u:
        c.execute("ALTER TABLE usuarios ADD COLUMN recovery_hash TEXT")
    cols_pg = [r[1] for r in c.execute("PRAGMA table_info(pagos)")]
    if "activo" not in cols_pg:
        c.execute("ALTER TABLE pagos ADD COLUMN activo INTEGER NOT NULL DEFAULT 1")

    ver = c.execute("PRAGMA user_version").fetchone()[0]
    if ver < 3:
        c.execute("UPDATE prestamos SET monto=CAST(ROUND(monto*100) AS INTEGER)")
        c.execute("UPDATE pagos SET monto=CAST(ROUND(monto*100) AS INTEGER)")
        c.execute("UPDATE pagos SET activo=1 WHERE activo IS NULL OR activo NOT IN (0,1)")
        print("[PrestamoFlow] migración v2->v3: cantidades convertidas a centavos")
    if ver < SCHEMA_VERSION:
        c.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        print(f"[PrestamoFlow] base de datos migrada a esquema v{SCHEMA_VERSION}")
    c.commit()
    c.close()
init_db()

def daily_backup():
    bk_dir = Path(db_path()).parent / "backups"
    try:
        bk_dir.mkdir(exist_ok=True)
        today_bk = bk_dir / f"prestamos-{datetime.now().date().isoformat()}.db"
        if not today_bk.exists() and db_path().exists():
            shutil.copy2(db_path(), today_bk)
    except OSError:
        pass
daily_backup()


def frontend_dist():
    """Raíz del frontend compilado (index.html, assets/). En un bundle de
    PyInstaller viaja como 'frontend_dist'; en desarrollo es frontend/dist."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / "frontend_dist"
    return Path(__file__).resolve().parent.parent / "frontend" / "dist"

class PersonaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
class PrestamoIn(BaseModel):
    persona_id: int
    monto: float = Field(gt=0, le=1000000000)
    tasa: float = Field(default=0, ge=0, le=100)
    vencimiento: str | None = None
class PagoIn(BaseModel):
    prestamo_id: int
    monto: float = Field(gt=0, le=1000000000)
    fecha: str | None = None
class EditarPagoIn(BaseModel):
    monto: float = Field(gt=0, le=1000000000)
    fecha: str | None = None
class AuthIn(BaseModel):
    usuario: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)
class RegIn(BaseModel):
    usuario: str = Field(min_length=3, max_length=50)
    nombre: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
class PassIn(BaseModel):
    actual: str = Field(min_length=1, max_length=128)
    nueva: str = Field(min_length=8, max_length=128)
class RecoveryIn(BaseModel):
    usuario: str = Field(min_length=1, max_length=50)
    codigo: str = Field(min_length=6, max_length=64)
    nueva: str = Field(min_length=8, max_length=128)

def current_user(cred=Depends(bearer)):
    if not cred:
        raise HTTPException(401, "No autenticado", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(cred.credentials, SECRET, algorithms=[ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Sesión expirada, vuelve a iniciar sesión")
    except Exception:
        raise HTTPException(401, "Token inválido")
    return {"id": int(payload["sub"]), "usuario": payload["usuario"], "nombre": payload["nombre"]}

def make_token(user_id, usuario, nombre):
    iat = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "usuario": usuario, "nombre": nombre,
                       "iat": iat, "exp": iat + timedelta(hours=TOKEN_HORAS)},
                      SECRET, algorithm=ALGO)