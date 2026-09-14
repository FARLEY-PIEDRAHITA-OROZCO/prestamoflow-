# Security Policy

## Reporting a Vulnerability

Si encuentras una vulnerabilidad de seguridad en PrestamoFlow, **no** la reportes
en una *issue* pública. Escríbenos directamente a **farley.developer@gmail.com**
indicando:

- Descripción del problema y cómo reproducirlo.
- Impacto potencial.
- Versión afectada (si la conoces).

Gracias por ayudar a mantener seguro este proyecto.

## Notas de seguridad del proyecto

- Las contraseñas se almacenan con **bcrypt**; nunca se guardan en texto plano.
- La clave JWT vive en `backend/.secret` (local, ignorado por git); al desplegar
  en otro entorno, genera la tuya (`python -c "import secrets;print(secrets.token_hex(32))"`).
- La base de datos `backend/prestamos.db` es local y contiene datos reales:
  haz **respaldo** periódico (botón "Respaldo" o copia de `backend/backups/`).
- Los endpoints de autenticación tienen *rate limiting* (12 peticiones/minuto/IP).
- Cualquier monto monetario se maneja en **centavos enteros** para evitar
  errores de redondeo.