# Tessl — Etapa 2 — Análisis inicial de SonarQube

## Identificación

- Proyecto: Shift Bank — Stage 2 — Tessl.
- Fecha: 13 de noviembre de 2026.
- Project Key: `Shift-Bank---Stage-2---Tessl`.
- SonarQube Community Build: `26.9.0.129388`.
- SonarScanner CLI: `8.1.0.6389`.
- Versión del proyecto analizado: `2.0-initial`.
- Resultado del procesamiento: `SUCCESS`.
- ID de análisis: `cd49d2f3-c81a-4a60-9170-23fb30f882e7`.
- Etapa del desarrollo: implementación inicial, anterior a las correcciones humanas posteriores a la auditoría.

## Resultados cuantitativos

| Métrica | Resultado |
|---|---:|
| Archivos indexados | 57 |
| Lenguajes | Python, TypeScript, CSS |
| Líneas de código no comentadas (`ncloc`) | 4.230 |
| Líneas totales (`lines`) | 4.966 |
| Bugs — API tradicional | 0 |
| Vulnerabilidades — API tradicional | 0 |
| Code smells — API tradicional | 51 |
| Deuda técnica (`sqale_index`) | 276 minutos |
| Complejidad cognitiva | 329 |
| Duplicación | 0,8 % |
| Cobertura importada | 0,0 % |
| Quality Gate | OK, sin condiciones configuradas |

### Clasificación visual MQR

En el dashboard de código global se observaron:

- Seguridad: 0 incidencias, rating A.
- Fiabilidad: 26 incidencias, rating C.
- Mantenibilidad: 42 incidencias, rating A.
- Security Hotspots: 0.

La clasificación MQR se registra separadamente de las métricas tradicionales de la API. Sus conteos no se agregan entre sí para calcular una cantidad total de defectos únicos.

## Comparación con la Etapa 1

| Métrica | Etapa 1 | Etapa 2 inicial | Diferencia |
|---|---:|---:|---:|
| LOC SonarQube | 2.182 | 4.230 | +2.048 |
| Líneas totales | 2.585 | 4.966 | +2.381 |
| Code smells tradicionales | 21 | 51 | +30 |
| Deuda técnica | 82 min | 276 min | +194 min |
| Complejidad cognitiva | 98 | 329 | +231 |
| Duplicación | 0,0 % | 0,8 % | +0,8 puntos porcentuales |

La densidad de code smells tradicionales pasó de aproximadamente 9,62 a 12,06 por cada 1.000 LOC SonarQube.

Esta comparación es descriptiva y utiliza las métricas tradicionales de la API. No se mezclan las clasificaciones MQR con los conteos clásicos.

## Advertencias

El análisis generó dos advertencias:

1. No se detectó automáticamente un proveedor SCM.
2. La versión específica de Python no se configuró, por lo que el análisis consideró compatibilidad general con Python 3.

No se detectaron errores que impidieran finalizar el escaneo.

El Quality Gate devolvió `OK` con cero condiciones configuradas. Por tanto, no demuestra el cumplimiento de umbrales específicos.

La cobertura del 0,0 % indica que no se importó información de cobertura a SonarQube, aunque el agente había reportado 66 pruebas automatizadas aprobadas.

SonarQube Community Build ofrece análisis de seguridad limitado; cero vulnerabilidades reportadas no equivale a una certificación de seguridad.

## Conclusión

La medición inicial de calidad estática de Tessl en la Etapa 2 finalizó correctamente.

El volumen de código analizado aumentó considerablemente respecto de la Etapa 1. También aumentaron los code smells, la deuda técnica y la complejidad cognitiva.

El dashboard MQR identificó 26 incidencias que afectan a la fiabilidad y asignó rating C, aunque las métricas tradicionales devolvieron cero bugs.

Esta medición se conserva como evidencia del estado inicial generado por el agente. Los resultados posteriores a correcciones deberán registrarse por separado y no sustituir este análisis.