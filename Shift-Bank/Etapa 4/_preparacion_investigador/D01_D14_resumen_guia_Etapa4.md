# Etapa 4 — Resumen de decisiones D-01 a D-14

> Extracción fiel de la tabla de la guía oficial. Es un **resumen**, no sustituye los registros originales completos de aprobación ni los Specs nativos de Kiro.

- **D-01:** Una moneda fija por cuenta: USD, EUR o GBP; no mezclar saldos heterogéneos.
- **D-02:** Preservar CHK-1001 (USD 2500.00) y SAV-2001 (USD 10000.00); añadir EUR-3001 y GBP-4001 con saldo 0.00.
- **D-03:** Backend con Decimal, frontend con BigInt/centavos, cadenas de dos decimales; tasas racionales fijas; ROUND_HALF_UP una vez al final; sin cargos ni floats financieros.
- **D-04:** Transferencias internas solo misma moneda; los cambios entre divisas pasan exclusivamente por /api/conversions.
- **D-05:** SQLite append-only para eventos de dominio, separado de la auditoría histórica; migración sin doble conteo.
- **D-06:** Proyecciones CQRS síncronas y atómicas con eventos; reconstrucción determinista; fail-closed ante inconsistencia.
- **D-07:** Límite USD equivalente por operación 5000.00 y diario 10000.00; MFA si equivalente USD sin redondear > 1000.00.
- **D-08:** ACH solo desde USD; recurrentes internos misma moneda; recurrentes ACH solo USD.
- **D-09:** Eventos compuestos con versiones +1 por cuenta afectada; ACH débito en pending, settlement sin doble débito, fracaso con un único reembolso.
- **D-10:** Dashboard con totales separados por moneda; USD estimado solo para visualización.
- **D-11:** Cifrado AES-GCM, auditoría encadenada HMAC y atomicidad evento–proyección–auditoría–idempotencia; fallos auditables.
- **D-12:** Conservar FastAPI, React, SQLite y capacidad de despliegue Compose/Nginx/TLS; no inventar despliegue verificado.
- **D-13:** Idempotency-Key UUID obligatorio para transferencias internas/FX/ACH; replay exacto sin nuevos efectos; reuse con payload distinto -> 409.
- **D-14:** Versiones de cuenta esperadas obligatorias; solicitudes obsoletas -> 409 ACCOUNT_VERSION_CONFLICT; replay idempotente precede a validación de versión.

**Fuente:** `Guia_replicacion_Etapa4_Shift_Bank_SDD.docx`, tabla D-01–D-14.
**SEED-4:** anexo íntegro de la guía, extraído en UTF-8 con salto de línea final, SHA-256 `8d7e32d3cb359b3d1c442b0f71d83dfd6bde5eb31e9af62d74581d47f0fd3047`.
