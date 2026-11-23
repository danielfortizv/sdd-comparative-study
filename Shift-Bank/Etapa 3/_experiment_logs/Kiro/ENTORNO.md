# Entorno de ejecución — Etapa 3 (Kiro)

- **Etapa:** 3 (Kiro)
- **Tarea:** 2 (auto) — Preparar la captura de evidencia experimental de la Etapa 3
- **Tipo:** SETUP / EVIDENCIA (no se modificó código de aplicación, pruebas ni SEED-3.md)
- **Fecha/hora de captura:** 2026-11-16 15:39:53 (timestamp de verificación: 20261116-153953)
- **Objetivo:** Registrar las versiones del sistema operativo y del entorno de ejecución
  que se usan como contexto para toda la evidencia experimental de la Etapa 3.

---

## Versiones del entorno

| Herramienta | Versión                           |
|-------------|-----------------------------------|
| Python      | 3.13.2                            |
| Node.js     | v24.19.0                          |
| npm         | 11.17.0                           |
| OS          | Microsoft Windows NT 10.0.26300.0 |

## Comando usado (re-ejecutado para confirmar)

```powershell
python --version; node --version; npm --version; [System.Environment]::OSVersion.VersionString
```

## Salida cruda (verbatim)

```
Python 3.13.2
v24.19.0
11.17.0
Microsoft Windows NT 10.0.26300.0
```

---

## Notas

- Estos valores se re-ejecutaron el 2026-11-16 y coinciden con los capturados en la
  sesión del Hito 0 (`sesiones/20261116-153800_M0-baseline-regresion-heredada.md`).
- Si en una sesión posterior cambia cualquiera de estas versiones, se debe generar un
  nuevo documento de entorno con sufijo de timestamp (p. ej. `ENTORNO-20261116-153953.md`)
  en lugar de sobrescribir este archivo.
