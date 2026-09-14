# PrestamoFlow

<p align="center">
  <img alt="Licencia" src="https://img.shields.io/badge/license-MIT-blue.svg">
  <img alt="Conventional Commits" src="https://img.shields.io/badge/conventional%20commits-1.0.0-yellow.svg">
  <img alt="CI" src="https://img.shields.io/github/actions/workflow/status/FARLEY-PIEDRAHITA-OROZCO/prestamoflow-/ci.yml?branch=main">
</p>

Sistema contable de préstamos personales: lleva el control de personas, préstamos con interés, pagos (registrar, editar y anular), vencimientos y mora, con auditoría completa, respaldo automático y una interfaz responsive.

- **Backend:** FastAPI + SQLite
- **Frontend:** React 18 + Vite (SPA)
- **Moneda:** pesos colombianos (COP) con formato `es-CO`
- **Idioma de la aplicación:** español

---

## Índice

1. [Características](#características)
2. [Arquitectura](#arquitectura)
3. [Estructura del proyecto](#estructura-del-proyecto)
4. [Cómo ejecutar](#cómo-ejecutar)
5. [Configuración](#configuración)
6. [API (referencia)](#api-referencia)
7. [Modelo de datos](#modelo-de-datos)
8. [Seguridad](#seguridad)
9. [Auditoría y respaldo](#auditoría-y-respaldo)
10. [Manejo del dinero (centavos)](#manejo-del-dinero-centavos)
11. [Pruebas](#pruebas)
12. [Responsive / UX](#responsive--ux)

---

## Características

- **Autenticación y seguridad:**
  - Registro de la cuenta inicial (solo la primera cuenta puede registrarse).
  - Inicio de sesión con JWT (token de 8 horas).
  - Cambio de contraseña.
  - Recuperación de contraseña mediante **clave de recuperación** (una sola, mostrada una única vez al registrar/regenerar).
  - Rate limiting por IP en los intentos de `registro`, `login`, `olvide_password` y `regenerar_clave` (12 intentos por minuto).
  - Contraseña mínima de 8 caracteres.

- **Personas:**
  - Crear, editar, **archivar** y restaurar personas.
  - No se puede archivar una persona con préstamos pendientes de pago.
  - Filtro mostrar/ocultar archivadas.

- **Préstamos:**
  - Crear préstamos por persona con monto, tasa de interés (0–100 %) y fecha de vencimiento opcional.
  - Cálculo automático del interés, total y saldo pendiente.
  - Estados: todos / en curso / en mora / pagados (chips de filtro).
  - Indicador de **mora** con número de días vencidos.

- **Pagos:**
  - Registrar pagos (monto + fecha opcional).
  - **Editar** pagos (monto y/o fecha) con validación de que no exceda el saldo.
  - **Anular** pagos; el saldo del préstamo se recupera automáticamente.
  - Historial de pagos por préstamo con acciones de editar/anular.

- **Panel (Resumen):**
  - Estadísticas globales: total prestado, interés esperado, total pagado, saldo pendiente, préstamos activos, en mora y personas activas.
  - Búsqueda global de personas y préstamos desde el encabezado.

- **Auditoría:**
  - Registro de cada evento (crear/editar/archivar/restaurar, pagos, anulaciones, login, recuperación, etc.).
  - Página de auditoría con filtro por límite y usuario.

- **Respaldo:**
  - Descarga manual del backup mediante el botón "Respaldo" (`GET /api/backup`).
  - Copia diaria automática del archivo en `backend/backups/`.

---

## Arquitectura

```
┌──────────────┐    HTTP+JSON (Bearer)     ┌─────────────────┐
│  Frontend    │  ───────────────────────► │  Backend        │
│  React/Vite  │  ◄─────────────────────── │  FastAPI        │
└──────────────┘       127.0.0.1:8001      └────────┬────────┘
                                                     │ sqlite3
                                             ┌───────▼────────┐
                                             │  prestamos.db  │
                                             └────────────────┘
```

- El backend expone una API REST bajo el prefijo `/api`.
- El frontend opera 100 % contra la API; no tiene acceso directo a la base de datos.
- El CORS permite orígenes `http://localhost:5173` y `http://127.0.0.1:5173` (dev de Vite).

### Cómo funciona el cálculo financiero

Para cada préstamo:

```
interés_c = round(monto_c * tasa / 100)          # centavos
total_c   = monto_c + interés_c
saldo_c   = total_c - Σ pagos activos
```

El interés es **simple** y se calcula una sola vez sobre el monto prestado. El pago se aplica primero al total (capital + interés) hasta dejarlo en cero.

---

## Estructura del proyecto

```
Sistema_Contable/
├── README.md                 ← esta documentación
├── INICIAR-WINDOWS.bat       ← arranque rápido (API + frontend en Windows)
├── .gitignore
├── backend/
│   ├── main.py               ← entrada de FastAPI (monta routers)
│   ├── core.py               ← app, BD, modelos Pydantic, auth JWT, rate limit, migraciones
│   ├── requirements.txt
│   ├── README.md
│   ├── routers/
│   │   ├── auth.py           ← login, registro, recuperación, cambio de clave
│   │   └── catalog.py        ← personas, préstamos, pagos, auditoría, backup, dashboard
│   ├── tests/
│   │   ├── conftest.py       ← fixtures (cliente + autenticado, BD temporal)
│   │   ├── test_core.py      ← 12 pruebas de lógica de negocio
│   │   └── test_auth.py      ← 6 pruebas de autenticación
│   ├── prestamos.db          ← base de datos real (NO subir a git)
│   ├── backups/              ← copias diarias automáticas
│   └── .secret               ← clave JWT local (NO subir a git)
└── frontend/
    ├── index.html
    ├── package.json
    └── src/
        ├── main.jsx          ← toda la interfaz (páginas, modales, estados)
        ├── lib.jsx           ← helpers: API, money, fechas, avatares, búsqueda
        └── styles.css        ← estilos y media queries responsive
```

---

## Cómo ejecutar

### Opción rápida (Windows)

Ejecutar `INICIAR-WINDOWS.bat`, que:

1. Crea el entorno virtual de Python si no existe e instala dependencias.
2. Arranca el backend en `http://127.0.0.1:8001`.
3. Arranca Vite dev en `http://localhost:5173`.

### Opción manual

**Backend**

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --port 8001
```

- API: `http://127.0.0.1:8001`
- Documentación interactiva (Swagger): `http://127.0.0.1:8001/docs`
- Healthcheck: `http://127.0.0.1:8001/api/health`

**Frontend**

```
cd frontend
npm install
npm run dev
```

Abrir `http://localhost:5173`.

**Primera vez:** la aplicación pedirá **registrar la cuenta inicial** (usuario, nombre y contraseña de al menos 8 caracteres). Al registrarse muestra la **clave de recuperación** una sola vez — guardarla, es imprescindible para recuperar acceso.

---

## Configuración

| Variable | Dónde | Valor por defecto | Descripción |
| --- | --- | --- | --- |
| `VITE_API_URL` | `frontend/.env.local` | `http://127.0.0.1:8001/api` | URL base de la API para el frontend |
| `PRESTAMOS_DB` | entorno del backend | `backend/prestamos.db` | Ruta del archivo SQLite (la usan los tests con una base temporal) |

El token de sesión se guarda en `localStorage` como `pf_token`.

---

## API (referencia)

Autenticación: casi todos los endpoints requieren el header `Authorization: Bearer <token>`.

### Autenticación

| Método | Ruta | Cuerpo (JSON) | Respuesta | Notas |
| --- | --- | --- | --- | --- |
| GET | `/api/health` | — | `{status}` | Healthcheck público |
| GET | `/api/auth/estado` | — | `{tiene_usuarios}` | ¿Hay cuenta registrada? |
| POST | `/api/auth/registro` | `usuario`, `nombre`, `password` | `{token, expires_in, usuario, nombre, recovery}` | Solo la primera cuenta (403 si ya existe alguna) |
| POST | `/api/auth/login` | `usuario`, `password` | `{token, expires_in, usuario, nombre}` | Registra evento `login`/`login_fallido` |
| POST | `/api/auth/olvide_password` | `usuario`, `codigo`, `nueva` | `{ok}` | La clave de recuperación se invalida al usarla |
| POST | `/api/auth/regenerar_clave` | — | `{recovery}` | Regenera clave para el usuario autenticado |
| GET | `/api/auth/mi` | — | `{id, usuario, nombre}` | Info del usuario autenticado |
| POST | `/api/auth/cambiar_password` | `actual`, `nueva` | `{ok}` | Requiere la contraseña actual |

### Catálogo

| Método | Ruta | Parámetros / Cuerpo | Respuesta | Notas |
| --- | --- | --- | --- | --- |
| GET | `/api/dashboard` | — | Totales y conteos globales | Resumen del panel |
| GET | `/api/personas` | `incluir_archivadas` (bool) | Lista de personas | |
| POST | `/api/personas` | `nombre` | `{id, nombre}` | |
| PUT | `/api/personas/{id}` | `nombre` | `{id, nombre}` | |
| DELETE | `/api/personas/{id}` | — | `{id, activa: false}` | **Archiva**; 400 si hay préstamos pendientes |
| POST | `/api/personas/{id}/restaurar` | — | `{id, activa: true}` | |
| GET | `/api/auditoria` | `limite` (1–1000), `usuario` | Lista de eventos | Orden descendente |
| GET | `/api/backup` | — | Archivo `.db` (descarga) | Snapshot consistente via SQLite backup |
| GET | `/api/prestamos` | `estado` (`todos`/`mora`/`en_curso`/`pagados`) | Lista de préstamos con saldo | |
| POST | `/api/prestamos` | `persona_id`, `monto`, `tasa`, `vencimiento?` | `{id}` | ISO `YYYY-MM-DD` para vencimiento |
| GET | `/api/prestamos/{id}/pagos` | — | Lista de pagos activos | |
| POST | `/api/pagos` | `prestamo_id`, `monto`, `fecha?` | `{id, balance}` | 400 si el pago excede el saldo |
| POST | `/api/pagos/{id}/anular` | — | `{id, activa: false}` | 404 si ya está anulado |
| PUT | `/api/pagos/{id}` | `monto`, `fecha?` | `{id, monto, fecha}` | Valida que no exceda el saldo; 404 si está anulado |

Códigos comunes: `401` no autenticado / sesión expirada, `403` sin permisos, `404` recurso inexistente, `422` validación Pydantic, `429` rate limit superado.

Respuestas de error: `{"detail": "mensaje"}`.

---

## Modelo de datos

La base es `backend/prestamos.db` (SQLite). Cuestiones importantes:

- **Los montos monetarios se guardan en centavos** (enteros). El API los expone en pesos. Ver [Manejo del dinero](#manejo-del-dinero-centavos).
- Esquema versionado con `PRAGMA user_version` (actual: **v4**). Las migraciones se aplican automáticamente al arrancar el backend.

### Tablas

**personas**

| Columna | Tipo | Notas |
| --- | --- | --- |
| id | INTEGER PK | |
| nombre | TEXT NOT NULL | |
| created_at | TEXT NOT NULL | ISO |
| activa | INTEGER DEFAULT 1 | 0 = archivada |

**prestamos**

| Columna | Tipo | Notas |
| --- | --- | --- |
| id | INTEGER PK | |
| persona_id | INTEGER FK → personas | |
| fecha | TEXT NOT NULL | `YYYY-MM-DD` |
| monto | REAL CHECK(monto>0) | en centavos |
| tasa | REAL DEFAULT 0 | porcentaje (0–100) |
| vencimiento | TEXT | `YYYY-MM-DD`, opcional |

**pagos**

| Columna | Tipo | Notas |
| --- | --- | --- |
| id | INTEGER PK | |
| prestamo_id | INTEGER FK → prestamos | |
| fecha | TEXT NOT NULL | `YYYY-MM-DD` |
| monto | REAL CHECK(monto>0) | en centavos |
| activo | INTEGER DEFAULT 1 | 0 = anulado |

**usuarios**

| Columna | Tipo | Notas |
| --- | --- | --- |
| id | INTEGER PK | |
| usuario | TEXT UNIQUE | |
| nombre | TEXT | |
| password_hash | TEXT | bcrypt |
| recovery_hash | TEXT | hash de la clave de recuperación |
| created_at | TEXT | ISO |

**auditoria**

| Columna | Tipo | Notas |
| --- | --- | --- |
| id | INTEGER PK | |
| usuario | TEXT | quien ejecutó la acción |
| accion | TEXT | p. ej. `crear_pago`, `anular_pago`, `login` |
| detalle | TEXT | descripción del cambio |
| created_at | TEXT | ISO (indexada) |

Acciones de auditoría registradas: `registro`, `login`, `login_fallido`, `recuperacion`, `regenerar_clave`, `cambiar_password`, `crear_persona`, `editar_persona`, `archivar_persona`, `restaurar_persona`, `crear_prestamo`, `crear_pago`, `editar_pago`, `anular_pago`.

---

## Seguridad

- **Contraseñas:** hash bcrypt (nunca en texto plano). Mínimo 8 caracteres tanto en registro como en cambios.
- **Sesiones:** JWT HS256 firmado con clave local (`backend/.secret`, autogenerada), expiración de **8 horas**. El frontend hace *logout automático* al recibir un 401.
- **Recuperación de acceso:** clave de 12 caracteres en 3 bloques (alfabeto sin caracteres ambiguos: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`), guardada como hash y **válida una sola vez**.
- **Rate limiting:** 12 peticiones por minuto por IP en los endpoints de autenticación sensibles. Respuesta `429`.
- **CORS restringido** a los orígenes de desarrollo de Vite.
- Prevención de *user enumeration* en la recuperación: el endpoint responde `401` idéntico tanto si el usuario no existe como si la clave es incorrecta.

---

## Auditoría y respaldo

- **Auditoría:** cada cambio significativo inserta un registro en `auditoria` con usuario, acción, detalle y timestamp. Consultable desde la página *Auditoría* del frontend y desde `GET /api/auditoria`.
- **Respaldo manual:** botón `Respaldo` en el menú lateral. Descarga `respaldo-prestamosflow-AAAA-MM-DD.db` (copia consistente mediante la API de backup de SQLite).
- **Respaldo automático:** al arrancar el backend se crea `backend/backups/prestamos-AAAA-MM-DD.db` (una copia por día, sin sobrescribir).

---

## Manejo del dinero (centavos)

Para eliminar errores de redondeo con floats, **todo monto se almacena como centavos enteros**:

- El API recibe pesos (`monto: 123456.78`) y lo convierte con `int(round(monto*100))`.
- El interés se redondea al centavo: `int(round(monto_c * tasa / 100))`.
- El API devuelve pesos con `round(cents / 100, 2)`.
- La migración v2→v3 multiplicó por 100 los montos existentes.

Esto garantiza, p. ej., que prestar y pagar exactamente `$123.456,78` deja saldo `0,00` real.

---

## Pruebas

Suite con **pytest** (18 pruebas) sobre una base temporal (no toca los datos reales).

```
cd backend
.venv\Scripts\python.exe -m pytest -q
```

- `tests/conftest.py` configura `PRESTAMOS_DB` a una base temporal ANTES de importar la app y limpia tablas entre pruebas.
- `test_core.py`: lógica de préstamos/pagos (interés, saldo, centavos, anular/editar pagos, mora, dashboard, backup, auditoría).
- `test_auth.py`: registro, login, recuperación, cambio de contraseña, política de contraseñas, única cuenta.

Para recompilar el frontend:

```
cd frontend
npm run build
```

---

## Responsive / UX

La interfaz se adapta en tres puntos de ruptura:

- **≤ 1180px:** contenidos con menos padding lateral.
- **≤ 900px:** la barra lateral se convierte en **drawer** tipo hamburguesa; busca y notificaciones siguen visibles.
- **≤ 640px:** las tablas pasan de columnas a **tarjetas** con etiquetas por campo; el encabezado se compacta; estadísticas a dos columnas.
- **≤ 400px:** estadísticas a una columna, modales y botones de acción a ancho completo.

Nota técnica: el drawer se renderiza como hermano del `<header>` (no hijo) porque el `backdrop-filter` del encabezado rompería el `position:fixed` del overlay en algunos navegadores.

---

## Historial de versiones

- **v4.0.0**: pagos editables (`PUT /api/pagos/{id}`), auditoría `editar_pago`, historial con acciones editar/anular.
- **v3.x**: mora y vencimientos, respaldo y resumen por persona, rate limiting y recuperación de contraseña, refactor a routers.
- **v2.x**: montos convertidos a centavos, migración automática, auditoría y anulación de pagos.
- **v1.x**: gestión básica de personas, préstamos y pagos.