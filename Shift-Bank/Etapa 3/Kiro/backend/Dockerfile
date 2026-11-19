# Dockerfile del backend de Shift Bank (Etapa 3, Tarea 25).
#
# Decisión D-E3-04 (despliegue local con Docker Compose; solo verificación local, sin
# hosting externo/K8s/CI-CD). Diseño §4.1: imagen Python slim, instala SOLO
# requirements.txt (incluye cryptography), corre uvicorn como usuario NO root,
# healthcheck de salud, y persiste la DB SQLite en el volumen montado en la ruta de
# DB_PATH. Los secretos (SHIFT_ENC_KEYS / SHIFT_ENC_ACTIVE_KID / SHIFT_AUDIT_HMAC_KEY /
# SHIFT_ADMIN_TOKEN) NO se hornean: se inyectan por entorno en runtime (Tarea 27, R2.1).
#
# ------------------------------------------------------------------------------
# Mecanismo DB_PATH -> volumen (sin cambiar código de la app):
#
# `config.DB_PATH` es una constante COMPUTADA:
#     Path(__file__).resolve().parent.parent / "shift_bank.db"
# donde `__file__` es `app/config.py`. Por tanto `DB_PATH` = (directorio que CONTIENE el
# paquete `app`) / "shift_bank.db". En esta imagen el paquete vive en /app/app, así que
# DB_PATH resuelve a /app/shift_bank.db.
#
# No se puede montar el volumen directamente en /app (sombrearía el código). Solución
# limpia y sin tocar código: un directorio de datos dedicado /data respaldado por el
# volumen Docker nombrado, y un symlink /app/shift_bank.db -> /data/shift_bank.db. SQLite
# sigue el symlink, de modo que el archivo de base de datos (y sus sidecars WAL/SHM) vive
# en el volumen persistente mientras el código permanece intacto. El symlink se
# (re)crea en cada arranque vía el entrypoint, porque el volumen se monta al iniciar el
# contenedor (después del build). Honra §4.1 ("monta el volumen en la ruta de DB_PATH")
# sin hornear la DB (R12.5) ni requerir una nueva variable de entorno en el código.
# ------------------------------------------------------------------------------

FROM python:3.12-slim

# No escribir .pyc; flush inmediato de stdout/stderr para logs de contenedor legibles.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Puerto interno de uvicorn. NO se publica al host aquí: en Compose solo Nginx expone
# 443/80; el backend queda en la red interna aislada (DT-9, R11.2). Documentativo.
ENV APP_PORT=8000

WORKDIR /app

# curl: usado por el HEALTHCHECK para consultar el endpoint de salud (GET /api/accounts).
# Se instala con una capa mínima y se limpian las listas de apt.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Usuario NO root (R11.4, AC-13). UID/GID fijos para ownership estable del volumen.
RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin appuser

# Instalar SOLO las dependencias de runtime (NO requirements-dev.txt: pytest/httpx/locust/
# coverage son dev-only y no deben entrar en la imagen de producción, R18).
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el paquete de la aplicación. El .dockerignore ya excluye *.db, .env, .venv,
# tests/, requirements-dev.txt y certs, de modo que ni la DB histórica ni secretos se
# hornean (R12.5).
COPY app ./app

# Directorio de datos dedicado, respaldado por el volumen persistente en runtime. Se crea
# con ownership del usuario no root: al montar un volumen Docker nombrado VACÍO, Docker
# copia el ownership del punto de montaje de la imagen, por lo que `appuser` podrá escribir
# la DB sin correr como root.
RUN mkdir -p /data && chown -R appuser:appuser /data /app

# Entrypoint: (re)crea el symlink DB_PATH -> /data al arrancar (tras montarse el volumen),
# luego lanza uvicorn. El lifespan de la app valida las claves (fail-closed) y ejecuta las
# migraciones idempotentes antes de servir tráfico (R12.2/R12.4).
COPY --chown=appuser:appuser docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER appuser

# El volumen persistente se monta aquí (la ruta real de la DB es el symlink /app/shift_bank.db).
VOLUME ["/data"]

EXPOSE 8000

# Healthcheck de salud (R13.1, AC-12): consulta un GET existente y liviano. La app NO
# expone un endpoint /health dedicado; el probe usa `GET /api/accounts` (la misma ruta que
# el runner de carga usa como sonda de salud). Si el arranque falla-cerrado por claves
# ausentes/ inválidas, uvicorn no sirve y el healthcheck queda `unhealthy` (R12.2).
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS "http://127.0.0.1:${APP_PORT}/api/accounts" || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
