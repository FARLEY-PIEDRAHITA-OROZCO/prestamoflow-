# Contributing to PrestamoFlow

¡Gracias por querer contribuir! Estas pautas mantienen el proyecto claro, testeable y plenamente documentado.

## Convención de commits

El historial usa [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/). Esto habilita versionado y changelog automáticos vía *release-please*.

Formato: `tipo(ámbito): descripción`

**Tipos admitidos**

| Tipo | Cuándo usarlo |
| --- | --- |
| `feat` | Nueva funcionalidad (cambia el menor de versión) |
| `fix` | Corrección de errores (cambia el parche) |
| `docs` | Solo documentación |
| `style` | Formato sin cambio de comportamiento |
| `refactor` | Cambio de código sin alterar comportamiento |
| `perf` | Mejora de rendimiento |
| `test` | Añadir/corregir pruebas |
| `build` | Dependencias o build |
| `ci` | Configuración de CI |
| `chore` | Tareas de mantenimiento, metadatos, ignore, etc. |

Ejemplos:

```
feat: allow editing payment amount and date
fix(backend): reject payments that exceed the balance
docs: document the REST API
test: cover payment cancellation flow
```

## Cómo contribuir

1. Haz *fork* del repositorio y crea una rama descriptiva (`feat/nombre-de-la-funcionalidad`).
2. Haz cambios pequeños e incrementales, siguiendo el estilo del código existente y **sin comentarios innecesarios**.
3. Ejecuta las pruebas antes de confirmar:

   ```bash
   cd backend
   .venv\Scripts\python.exe -m pytest -q
   ```

   y compila el frontend:

   ```bash
   cd frontend
   npm run build
   ```

4. Confirma usando Conventional Commits.
5. Abre un *pull request* describiendo qué hace el cambio y cómo probarlo.

## Reglas de estilo

- **Python:** sigue el estilo de `backend/core.py` y `routers/` (PEP 8, imports planos, funciones pequeñas).
- **React:** componentes pequeños, nombres claros, sin comentarios innecesarios; usa los helpers de `frontend/src/lib.jsx`.
- **Dinero:** nunca uses floats para operaciones monetarias; todo se almacena en **centavos enteros** y solo se formatea a pesos en la API/frontend.
- **Tests:** cada nueva lógica del backend debe incluir su prueba en `backend/tests/`.

## Reportar problemas

Abre una *issue* describiendo el paso a paso para reproducir, el resultado esperado y el comportamiento observado.

## Código de conducta

Revisa [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md): se espera un ambiente respetuoso para todxs.