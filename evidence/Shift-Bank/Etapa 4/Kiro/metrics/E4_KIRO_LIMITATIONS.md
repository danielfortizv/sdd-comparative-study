# Etapa 4 — Kiro — Limitaciones y amenazas a la validez

Registro honesto de límites, decisiones con implicaciones y amenazas metodológicas. No altera los
veredictos; los contextualiza.

## 1. Medición D1 (créditos/uso)
- Solo existe el **snapshot PRE** provisto por el investigador (30,24/969,76, cuenta NUEVA). **No
  hay snapshot POST ni export de uso de sesión** en el workspace (`preparacion/D1/session-exports/`
  solo tiene `.gitkeep`). Por tanto: créditos consumidos, nº de interacciones/mensajes, tool calls,
  subagentes y timestamps de sesión = **N/D**. No se calcula ningún delta ni se inventan totales.
- El snapshot 898,98 pertenece a OTRA cuenta Kiro (histórico); NO se usa como baseline y no se
  mezcla.

## 2. Decisión Path A (dual-fixture) — implicaciones
- El arnés de regresión HEREDADO usa la siembra COP (`SHIFT_SEED_MODE=legacy`); la app por defecto
  y la ACEPTACIÓN de la Etapa 4 usan la fixture D-02 (`SHIFT_SEED_MODE=stage4`).
- **Implicación:** las pruebas legacy demuestran compatibilidad hacia atrás, NO aceptación de la
  Etapa 4. La aceptación de la Etapa 4 se demuestra exclusivamente con la fixture D-02 (tests
  `stage4_app_client` y servicios con cuentas D-02). Es una decisión reversible, sin cambio de
  contrato de los Specs; se eligió para mantener verde el baseline heredado y aislar la aceptación.

## 3. Discontinuidad monetaria del reset D-02 (DK-01)
- La fixture D-02 (USD/EUR/GBP) es un **reset experimental declarado**, NO una conversión COP→USD
  ni una migración que preserve valor. La preservación de datos/migración/rollback se verifica de
  forma **estructural** (idempotencia, atomicidad, rebuild determinista, sin doble conteo), no por
  equivalencia de valor monetario. Cualquier comparación de saldos Etapa 3 (COP) ↔ Etapa 4 (USD)
  es una discontinuidad intencional, no una regresión.

## 4. Cobertura
- La cobertura global en SonarQube (**49,6%**) está deprimida porque el **frontend React heredado**
  (App.tsx y paneles de Etapas 1–3) no tiene pruebas unitarias; lcov cubre el cliente de API y los
  módulos Stage 4. El backend coverage.py reporta 94%. No se infló cobertura ni se redujo el
  alcance para mejorar el número (prohibido). El Quality Gate POST es OK porque las condiciones son
  de **New Code** (new_coverage informativo, new_violations=0).

## 5. Alcance deliberado de la pasada correctiva (T29)
- Se resolvió la ÚNICA vulnerabilidad (typescript:S2245) y 2 de 10 findings S6759 (componentes
  propios de la Etapa 4). Se decidió **NO** modificar python:S9073/S5778/S9083 (124 findings, 100%
  en archivos de test, 0 en `app/`): reescribir aserciones/decoradores de tests en masa es el
  anti-patrón prohibido ("do not blindly modify code to eliminate counts") y arriesga el baseline
  de regresión y archivos heredados. **Implicación:** el total de issues POST (158) no baja a ~0;
  es un resultado honesto, no una regresión de calidad del producto.

## 6. Carga y despliegue
- La carga en vivo es local (una máquina; SQLite de único escritor). Los números p95/throughput son
  representativos de ese entorno, no de producción distribuida. La corrida oficial fue 30/5/60
  (contrato exacto); la verificación de invariantes post-carga se hizo en una corrida con DB viva
  separada (más corta) para poder inspeccionar la DB antes del teardown.
- El despliegue usa certificado autofirmado y secretos DESECHABLES (generados y eliminados);
  verificación SOLO local (sin hosting externo/K8s/CI). Las imágenes Docker construidas quedan en
  el daemon local (reutilizables), no son archivos del workspace.

## 7. Entorno vs preparación
- Node v20.17.0/npm 11.6.3 en esta máquina frente a v24.19.0/11.17.0 del baseline de preparación.
  Registrado explícitamente; los resultados de Vitest/build coinciden. No se considera amenaza
  material, pero se documenta.

## 8. SonarQube — límites del modelo de amenazas
- La auditoría HMAC + ancla detecta manipulación/inserción/eliminación intermedia y truncación de
  cola, pero no reclama inmutabilidad absoluta frente a un administrador con control total (clave +
  DB + ancla). Heredado de la Etapa 3 y preservado.
- Diferencia tradicional vs MQR: la fiabilidad tradicional es A (0 bugs) mientras la MQR fue D→C;
  son modelos distintos y se reportan por separado, sin combinarlos.

## 9. Incidente de exportación POST (no-escáner)
- El script PowerShell que generaba `*_POST_export_summary.json` falló; ese archivo de RESUMEN no
  existe. **El escaneo POST tuvo éxito** (scanner.log: ANALYSIS SUCCESSFUL/EXECUTION SUCCESS; exit
  0; ce_task SUCCESS) y el resto de exportaciones POST están completas y verificadas. Es un fallo
  de tooling de exportación, no del análisis.

## 10. Reintentos/correcciones durante la ejecución (transparencia)
- Orden de guardia ACH en recurrentes (INVALID_SOURCE→RECURRING_ACH_NOT_USD); literal SQLite
  `1000_00`; `Math.random` en fallback de UUID (resuelto T29); `openssl` del sistema inoperable
  (cert vía `cryptography`); encoding cp1252 del runner (PYTHONIOENCODING=utf-8); componentes
  Stage 4 no incluidos en el bundle hasta integrarlos en App.tsx. Todos corregidos y documentados;
  ninguna suite quedó roja al cierre.
