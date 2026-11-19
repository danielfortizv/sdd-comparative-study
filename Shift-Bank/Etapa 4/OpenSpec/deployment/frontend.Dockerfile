FROM node:22-alpine AS build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.28-alpine
USER root
RUN apk add --no-cache curl \
    && rm -f /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh
COPY --from=build /frontend/dist/ /usr/share/nginx/html/
COPY deployment/nginx.conf /etc/nginx/conf.d/default.conf
USER 101:101
EXPOSE 8080 8443
HEALTHCHECK --interval=10s --timeout=4s --start-period=20s --retries=6 \
  CMD curl --fail --silent --show-error --cacert /run/secrets/tls_cert https://localhost:8443/health/ready -o /dev/null

