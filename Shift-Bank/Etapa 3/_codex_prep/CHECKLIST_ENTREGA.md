# Checklist de aceptación — Preparación E3 Spec Kit (Codex, Hito 0)

**Este checklist es para la revisión del investigador, no representa resultados ya ejecutados.** Codex debe completar los estados únicamente según evidencia generada localmente.

| Control | Estado inicial | Evidencia requerida |
|---|---|---|
| Ruta E2 `Etapa 2/Spec Kit` inequívoca | PENDIENTE | Ruta resuelta, `git status`, commit, carpeta real |
| Destino E3 ausente o sin colisiones | PENDIENTE | Resultado de inspección previa y justificación de reutilización si aplica |
| Semilla E3 byte-idéntica | PENDIENTE | SHA-256 `99d23b7aee6eeb775fdc1617fff46a5409f10cb779ebcf411245e4602fabf1d9` |
| Inventario durable E2 verificable | PENDIENTE | CSV/hashes; reconciliación con manifiesto de cierre E2 si existe |
| Copia durable E2 → E3 intacta | PENDIENTE | CSV comparativo: 0 missing, 0 changed, 0 unexpected entre elegibles |
| Exclusión de DB/sidecars, secretos, node_modules y cachés | PENDIENTE | Regla de filtrado y verificación de ausencia; no borrar archivos históricos |
| `.specify`, código E1/E2, specs y tests heredados presentes | PENDIENTE | Inventario/árbol y hashes |
| Python, Node, npm, Git, Gemini y Spec Kit verificados | PENDIENTE | Salida de versiones reales y `N/D` para lo no comprobado |
| Dependencias instaladas en entornos E3 aislados | PENDIENTE | Comandos y logs; manifests/locks sin cambios |
| Base de prueba aislada y no histórica | PENDIENTE | Ruta absoluta, env efectiva sin exponer secretos, comprobación de fixtures |
| Backend pytest baseline | PENDIENTE | STDOUT/STDERR, exit code, conteos reales (E2 reportó 47/47) |
| Frontend Vitest baseline | PENDIENTE | STDOUT/STDERR, exit code, conteos reales (E2 reportó 12/12) |
| Frontend build baseline | PENDIENTE | STDOUT/STDERR, exit code |
| SHA de código E3 idéntico tras las pruebas | PENDIENTE | Segundo cotejo fuente/destino hash por archivo |
| Históricos E1/E2, otras herramientas y DB preservados | PENDIENTE | Inventario/observación antes-después; declarar limitaciones de prueba |
| Árbol de evidencias organizado; `sesiones`/`decisiones` aún sin casos ficticios | PENDIENTE | Listado de archivos realmente creados |
| Bitácora Codex separada de telemetría Gemini E3 | PENDIENTE | `E3_SPECKIT_PREPARACION_CODEX_LOG.md` |
| Informe final Hito 0 completo y verificable | PENDIENTE | `E3_SPECKIT_HITO0_READINESS.md` |
| Gemini no ejecutado; ninguna spec E3 ni implementación nueva | PENDIENTE | Diff/inventario y declaración de límites |

## Veredicto

- **GO PARA GEMINI HITO 1:** todos los controles críticos aprobados y no hay divergencias durables; pruebas iniciales realmente ejecutadas y aprobadas o excepciones formalmente revisadas por el investigador.
- **NO-GO:** colisión, semilla incorrecta, E2 fuente no verificable, hashes que divergen, uso de DB histórica, pruebas rotas o cambios de fuentes no autorizados. Identificar exactamente qué bloqueó la entrega. No pasar a Hito 1 de forma automática.

## Resumen final obligatorio de Codex

Completar con datos observados:

```text
E3 HITO 0: GO / NO-GO
Fuente E2: <ruta, commit y cantidad durable>
Destino E3: <ruta, cantidad durable>
Comparación SHA: <iguales, diferentes, ausentes, extras>
SEED-3 SHA: <hash verificado>
Backend tests: <N pass / N fail / skip / NOT EXECUTED, exit code>
Frontend tests: <N pass / N fail / NOT EXECUTED, exit code>
Frontend build: <PASS / FAIL / NOT EXECUTED, exit code>
Aislamiento DB: <ruta de DB temporal; evidencias de histórico no modificado>
Archivos generados: <paths en _experiment_logs/Spec Kit>
Bloqueos/limitaciones: <items concretos o Ninguno>
Siguiente paso permitido: revisión humana del Hito 0; NO iniciar Gemini por cuenta propia.
```
