# E2 · Kiro · Registro 03 — Refinamiento de requirements.md tras auditoría

- **Fecha:** 2026-11-16
- **Etapa:** 2 · Herramienta: Kiro
- **Fase:** refinamiento de requisitos tras auditoría (previa a diseño)
- **Autorización:** el investigador aprobó las cinco correcciones de la §5 de la auditoría y la
  decisión E2-KIRO-D06. Autorizado a modificar solo `requirements.md` y la documentación
  experimental asociada.

## Trazabilidad de versiones

| Versión | SHA-256 | Requisitos | Criterios | Líneas |
|---|---|---|---|---|
| v1 (Registro 02) | (generación inicial) | 16 | 82 | — |
| v2 (este registro) | `09B65639E8D3BBE2DA792E7E5EF1935A95AA56F3ED759ADB3411AF4A4A4F0197` | 16 | **86** | 600 |

## Cambios aplicados por ID de requisito

### Corrección 1 — R3 (validación de monto ACH)

- **Añadido criterio 3.8:** rechaza monto ACH ≤ 0 o con más de 2 decimales, sin producir
  débito, consistente con el modelo monetario de E1 (Req. 3.3 de E1). _(ACH-04; A09)_
- **Trazabilidad A09 corregida:** ahora referencia 3.1, **3.8** y 13.4, de modo que A09 se
  ancla a la validación de monto de transferencia y no solo al criterio de límites 13.4.

### Corrección 2 — R4 (elegibilidad de settlement)

- **R4 reescrito de 3 a 4 criterios:**
  - 4.1 (nuevo): elegibilidad explícita — solo ACH autorizada en `pending`; `settled`/`failed`
    no elegibles.
  - 4.2: settlement automático al cumplirse la condición de simulación documentada,
    **determinista e independientemente verificable** (reloj inyectable); mecanismo/retardo
    concretos diferidos a diseño; sin red bancaria real ni reglas arbitrarias.
  - 4.3: sin segundo débito.
  - 4.4: idempotencia ampliada a `settled` **y** `failed`.
- **Trazabilidad actualizada:** ACH-06 → 4.1,4.2,4.3; ACH-08 → 4.4; A07 → 3.5,4.2,4.3,4.4,6.1.

### Corrección 3 — R9 (reanudación de recurrentes, E2-KIRO-D06)

- **Añadidos criterios 9.6 y 9.7:**
  - 9.6: al reanudar, se **saltan** las ocurrencias perdidas durante la pausa y se **recalcula**
    la siguiente fecha desde la reanudación (intervalos 1/7/30), sin pagos duplicados ni débitos
    acumulados. _(REC-06, REC-08, REC-02, D06; A18)_
  - 9.7: `cancelled` permanece terminal, no reanudable. _(REC-07, D06; A18)_
- **Trazabilidad:** REC-06 → +9.6; REC-07 → +9.7; REC-08 → +9.6; A18 → +9.6,9.7.

### Corrección 4 — R7 (trazabilidad ACH-09)

- **Sin añadir conducta nueva:** se mapean explícitamente los cuatro comportamientos UI de
  ACH-09 a los criterios existentes mediante etiquetas [a][b][c][d] y una nota de cobertura:
  [a] diferenciar interno/ACH → 7.1; [b] seleccionar guardado/ad hoc → 7.1; [c] opción de
  guardar → 7.2; [d] mostrar estado → 7.4.
- **Trazabilidad ACH-09:** ahora `7.1 [a][b], 7.2 [c], 7.4 [d]`.

### Corrección 5 — A20 (verificación de regresión)

- **A20 se mantiene como obligación de verificación** (no se convierte en requisito funcional).
- **Nota ampliada** que documenta las obligaciones del futuro `tasks.md`: (1) crear suite de
  regresión de E1 (no existe heredada), (2) ejecutar regresión de lo heredado, (3) ejecutar
  nuevas pruebas de aceptación de E2, (4) build de producción del frontend, (5) registrar
  resultados/fallos reales. **A21** se preserva como obligación de verificación manual de UI,
  separada de A20.

## Decisión registrada

- **E2-KIRO-D06** — `decisiones/E2-KIRO-D06_reanudacion_recurrentes.md` (reanudación sin
  catch-up). D01–D05 preservadas sin cambios.

## Métricas finales (verificadas sobre el texto)

- Requisitos: 16 (sin cambio en número; R3, R4 y R9 ampliados).
- Historias de usuario: 16.
- Criterios de aceptación: **86** (v1: 82; +4: R3.8, R4 +1, R9.6, R9.7).
- Líneas físicas Markdown: 600.
- SHA-256: `09B65639E8D3BBE2DA792E7E5EF1935A95AA56F3ED759ADB3411AF4A4A4F0197`.

## Integridad

- Specs de Etapa 1: sin cambios (git limpio).
- Seed común y contrato funcional: no modificados.
- Evidencia previa (Registros 01 y 02, D01–D05, inventarios, smoke test): preservada.
- No se generó `design.md`, `tasks.md`, pruebas ni código de aplicación.
