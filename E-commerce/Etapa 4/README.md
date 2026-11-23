# Etapa 4: microservicios y eventos

Las cuatro implementaciones usan la misma semilla inicial: identidad, comercio y reseñas en procesos separados, un gateway HTTP y eventos reales de RabbitMQ. Cada servicio conserva su propio almacenamiento. BMAD queda fuera de esta etapa.

**Estado:** especificaciones y código terminados en OpenSpec, Kiro, Tessl y Spec Kit. Pasaron los recorridos locales, las pruebas con RabbitMQ real y los cuatro comandos comunes de apertura/apagado desde Windows PowerShell. La etapa 3 conserva sus hashes originales. Los servidores de prueba quedaron detenidos; RabbitMQ continúa disponible para iniciar una aplicación.

## Abrir una implementación

En PowerShell, entra en esta carpeta:

```powershell
cd "Caso 3-Ecommerce/Etapa 4"
```

Ejecuta **uno** de estos comandos según la herramienta que quieras probar. El comando inicia el broker local y después la aplicación:

```powershell
powershell -ExecutionPolicy Bypass -File .\Start-App.ps1 -Tool OpenSpec
powershell -ExecutionPolicy Bypass -File .\Start-App.ps1 -Tool Kiro
powershell -ExecutionPolicy Bypass -File .\Start-App.ps1 -Tool Tessl
powershell -ExecutionPolicy Bypass -File .\Start-App.ps1 -Tool SpecKit
```

| Herramienta | Abrir en el navegador | Gateway | Usuario moderador | Contraseña de demostración |
|---|---|---|---|---|
| OpenSpec | http://127.0.0.1:18100 | 18000 | `moderator` | `modpassword` |
| Kiro | http://127.0.0.1:18300 | 18200 | `moderator` | `moderator123` |
| Tessl | http://127.0.0.1:18500 | 18400 | `moderator` | `moderator` |
| Spec Kit | http://127.0.0.1:18700 | 18600 | `moderator` | `moderator` |

Las dependencias de las cuatro copias están preparadas en este equipo. Para reinstalarlas en otro equipo, sigue el README de cada herramienta. RabbitMQ utiliza la distribución Ubuntu de WSL ya instalada; [LocalBroker/README.md](LocalBroker/README.md) explica su arranque.

## Qué probar

1. Registra un cliente, inicia sesión, añade productos al carrito y termina una compra simulada.
2. Crea una reseña con una imagen. Debe quedar pendiente de moderación.
3. Cierra sesión y entra como moderador usando la tabla. Aprueba la reseña.
4. Comprueba su aparición pública después de la propagación del evento. Una reseña rechazada debe permanecer oculta.
5. Cierra sesión e intenta acceder a moderación con un cliente normal: debe denegar el acceso.

## Detener

Usa el mismo nombre de herramienta que utilizaste para abrirla:

```powershell
powershell -ExecutionPolicy Bypass -File .\Stop-App.ps1 -Tool OpenSpec
```

Puedes sustituir `OpenSpec` por `Kiro`, `Tessl` o `SpecKit`. Esto detiene la aplicación; el broker compartido queda disponible para probar otra herramienta. Sus puertos y vhosts están separados.

## Fuentes para el análisis posterior

`Evaluacion/` conserva la semilla común, los prompts enviados, las sesiones originales, las estadísticas nativas disponibles, las versiones y tiempos de ejecución. La cobertura XML y LCOV queda en las carpetas de cada implementación. `Evaluacion/source-manifest.json` inventaría las fuentes con SHA-256; no calcula costos ni métricas del estudio. Las intervenciones del orquestador están separadas en `Evaluacion/driver-interventions.md`.

Las especificaciones nativas se encuentran en `OpenSpec/openspec/changes/stage-4-microservices/`, `Kiro/.kiro/specs/ecommerce-stage4/`, `Tessl/specs/` y `Spec Kit/specs/004-stage4-microservices/`.

La validación se ejecuta con procesos locales y RabbitMQ real. Docker y GitHub Actions remotos no se ejecutaron en este equipo; los archivos de Compose y CI se entregan con esa limitación.

Los lanzadores comunes y el broker local son infraestructura del orquestador. Las especificaciones, los servicios, las correcciones y las pruebas de cada herramienta se generaron mediante su flujo nativo.
