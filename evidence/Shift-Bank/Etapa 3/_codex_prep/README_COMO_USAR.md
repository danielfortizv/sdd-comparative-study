# Paquete de preparación E3 — Shift Bank / Spec Kit / Codex

**Finalidad:** encargar a Codex únicamente la preparación experimental de la **Etapa 3, Hito 0**, dejando el espacio listo para iniciar posteriormente el descubrimiento y las aclaraciones con **Gemini CLI + GitHub Spec Kit**. Codex **NO** debe implementar ninguna funcionalidad de E3, redactar las nuevas especificaciones ni tomar decisiones de negocio.

## Cómo utilizarlo en Windows / VS Code

1. Descarga el ZIP del paquete y extráelo en este directorio del repositorio (créalo si no existe):

   `C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\_codex_prep\`

   Debe contener `PROMPT_MAESTRO_CODEX.md`, los cuatro documentos de instrucciones, `CHECKLIST_ENTREGA.md` y `SEED-3.md`.
2. Abre en VS Code el **repositorio `sdd-comparative-study`**, preferiblemente manteniendo a Codex dentro de la carpeta `Shift-Bank` y sus rutas autorizadas.
3. Pega el texto de `PROMPT_MAESTRO_CODEX.md` en Codex o adjunta dicho archivo junto con los demás `.md`.
4. Codex debe copiar **sin modificar un byte** `SEED-3.md` a `Shift-Bank\Etapa 3\SEED-3.md` si todavía no está allí. Si existe y difiere, debe **detenerse**, no sobrescribirlo.
5. Al terminar, examina `Etapa 3\_experiment_logs\Spec Kit\preparacion\E3_SPECKIT_HITO0_READINESS.md` y el resultado `GO / NO-GO` de Codex. Luego comparte su respuesta conmigo para que revisemos las evidencias y redactemos el primer prompt de Gemini.

## Archivos incluidos

- `SEED-3.md`: semilla de E3, normativa común; **inmutable**. SHA-256 de esta copia: `99d23b7aee6eeb775fdc1617fff46a5409f10cb779ebcf411245e4602fabf1d9`.
- `00_CONTEXTO_Y_CONTRATOS.md`: situación real del proyecto, alcance, fuentes y límites.
- `01_PLAN_TECNICO_HITO0.md`: procedimiento de preparación, aislamiento, inventarios y validación inicial.
- `02_EVIDENCIAS_Y_METRICAS.md`: árbol de evidencia, procedencia y criterios científicos D1–D5.
- `03_HANDOFF_A_GEMINI.md`: condición de entrega, bloqueos y futura transición a Gemini.
- `CHECKLIST_ENTREGA.md`: criterios de aceptación para dar por preparado el Hito 0.
- `PROMPT_MAESTRO_CODEX.md`: mandato ejecutable para Codex.

## Qué NO se ha hecho aquí

El paquete se ha diseñado a partir de la semilla y del protocolo de replicación. **No se ha accedido a tu repositorio Windows, ni se han copiado sus archivos, instalado dependencias o ejecutado pruebas de E3.** Codex realizará esas actividades en tu máquina y generará la evidencia real. El texto de estos `.md` es material de coordinación previo al experimento y **no son especificaciones aprobadas de E3**.

## Principio metodológico

La Etapa 3 debe **heredar el cierre E2 de Spec Kit**, no el código de Tessl ni un prototipo nuevo. El desarrollo E3 medible comienza con Gemini y el proceso nativo de Spec Kit después de la aprobación humana del Hito 0. Las llamadas a Codex se registran como **preparación externa**, nunca se mezclan con métricas de Gemini de E3.
