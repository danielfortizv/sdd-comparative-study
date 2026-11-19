# Evidencia — Etapa 3 (Kiro) · Tarea 3

**Tarea:** (auto) Añadir `cryptography` (runtime) y `locust` (solo dev) con versiones fijadas.
**Fecha/hora (local):** 2026-11-16 15:42:58
**Requisitos:** R18.1, R18.2 · **Diseño:** §Módulos afectados · **AC:** AC-02, AC-10

## Entorno

| Elemento | Valor |
|----------|-------|
| SO | Windows (win32) |
| venv | `backend/.venv` (creada en Tarea 1) |
| Python | 3.13.2 |
| pip | 26.3 |

## Versiones fijadas (exactas)

Las versiones se resolvieron instalando en la `.venv` existente (resolver de pip, compatible con
Python 3.13) y se pinnearon al valor exacto instalado.

| Paquete | Versión pinneada | Archivo | Tipo |
|---------|------------------|---------|------|
| `cryptography` | `50.0.2` | `requirements.txt` | runtime (cifrado de campos AES-256-GCM) |
| `locust` | `2.47.0` | `requirements-dev.txt` | solo dev (prueba de carga) |

No se añadió ninguna otra dependencia de runtime. Las entradas previas se conservaron intactas
(`fastapi==0.115.5`, `uvicorn==0.32.1`, `pydantic==2.10.3`; `pytest==8.3.4`, `httpx==0.28.1` y el
include `-r requirements.txt`). Las dependencias transitivas de `locust` quedan en la venv pero
NO se declaran como runtime (no entran en `requirements.txt`).

## Comandos y salidas de verificación (reales)

### 1. Versiones de entorno
```
> .venv\Scripts\python.exe --version
Python 3.13.2
> .venv\Scripts\python.exe -m pip --version
pip 26.3 from ...\.venv\Lib\site-packages\pip (python 3.13)
```

### 2. Resolución de versiones (instalación en la venv)
```
> .venv\Scripts\python.exe -m pip install cryptography locust
...
Successfully installed ... cryptography-50.0.2 ... locust-2.47.0 ...
Exit Code: 0
```

### 3. Import de cryptography y versión de locust
```
> .venv\Scripts\python.exe -c "import cryptography; print('cryptography', cryptography.__version__)"
cryptography 50.0.2
> .venv\Scripts\locust.exe --version
locust 2.47.0 from ...\.venv\Lib\site-packages\locust (Python 3.13.2)
```

### 4. Instalación limpia desde requirements-dev.txt (resuelve con pines)
```
> .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Requirement already satisfied: fastapi==0.115.5 ...
Requirement already satisfied: cryptography==50.0.2 ...
Requirement already satisfied: locust==2.47.0 ...
Exit Code: 0
```

### 5. La app sigue importando igual que antes
```
> .venv\Scripts\python.exe -c "import app.main; print('app.main imports OK')"
app.main imports OK
```

### 6. Regresión heredada completa (Pytest)
```
> .venv\Scripts\python.exe -m pytest -q
...
220 passed, 1 warning in 14.68s
Exit Code: 0
```
(El único warning es un `DeprecationWarning` preexistente de Starlette/anyio en `testclient`, no
relacionado con esta tarea.)

## Resultado

PASS. `requirements.txt` tiene `cryptography==50.0.2` pinneado (runtime); `requirements-dev.txt`
tiene `locust==2.47.0` pinneado (solo dev). No se introdujeron otras dependencias de runtime. La
instalación resuelve en entorno limpio, `cryptography` importa, `locust --version` funciona, la
app importa igual que antes y la regresión heredada sigue en 220 passed.
