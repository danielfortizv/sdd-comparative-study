"""Readable Spanish presentation of verified researcher JSON; no new checks."""
from kiro_research import DOCS, load

r=load(DOCS/'FINAL_REPORT.json')
m=load(DOCS/'metrics.json')
catalog=load(DOCS/'acceptance/final/catalog.json')
questions=load(DOCS/'question-audit.json')
q={row['label']:row for row in questions['runs']}
def n(value,places=3):
    if value is None: return 'ND'
    return f'{value:,.{places}f}'.replace(',','_').replace('.',',').replace('_','.')
names=['Nuevo juego','Lectura sin mutación','Bloqueo sin limpiar filas','Una fila','Dos filas',
       'Tres filas','Regla de cuatro filas','Cruce de 9 a 10 líneas','Suelo de gravedad: 100 ms',
       'Primer Hold','Segundo Hold rechazado','Hold tras bloquear','Spawn reservado bloqueado',
       'Acciones tras Game Over','Reinicio','Contrato HTTP','HUD, tecla C y botón Hold',
       'Gravedad y concurrencia','Regresión de etapa 1','Build de producción']
text=['# Kiro — Tetris, etapa 2, opción A','',
 'Cierre técnico verificado el **23 de octubre de 2026**, hora de Bogotá. La publicación en Drive y su revisión visual se registran por separado.','',
 '## Resultado','',
 '- **120 pruebas backend y 49 frontend aprobadas** en una repetición independiente. Build de producción aprobado.',
 '- **Cero hallazgos npm**, tanto en el árbol completo como en producción.',
 '- **Cinco controles externos de concurrencia aprobados**, 15 registros de dominio, siete registros HTTP y nueve controles suplementarios de contrato.',
 '- **20/20 criterios del catálogo verificados**, mediante los mecanismos declarados abajo. No es una tasa de aceptación exclusivamente en navegador.',
 '- Entrega íntegra de la semilla común acreditada en **7/7 entradas**. Se conserva la semilla del juego **20260929**, las formas canónicas y el generador de bolsa de siete piezas.','',
 '## Pruebas y cobertura','',
 '| Medición | Resultado |','|---|---:|',
 '| Backend | 245/247 líneas: 99,19 % |',
 '| Frontend: sentencias | 163/184: 88,58 % |',
 '| Frontend: ramas | 76/98: 77,55 % |',
 '| Frontend: funciones | 38/41: 92,68 % |',
 '| Frontend: líneas | 154/163: 94,47 % |','',
 'El LCOV incluye los siete módulos de producción, incluido `main.tsx`. La cobertura de ramas del backend no se instrumentó: los contadores 0/0 no se presentan como 0 % ni como 100 %. Las versiones 3 y 4 de Vitest usan denominadores diferentes; sus porcentajes no se comparan como si fueran idénticos.','',
 '## SonarQube','',
 f'- Proyecto `tetris-stage2-kiro`, versión 2.0; baseline 1.0. CE `{r["exact_quality"]["ce_task_id"]}`: **SUCCESS**.',
 f'- Análisis `{r["exact_quality"]["analysis_id"]}`: **gate OK**.',
 '- Cobertura nueva **88,7 %**, duplicación nueva **0 %**, **cero violaciones nuevas**.',
 '- Cobertura global **93,2 %**; cero bugs, vulnerabilidades y hotspots; **siete smells heredados** activos.',
 '- Deuda: **23 minutos**. Complejidad: **153**; cognitiva: **114**. `ncloc`: **784**; líneas Sonar: **1292**; calificaciones A.','',
 'Se comprobaron los hashes de XML y LCOV usados por el análisis. El gate es el gate independiente del estudio; no se sustituye por otra configuración ni se ocultan los hallazgos heredados. No se infiere una puntuación de escalabilidad sin pruebas de carga.','',
 '## Invocaciones, tiempo y créditos','',
 '| ID | Propósito | CLI (s) | Agente (s) | Créditos Kiro | Aclaraciones bloqueantes |',
 '|---|---|---:|---:|---:|---:|']
purposes=['Especificación interrumpida: cuenta incorrecta','Especificación: Vibe observado',
          'Revisión nativa Spec','Implementación inicial','QA 1 interrumpida','Reintento QA 1','QA 2: temporizadores en cola']
for row,purpose in zip(m['runs'],purposes):
    text.append('|'+ '|'.join([row['label'].split('-')[0],purpose,n(row.get('duration_seconds')),
        n(row.get('agent_elapsed_seconds')),n(row.get('credits'),6),str(q[row['label']]['blocking_clarification_questions'])])+'|')
text += ['',f'**Créditos conocidos: {n(m["known_credits"],6)}.** Los créditos finales de 01 y 05 permanecen desconocidos.',
 f'Tiempo CLI conocido: **{n(m["known_launcher_duration_seconds"])} s**; falta la duración de 05. Tiempo de agente conocido: **{n(m["known_agent_elapsed_seconds"])} s**; faltan 01 y 05. Son sumas de intervalos acreditados, no la duración total del proyecto.',
 '', 'Tokens de entrada, caché, salida y razonamiento: **ND**. Intentos, errores y éxitos API: **ND**. Los requestIds se conservan como identificadores y no se convierten en contadores API. La ocupación del contexto tampoco se suma como consumo de tokens.',
 '', 'La pregunta de 05 fue una confirmación del alcance del workflow. Se eligió la opción ofrecida de completar todo mediante la autorización existente; no hubo una nueva respuesta humana. En 02 se conserva además una referencia de confirmación no bloqueante. Todos los mensajes naturales Say de los siete intervalos fueron revisados; Reasoning queda fuera del recuento.',
 '', '**Tres intentos externos de corrección, para dos intenciones distintas.** Los dos ciclos Sonar conocidos dentro de 04 se informan aparte; no se presentan como el total de todas las correcciones internas.','',
 '## Artefactos y deltas','',
 '| Alcance | Archivos | Líneas | Caracteres Unicode/LF |','|---|---:|---:|---:|']
for label,key in [('Fuente propia de etapa 1','source_baseline'),('Fuente de etapa 2, con tests/config','source_current'),
                  ('Specs nativas heredadas','spec_stage1_copy'),('Feature nativo de etapa 2','spec_stage2')]:
    item=m[key];text.append(f'|{label}|{item["files"]}|{item["lines"]}|{item["characters"]}|')
text += ['', 'Densidad: **99,76 líneas por archivo fuente**, y **295,33 por artefacto nativo del feature**. Delta fuente: **+2552 / −68 líneas**; neto **+2484 líneas y +85906 caracteres**. El delta compara estados retenidos; no reconstruye el volumen acumulado de edición.',
 '', 'Los manifiestos y la configuración se cuentan aparte y no se suman dos veces a la fuente. Se excluyen dependencias, builds, cachés, documentación del investigador y Git. Los SHA-256 se calculan sobre los bytes originales; los recuentos de texto normalizan LF y eliminan BOM.',
 '', 'El corpus previsto para BERTopic contiene únicamente los **tres Markdown nativos del feature de etapa 2**. No se ha entrenado un modelo de temas ni se atribuyen temas o embeddings no calculados.','',
 '## Catálogo común de aceptación','',
 '| ID | Criterio | Resultado y mecanismo |','|---|---|---|']
for row,name in zip(catalog['cases'],names):
    number=int(row['id'][-2:])
    if number in [6,7]: method='PASS — fixture aislado de dominio; no se afirma alcanzabilidad en juego sin rotación.'
    elif number==17: method='PASS — navegador real, capturas y observaciones de HUD/controles.'
    elif number==18: method='PASS — tests nativos y cinco controles externos con transporte diferido y temporizadores; captura/traza del cruce real.'
    elif number==19: method='PASS de comportamientos de regresión — 38 pruebas originales pasan; una igualdad de esquema cerrado incompatible se conserva como fallo esperado.'
    elif number==20: method='PASS — build independiente y versiones registradas.'
    else: method='PASS — HTTP real o engine/serializer real con estado controlado; referencias exactas en el JSON del catálogo.'
    text.append(f'|{row["id"]}|{name}|{method}|')
text += ['', 'La limpieza de tres/cuatro filas se verifica por fórmula en fixtures de dominio con filas prefijadas completas y una pieza canónica. Estos casos se separan de la aceptación de gameplay normal. No se publica una tasa exclusivamente visual a partir de este catálogo mixto.','',
 '## Límites y desviaciones registradas','',
 '- 01 se interrumpió por cambio de cuenta. 02 emitió Vibe pese al flag Spec. Desde 03 se acredita Spec/Auto por ACP antes de cada prompt. Auto no revela el modelo de backend resuelto ni consumo por rol auxiliar.',
 '- 05 no conserva cierre nativo: final, duración y exit son desconocidos. El límite superior de observación sirve para auditar el tramo retenido; el tiempo fuera de línea no se atribuye al agente ni a facturación.',
 '- Las 39 pruebas Stage1 originales, sin editar, dan 38 PASS y un FAIL de igualdad cerrada de cuatro claves. La etapa 2 exige siete claves nuevas. La copia de etapa 2 amplió esa expectativa tras revisar sus specs; no se afirma que las 39 originales pasen sin cambios.',
 '- En 04 se corrigieron findings estilísticos sin revisión previa de specs, según su registro. Esa parte no acredita el procedimiento spec-first. En 07 sí se revisaron los tres artefactos antes del código.',
 '- Se conservan los fallos de concurrencia anteriores, los dos análisis Sonar fallidos, las auditorías vulnerables, los errores de preparación/sandbox y los resultados corregidos.',
 '- CLI 01: 2.25.0; desde 02: 2.33.0. Vite se actualizó de 5.4.11 a 8.3.5; Vitest/coverage-v8 4.1.12 y plugin-react 6.1.2. React 18.3.1, TypeScript 5.6.3 y Python 3.10.11 se conservan. Las versiones, fechas y el modelo opaco limitan comparaciones causales entre herramientas.',
 '- El trabajo del investigador/Codex —helpers, revisión, verificación, navegador y documentos— está fuera de los créditos y tiempos de generación Kiro.',
 '', '## Control de energía y estado del proyecto','',
 'Por la nueva instrucción del 23 de octubre se reactivó la tarea Windows existente, con repetición horaria. La ejecución normal verificada terminó con código 0 y decisión continuar. Solo una cuota Codex válida agotada habilita la suspensión normal; los datos desconocidos no equivalen a cero y no se usan restablecimientos. El historial de cancelación se conserva en `shared/quota-monitor/`.',
 '', 'El código permanece **local, sin commits ni subidas al repositorio**. Tessl y BMAD siguen pausados hasta nuevas credenciales/autorización.',
 '', '## Referencias locales','',
 '- `metrics.json`, `input-audit.json`, `question-audit.json` y `RESEARCH_LOG.md`.',
 '- `researcher-verification/final-07/verification-summary.json`.',
 '- `acceptance/final/catalog.json`, informes HTTP/dominio/browser y controles de concurrencia.',
 '- `sonar-verification.json`, `stage2-frontend-result-07.json`, capturas y transcripts identificados por hash.',
 '- La publicación en Drive y el snapshot final se registran después de verificar la maquetación del documento.']
(DOCS/'FINAL_REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
print('Readable final Markdown report written from verified JSON')
