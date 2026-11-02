# Control verificado de Spec/Auto mediante ACP

El headless normal pidió Spec, pero su configuración nativa registró Vibe en los intentos01/02. Se prepara un transporte investigador, sin cambiar aplicación/specs, para comprobar la configuración **antes** de entregar la semilla.

La [migración oficial de Kiro a ACP V3](https://kiro.dev/docs/cli/v3/acp-migration/) documenta arrancar `kiro-cli acp --agent-engine=v3`, usar autenticación CLI y seleccionar opciones anunciadas después de inicializar. El driver usa `initialize`, `session/new` y `session/set_config_option` para `mode=spec` y `model=auto`; exige que ambos valores existan en las opciones y que el servidor los devuelva activos. No utiliza métodos privados, credenciales copiadas ni configuración de billing. El formato de `session/prompt` usa el campo `prompt` del [protocolo ACP](https://agentclientprotocol.com/protocol/v1/prompt-turn).

## Preflight ejecutado sin inferencia

- CLI2.33.0, SHA-256 BC711541FC139D5E5FC8E07FC8FA13E9239ED039862F4A9D55C0E344BAC7C3F8.
- Primer intento en sandbox: acceso denegado antes de inicializar; evidencia conservada.
- Mismo control fuera del sandbox: exit0; sesión sess_4687607e-2d7f-4d7d-9273-46f15f2407aa; servidor confirma **Spec y Auto**.
- **Ningún `session/prompt` enviado**. No se atribuye esta configuración a una invocación generadora ni se incorpora al consumo.

Evidencia privada: `researcher-setup/acp-spec-auto-preflight-unsandboxed.acp-preflight.json`, `.rpc.jsonl`, `.stdout.jsonl`, `.stderr.txt`. No se alteró el proceso02.

## Uso acotado

`shared/run-kiro-acp.py --label <nuevo>` solo inicializa, crea/configura sesión y sale. Para generación, el proceso principal debe añadir explícitamente `--execute --prompt-file <prompt revisado>`. El driver exige hash de semilla congelada, bloque completo, versión pin y configuración verificada. Una etiqueta nunca se sobrescribe. No se ejecutó esta ruta de inferencia durante el preflight; su primer uso real requiere verificar entrada y resultado conservados.

`--allow-tools` solo sirve junto con ejecución explícita: responde con una opción `allow_once` realmente ofrecida; no persiste permisos. Sin ese flag cancela aprobaciones. El cliente no implementa terminal ni escritura de archivos por RPC; las herramientas propias del agente permanecen bajo su flujo normal.

Durante una ejecución real, las notificaciones se conservan como `sessionUpdate`, con sobre investigador `runStarted`; `runFinished` se emite al responder la solicitud de prompt, no ante un metadato intermedio de turno. Los JSON-RPC se preservan por separado para atribuir esa normalización. El código de transporte no acredita aceptación funcional. La configuración Auto no revela el modelo de backend resuelto.

La ejecución requiere también --phase (specify/spec_revision/implement/clarify). Registra SHA del prompt, fase y seed congelada. RPC OK y resultado de generación se separan: solo stopReason=end_turn emite success/exit0; refusal/cancelled/otro estado conserva stopReason y emite refused/cancelled/incomplete con exit2. Esperas o marcas del workflow no se fuerzan mediante métodos privados; verificar Spec/Auto no acredita fases/aprobaciones ni tareas completadas.
