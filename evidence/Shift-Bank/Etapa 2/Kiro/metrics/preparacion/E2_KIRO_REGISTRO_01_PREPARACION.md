# E2 · Kiro · Registro 01 — Preparación del workspace y preservación del baseline

- **Proyecto:** Shift Bank — Estudio comparativo de metodologías SDD
- **Etapa:** 2 (Complejidad funcional y estado)
- **Herramienta evaluada:** Kiro
- **Fecha de preparación:** 2026-11-16
- **Alcance de esta tarea:** preparación del workspace y verificación del baseline. **No** se implementó funcionalidad de Etapa 2, ni se crearon/modificaron especificaciones funcionales nuevas.

---

## 1. Entorno observado

| Elemento | Valor |
| --- | --- |
| Sistema operativo | Microsoft Windows NT 10.0.26300.0 (win32) |
| Shell | PowerShell |
| Python | 3.13.2 |
| pip | 26.2.1 |
| Node.js | v24.19.0 |
| npm | 11.17.0 |
| Kiro / modelo IA | Kiro IDE; modelo **Auto** (selección dinámica en servidor) — versión exacta de Kiro no observable desde el entorno |
| Repositorio Git | `C:/Users/danie/Documents2/sdd-comparative-study` (único repo raíz) |
| Rama | `ShiftBank` |
| Commit base | `ebf1017748928b30a9a5ad68a56b9b532f304e86` — "Merge branch 'main' into ShiftBank" |
| Estado Git de `Etapa 1/Kiro` | limpio (sin cambios), antes y después de la preparación |

> Los cambios que aparecen en `git status` global corresponden exclusivamente a `Etapa 4/Spec Kit` (trabajo ajeno a esta tarea). `Etapa 1/Kiro` no presenta cambios.

### Dependencias declaradas (heredadas de Etapa 1)

- **Backend** (`backend/requirements.txt`): `fastapi==0.115.5`, `uvicorn==0.32.1`, `pydantic==2.10.3`.
- **Frontend** (`frontend/package.json`): `react ^18.3.1`, `react-dom ^18.3.1`; dev: `typescript ^5.6.3`, `vite ^5.4.11`, `@vitejs/plugin-react ^4.3.4`, `@types/react*`.

---

## 2. Rutas

| Rol | Ruta |
| --- | --- |
| Implementación original Etapa 1 (SOLO LECTURA) | `Shift-Bank/Etapa 1/Kiro/` |
| Copia de trabajo independiente Etapa 2 | `Shift-Bank/Etapa 2/Kiro/` |
| Evidencia experimental Etapa 2 | `Shift-Bank/Etapa 2/_experiment_logs/Kiro/` |

Estructura de logs creada: `preparacion/`, `sesiones/`, `pruebas/`, `sonarqube/`, `diffs/`, `decisiones/`.

---

## 3. Estructura real de la implementación heredada (Kiro, Etapa 1)

```text
Etapa 1/Kiro/
├── .kiro/
│   └── specs/
│       └── shift-bank/
│           ├── design.md
│           ├── requirements.md
│           └── tasks.md
├── backend/
│   ├── .gitignore
│   ├── requirements.txt
│   ├── shift_bank.db        (EXCLUIDO — DB SQLite mutable)
│   ├── .venv/               (EXCLUIDO — entorno virtual)
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       ├── db.py
│       ├── main.py
│       ├── money.py
│       ├── repository.py
│       ├── schemas.py
│       ├── seed.py
│       ├── service.py
│       └── routers/
│           ├── __init__.py
│           ├── accounts.py
│           └── transfers.py
└── frontend/
    ├── .gitignore
    ├── index.html
    ├── package.json
    ├── package-lock.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── node_modules/        (EXCLUIDO)
    ├── dist/                (EXCLUIDO — build)
    └── src/
        ├── App.tsx
        ├── main.tsx
        ├── types.ts
        ├── api/client.ts
        ├── components/{AccountsPanel,HistoryList,MfaDialog,TransferForm}.tsx
        └── styles/global.css
```

Observaciones relevantes sobre la arquitectura heredada (no modificada):

- Backend FastAPI, SQLite con el módulo estándar `sqlite3` (sin ORM). Se arranca con
  `uvicorn app.main:app`. El esquema y la siembra idempotente se ejecutan en el evento
  `startup` de FastAPI contra `backend/shift_bank.db` (`app/config.py → DB_PATH`).
- **No existe suite de pruebas automatizadas** en el backend (no hay carpeta `tests/`,
  ni `pytest` declarado en `requirements.txt`).
- Frontend React + TypeScript con Vite. Scripts: `dev`, `build` (`tsc && vite build`),
  `preview`. **No existe suite de pruebas** de frontend definida en `package.json`.
- No hay archivos `.env` ni `.env.example` en el proyecto.
- Moneda: COP; montos almacenados en centavos enteros. Umbral MFA: `1000000`;
  código MFA simulado fijo `123456`; TTL de MFA 5 min (`app/config.py`).

---

## 4. Copia de Etapa 1 → Etapa 2

Copia realizada con `robocopy /E` aplicando exclusiones. Resultado: **32 archivos
elegibles copiados**, 0 errores.

### Exclusiones aplicadas (artefactos generados / mutables / sensibles)

| Patrón | Encontrado en E1 | Motivo |
| --- | --- | --- |
| `node_modules/` | sí (frontend) | dependencias instalables |
| `.venv/` | sí (backend) | entorno virtual Python |
| `__pycache__/`, `*.pyc` | sí | caché de bytecode |
| `.pytest_cache/` | no presente | caché de pruebas |
| `dist/` | sí (frontend) | salida de build |
| `shift_bank.db` (+ `-journal/-wal/-shm`) | sí (`backend/shift_bank.db`, 36 864 B) | **DB SQLite mutable histórica** — nunca copiada ni modificada |
| `*.log`, `.env` | no presentes | logs locales / secretos |
| `.git/` anidados | no presentes | el repo git es único a nivel raíz |

No se encontró `.env.example` ni otras plantillas de configuración seguras que preservar
(no existen en el proyecto heredado).

---

## 5. Inventario SHA-256 y verificación de identidad

Script de inventario: `preparacion/_inventory.ps1` (aplica las mismas reglas de exclusión
y conserva los archivos que empiezan por `.`).

| Archivo de evidencia | Contenido |
| --- | --- |
| `E2_KIRO_BASELINE_E1_SHA256.csv` | inventario de `Etapa 1/Kiro` — 32 archivos (ruta relativa, tamaño, SHA-256) |
| `E2_KIRO_INITIAL_COPY_SHA256.csv` | inventario de `Etapa 2/Kiro` — 32 archivos |

**Resultado de la comparación:**

- Baseline: **32** archivos · Copia: **32** archivos.
- Hashes distintos: **0**. Faltantes en la copia: **0**. Extras en la copia: **0**.
- **VERIFICACIÓN: IDÉNTICOS — OK.** Cada archivo elegible copiado es bit a bit idéntico
  al original.

---

## 6. Verificación de la aplicación heredada (sobre la copia de Etapa 2)

### Frontend

| Paso | Comando (desde `Etapa 2/Kiro/frontend`) | Resultado |
| --- | --- | --- |
| Instalar dependencias | `npm install` | OK (código 0). 68 paquetes. Aviso: 2 vulnerabilidades (1 moderada, 1 alta) reportadas por `npm audit`; aviso `allow-scripts` sobre `esbuild` postinstall. No se aplicó `audit fix` (fuera de alcance). |
| Build de producción | `npm run build` (`tsc && vite build`) | **OK (código 0)**. `tsc` sin errores de tipos; Vite generó `dist/` (`index.js` 149,43 kB, gzip 48,34 kB) en ~0,5 s. |
| Pruebas de frontend | — | **No existen** (ningún script de test en `package.json`). No ejecutable: documentado, no corregido. |

### Backend

| Paso | Detalle | Resultado |
| --- | --- | --- |
| Entorno aislado | `python -m venv .venv` en la copia + `pip install -r requirements.txt` | OK (código 0). fastapi 0.115.5, uvicorn 0.32.1, pydantic 2.10.3 y transitivas. |
| Pruebas automatizadas | — | **No existen** en el proyecto heredado (sin `tests/`, sin `pytest`). No se instaló `pytest`/`httpx` para respetar la regla de no añadir dependencias ajenas. Documentado, no corregido. |
| Smoke test de arranque y endpoints | `pruebas/_smoke_backend.py` — invoca la app ASGI directamente (sin httpx) contra una **DB SQLite temporal aislada** (`%TEMP%\e2_kiro_smoke.db`), parcheando `DB_PATH`. Nunca toca `shift_bank.db`. | **OK — 9/9 checks PASS** |

Checks del smoke test (todos PASS):

1. DB temporal creada en arranque (schema + seed ejecutados).
2. `GET /api/accounts` → 200.
3. Dos cuentas sembradas.
4. Cuentas = `Checking`, `Savings`.
5. `GET /api/transfers` → 200.
6. Dos transferencias históricas sembradas.
7. `POST /api/transfers` (1000.00, bajo umbral MFA) → 201.
8. Transferencia no requiere MFA (`mfa_required=false`).
9. Historial refleja la nueva transferencia (3 registros).

> La DB temporal se eliminó al finalizar. La DB histórica `Etapa 1/Kiro/backend/shift_bank.db`
> conserva su fecha original (13/10/2026) — nunca fue abierta ni modificada.
> Arranque manual documentado (no ejecutado como proceso de larga duración): backend
> `uvicorn app.main:app --reload --port 8000` desde `backend/`; frontend `npm run dev`
> (Vite, puerto 5173) desde `frontend/`.

---

## 7. Especificaciones Kiro SDD preservadas

Workflow nativo de Kiro (spec) preservado íntegro en la copia, sin regenerar ni reescribir:

- `.kiro/specs/shift-bank/requirements.md`
- `.kiro/specs/shift-bank/design.md`
- `.kiro/specs/shift-bank/tasks.md`

No se hallaron steering files (`.kiro/steering/`), hooks (`.kiro/hooks/`) ni otra
configuración `.kiro/` adicional en el proyecto heredado; solo existe `.kiro/specs/`.

---

## 8. Semilla común (SEED-2)

- `SEED-2.md` **ya existe**: `Shift-Bank/Etapa 2/SEED-2.md` (estado: PROPOSED COMMON SEED,
  pendiente de aprobación del investigador). **No se modificó.**
- Contrato funcional acompañante presente: `Shift-Bank/Etapa 2/E2_COMMON_FUNCTIONAL_CONTRACT.md`
  (no modificado; su lectura funcional queda fuera del alcance de esta preparación).

---

## 9. Integridad experimental — confirmaciones

1. **Etapa 1 sin modificar:** `git status` de `Etapa 1/Kiro` limpio; DB histórica intacta.
2. **Solo código propio de Kiro:** la copia proviene exclusivamente de `Etapa 1/Kiro`.
3. **Sin contaminación cruzada:** no se copió nada de Tessl, OpenSpec, Spec Kit ni BMAD.
4. **Sin requisitos funcionales nuevos.**
5. **Sin cambios de comportamiento de la aplicación.**
6. **Specs de Kiro no regeneradas ni reescritas.**
7. **Sin especificaciones funcionales de Etapa 2** (pendiente de aprobación del investigador).
8. **Sin instalar herramientas no relacionadas:** no se añadió `pytest`/`httpx`; solo las
   dependencias declaradas en los manifests heredados.
9. **Evidencia histórica separada** de la evidencia futura de Etapa 2 (carpeta propia por herramienta).
10. **Desviaciones registradas** (sección 10).

---

## 10. Desviaciones respecto al protocolo previsto

- **Pruebas automatizadas inexistentes en el baseline:** el protocolo pide "ejecutar
  pruebas existentes de backend/frontend". El proyecto Kiro de Etapa 1 **no incluye
  ninguna suite de pruebas**. No se crearon pruebas (fuera de alcance). Como sustituto de
  verificación se ejecutó un smoke test no intrusivo (ASGI, DB temporal) que no forma
  parte de la aplicación.
- **`TestClient`/`httpx` no disponibles:** para no instalar dependencias ajenas (regla 8),
  el smoke test invoca la app vía protocolo ASGI con `asyncio` en lugar de un cliente HTTP.
- **Versión exacta de Kiro:** no observable de forma fiable desde el entorno; se registra
  el modo de modelo (Auto) en su lugar.
- **`npm audit`:** reporta 2 vulnerabilidades en dependencias de desarrollo heredadas; no
  se aplicó corrección para no alterar el baseline (`npm audit fix` cambiaría el lockfile).

---

## 11. Artefactos de evidencia generados

```text
Etapa 2/_experiment_logs/Kiro/preparacion/
├── E2_KIRO_BASELINE_E1_SHA256.csv      # inventario SHA-256 de Etapa 1 (32 archivos)
├── E2_KIRO_INITIAL_COPY_SHA256.csv     # inventario SHA-256 de la copia (32 archivos)
├── E2_KIRO_REGISTRO_01_PREPARACION.md  # este registro
└── _inventory.ps1                      # script de inventario reutilizable
Etapa 2/_experiment_logs/Kiro/pruebas/
└── _smoke_backend.py                   # smoke test ASGI del backend heredado
```

**Estado:** preparación y verificación de baseline completadas. A la espera de
autorización explícita del investigador para iniciar el descubrimiento de requisitos,
la generación de especificaciones o la implementación de la Etapa 2.
