# Multi-stage frontend image (Stage 3, Option A).
#
# Node build stage produces the production bundle; the nginx runtime stage
# serves the static assets and reverse-proxies /api to the backend over the
# internal network. Runs as a non-root user distinct from the backend user.

# ---- build stage ----
FROM node:24-slim AS build

WORKDIR /app

# Install dependencies against the committed lockfile for a reproducible build.
COPY package.json package-lock.json ./
RUN npm ci

# Build the production bundle (tsc && vite build).
COPY . .
RUN npm run build

# ---- runtime stage ----
FROM nginx:alpine AS runtime

# nginx:alpine ships an unprivileged "nginx" user; use it (distinct from the
# backend "tetris" user). Adjust nginx to run fully as non-root.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Serve the built assets.
COPY --from=build /app/dist /usr/share/nginx/html

# Make the paths nginx needs writable by the non-root user.
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx && \
    touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 5183

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:5183/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
