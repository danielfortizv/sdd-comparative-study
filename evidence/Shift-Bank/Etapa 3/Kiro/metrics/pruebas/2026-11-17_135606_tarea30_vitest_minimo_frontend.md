# Tarea 30 — Vitest MÍNIMO solo-dev en el frontend (Kiro)

- **Fecha/hora:** 2026-11-17 13:56:06 (-05:00)
- **Workspace:** `Etapa 3/Kiro/frontend`
- **Requisitos:** R19.2 · **Diseño:** §7 · **AC:** AC-14
- **Entorno:** Node v20.17.0, npm 11.6.3, Windows (PowerShell). Vite 5.4.21.

## Decisión

El frontend heredado solo tenía los scripts `dev`, `build` (`tsc && vite build`) y
`preview`; **no** había runner de pruebas. Se añade **Vitest** como dependencia
**SOLO de dev** con un conjunto de pruebas de humo mínimo alrededor del cliente de API.
Se eligió el entorno `node` (sin renderizar React) para mantener las dependencias al
mínimo: **no** se añadieron `@testing-library/*`, `jsdom`, `happy-dom` ni ninguna
dependencia de runtime. **No** se alteró el código de la aplicación.

## Dependencias de dev añadidas (nombres + versiones)

| Paquete  | Rango en package.json | Versión resuelta/instalada |
|----------|-----------------------|----------------------------|
| `vitest` | `^2.1.8`              | `2.1.9` (win32-x64, node-v20.17.0) |

- `npm install` → `added 30 packages, and audited 99 packages in 7s` (exit 0).
  (Las 30 son `vitest` + su árbol transitivo, todas bajo devDependencies.)
- **Sin** nuevas dependencias de `dependencies` (runtime). `react`/`react-dom` intactas.

## Archivos creados / modificados

- **Modificado** `package.json`:
  - Añadido script `"test": "vitest run"`. **No** se tocó `"build": "tsc && vite build"`.
  - Añadido `"vitest": "^2.1.8"` a `devDependencies`.
- **Modificado** `vite.config.ts`: añadido `/// <reference types="vitest/config" />` y
  un bloque `test` MÍNIMO (`environment: "node"`, `include: ["src/**/*.test.ts"]`).
  Vite ignora el bloque `test` fuera de Vitest, por lo que el build de producción no cambia.
- **Modificado** `tsconfig.json`: añadido `"exclude": ["src/**/*.test.ts", "src/**/*.test.tsx"]`
  para que `tsc` del build de producción **no** compile los archivos de prueba (así `tsc`
  sigue verde sin debilitar el chequeo de tipos de la app — `strict` y demás flags intactos).
- **Creado** `src/api/client.test.ts`: pruebas de humo del cliente de API.

## Descripción de las pruebas de humo (`src/api/client.test.ts`)

Parchean el `fetch` global (`vi.stubGlobal`) y verifican el comportamiento real del
cliente sin modificarlo. Importan explícitamente de `vitest` (sin globals):

1. `getAccounts()` → hace una petición a la ruta **relativa** `/api/accounts` (con
   `BASE_URL` por defecto `""`, es decir, mismo origen), sin `method` explícito (GET),
   y parsea/devuelve el JSON.
2. `createTransfer(payload)` → **POST** a `/api/transfers`, cuerpo `JSON.stringify(payload)`
   y cabecera `Content-Type: application/json`.
3. `updateLimits(...)` → **PUT** a `/api/limits` y, ante `{ error: { code, message } }` con
   HTTP 400, lanza `ApiRequestError` con el `code` propagado.

## Comandos exactos

```powershell
# (desde Etapa 3/Kiro/frontend)
npm install
npx vitest --version
npx vitest run
npm run build
npm test
```

## Resultados REALES

### `npx vitest --version`
```
vitest/2.1.9 win32-x64 node-v20.17.0
```

### `npx vitest run` → PASS
```
 RUN  v2.1.9 .../Etapa 3/Kiro/frontend
 ✓ src/api/client.test.ts (3)
   ✓ cliente de API — rutas relativas y métodos (prueba de humo) (3)
     ✓ getAccounts() hace GET a la ruta relativa /api/accounts y parsea el JSON
     ✓ createTransfer() hace POST a /api/transfers con cuerpo JSON
     ✓ updateLimits() hace PUT a /api/limits y propaga errores { error: { code, message } }
 Test Files  1 passed (1)
      Tests  3 passed (3)
   Duration  437ms
```
**Resultado: 3 passed (3) — Test Files 1 passed (1). Exit code 0.**

### `npm run build` → VERDE
```
> shift-bank-frontend@1.0.0 build
> tsc && vite build
vite v5.4.21 building for production...
✓ 41 modules transformed.
dist/index.html                   0.40 kB │ gzip:  0.27 kB
dist/assets/index-CX77R-vI.css    4.52 kB │ gzip:  1.38 kB
dist/assets/index-uDwVUt2C.js   169.82 kB │ gzip: 52.56 kB
✓ built in 722ms
```
**Resultado: `tsc` sin errores + `vite build` OK. Exit code 0.**

### `npm test` (alias de `vitest run`) → PASS
```
 ✓ src/api/client.test.ts (3 tests) 7ms
 Test Files  1 passed (1)
      Tests  3 passed (3)
```

## Notas

- Sin cambios en el backend; la baseline de 372 pruebas del backend no se ve afectada.
- D-E3-01..04 preservados (no se tocaron artefactos ni fuentes de la app).
- Resultados no fabricados: salidas copiadas de las ejecuciones reales (exit 0 en todas).
