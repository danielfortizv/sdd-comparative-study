# Kit inicial — Shift Bank Etapa 2 / Spec Kit

Preparado: 2026-11-14. Este paquete contiene documentos propuestos y una instrucción de descubrimiento de SOLO LECTURA. No significa que el investigador haya aprobado la semilla ni que Gemini haya implementado la etapa.

## Colocación en el repositorio

Copiar los archivos respetando las rutas de este paquete, relativas a:
`C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\`

- `Etapa 2/SEED-2.md` — semilla de Etapa 2 a entregar idéntica a las siguientes herramientas, después de aprobarla.
- `Etapa 2/E2_COMMON_FUNCTIONAL_CONTRACT.md` — contrato neutral en inglés, idéntico para herramientas restantes.
- `Etapa 2/_experiment_logs/Spec Kit/PROMPT_01_READ_ONLY_DISCOVERY.md` — prompt exacto exclusivo de Spec Kit para copiar en Gemini.
- `Etapa 2/_experiment_logs/Spec Kit/E2_SPECKIT_REGISTRO_02_DESCUBRIMIENTO.md` — plantilla experimental que debe completarse solo con evidencia.

NO sobrescribir ni reemplazar:
- `Etapa 2/_experiment_logs/Spec Kit/E2_SPECKIT_REGISTRO_01_PREPARACION.md`
- `Etapa 2/_experiment_logs/Spec Kit/E2_SPECKIT_GEMINI_HANDOFF.md`
- los manifests SHA-256, pruebas y logs previos
- ningún archivo de `Etapa 1/`

## Cómo empezar en PowerShell

```powershell
cd 'C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 2\Spec Kit'
specify version
specify check
specify integration status
$env:GEMINI_MODEL
gemini
```

Dentro de la sesión de Gemini:
1. Verificar que la integración incluya los slash commands `/speckit.*`.
2. Pegar TODO el contenido entre separadores de `PROMPT_01_READ_ONLY_DISCOVERY.md`.
3. Guardar íntegra la respuesta y registrar el estado de archivos/telemetría.
4. No ejecutar `/speckit.specify` todavía: primero revisar el descubrimiento y aprobar la semilla/decisiones.

**Nota:** ni el comando de arranque ni una variable de entorno prueban por sí solos cuál modelo fue empleado. Registrar la observación efectiva en `/stats`, transcript y configuración de sesión. Si el modelo requerido no está disponible, no sustituirlo silenciosamente.

## Referencias de investigación

- `Etapas proyecto de grado (1).pdf`, Etapa 2 / Fintech / opción A.
- `SHIFT_BANK_E2_CONTRATO_COMUN_Y_REFERENCIA_TESSL.md`, secciones 3–9 (fuente del contrato neutral; las métricas/hallazgos Tessl no son metas).
- `Guia Estandarizacion Metricas.pdf`.
- `Proyecto_de_Grado__SDD_en_Desarrollo_de_Software_Asistido_por_IA.pdf`, capítulo 5 (Spec Kit).

No presentar documentos nuevos como materiales históricos utilizados por Tessl.
