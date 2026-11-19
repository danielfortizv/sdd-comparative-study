# Dockerfile multistage del frontend de Shift Bank (Etapa 3, Tarea 26).
#
# Decisión D-E3-04 (despliegue local con Docker Compose; TLS termina en Nginx; reverse-proxy de
# /api al backend por la red interna; redirección HTTP->HTTPS; solo verificación local).
# Diseño §1.7, §4.1, §4.2.
#
# Etapa 1 (build): Node compila el frontend Vite+React+TS (`npm ci` + `npm run build`), que
#   ejecuta `tsc && vite build` y emite assets estáticos a `dist/`. El build usa el DEFAULT
#   RELATIVO de la API (sin VITE_API_BASE_URL): el navegador llamará a `/api/...` contra el mismo
#   origen HTTPS y Nginx hará reverse-proxy al backend (ver src/api/client.ts).
# Etapa 2 (runtime): imagen `nginx` que sirve esos assets estáticos, termina HTTPS con los certs
#   MONTADOS (no horneados; ver .dockerignore) y hace proxy de /api al servicio `backend` de la
#   red interna de Compose (nombre de upstream cableado en docker-compose.yml, Tarea 27).

# ------------------------------------------------------------------------------
# Etapa 1 — build de los assets estáticos con Node.
# ------------------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Instalar dependencias de forma reproducible a partir del lockfile (`npm ci`). Se copian
# primero los manifiestos para aprovechar la cache de capas de Docker.
COPY package.json package-lock.json ./
RUN npm ci

# Copiar el resto del contexto del frontend (el .dockerignore excluye node_modules, dist, .env,
# certs, etc.) y construir. `npm run build` = `tsc && vite build`; la salida queda en dist/.
COPY . .
RUN npm run build

# ------------------------------------------------------------------------------
# Etapa 2 — runtime Nginx sirviendo los assets estáticos + TLS + proxy /api.
# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# Reemplazar la config por defecto por la nuestra (HTTPS 443, redirección 80->443, SPA fallback,
# reverse-proxy de /api -> http://backend:8000). Se coloca como server único en conf.d.
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/shift-bank.conf

# Copiar SOLO los assets compilados desde la etapa de build (no se incluyen node_modules ni
# código fuente en la imagen de runtime).
COPY --from=build /app/dist /usr/share/nginx/html

# Puntos de montaje documentados (se montan en runtime vía docker-compose, Tarea 27):
#   - /etc/nginx/certs : certificados TLS (server.crt + server.key) provisionados externamente,
#     NUNCA horneados en la imagen (R4.4, ver .dockerignore).
# El directorio se crea con permisos legibles para el usuario `nginx` (uid/gid 101 en la imagen
# oficial), de modo que los workers no privilegiados puedan leer el material montado.
RUN mkdir -p /etc/nginx/certs \
    && chown -R nginx:nginx /etc/nginx/certs /usr/share/nginx/html

# Modelo de privilegios (R11.4 "no root donde sea factible"):
#   La imagen oficial de Nginx arranca su proceso MAESTRO como root únicamente para poder enlazar
#   los puertos PRIVILEGIADOS 80 y 443 (requisito del kernel para puertos < 1024); acto seguido
#   los procesos WORKER que atienden el tráfico se ejecutan como el usuario NO privilegiado
#   `nginx` (directiva `user nginx;` del nginx.conf principal de la imagen). Así, el manejo real
#   de peticiones ocurre sin privilegios. No se usa la variante unprivileged (que escucha en
#   8080/8443) para conservar el contrato de exponer 80/443 directamente (diseño §4.2); el
#   compromiso queda documentado aquí y en la evidencia.

# 80 (redirección) y 443 (HTTPS). Documentativo: el mapeo al host lo hace Compose (Tarea 27).
EXPOSE 80 443

# Healthcheck liviano: el server HTTPS responde a la raíz (SPA). Se usa --insecure porque el
# certificado es autofirmado/ provisionado externamente (solo verificación local, D-E3-04).
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD wget --no-verbose --tries=1 --no-check-certificate -O /dev/null https://127.0.0.1/ || exit 1

# `daemon off;` lo fija la imagen oficial en su CMD por defecto; se mantiene.
CMD ["nginx", "-g", "daemon off;"]
