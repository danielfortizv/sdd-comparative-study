#!/bin/sh
# Entrypoint del backend de Shift Bank (Etapa 3, Tarea 25).
#
# Responsabilidad única: enlazar la ruta COMPUTADA de config.DB_PATH (/app/shift_bank.db)
# hacia el directorio de datos persistente respaldado por el volumen Docker (/data), y
# luego ceder el control al proceso de la app (uvicorn vía CMD). No valida claves ni corre
# migraciones: eso lo hace el `lifespan` de la app de forma fail-closed e idempotente
# (R12.2/R12.4) una vez que uvicorn arranca.
#
# El symlink se crea en runtime (no en build) porque el volumen se monta al iniciar el
# contenedor. Es idempotente: si el symlink ya apunta a /data no hace nada.
set -eu

DATA_DIR="/data"
DB_LINK="/app/shift_bank.db"
DB_TARGET="${DATA_DIR}/shift_bank.db"

# Asegurar el directorio de datos (el volumen puede montarse vacío).
mkdir -p "${DATA_DIR}"

# (Re)crear el symlink DB_PATH -> volumen de forma idempotente.
#  - Si /app/shift_bank.db ya es un symlink correcto, no se toca.
#  - Si existe un archivo regular ahí (no debería, el .dockerignore excluye *.db), se
#    respeta /data como fuente de verdad y se reemplaza por el symlink.
if [ -L "${DB_LINK}" ]; then
    current="$(readlink "${DB_LINK}")"
    if [ "${current}" != "${DB_TARGET}" ]; then
        ln -sfn "${DB_TARGET}" "${DB_LINK}"
    fi
else
    # Quitar cualquier archivo/dir residual en la ruta del symlink (no la DB del volumen).
    rm -rf "${DB_LINK}"
    ln -s "${DB_TARGET}" "${DB_LINK}"
fi

# Ceder el control al CMD (uvicorn). `exec` conserva PID 1 -> señales/stop limpios para
# el apagado del scheduler en el lifespan (R10.2).
exec "$@"
