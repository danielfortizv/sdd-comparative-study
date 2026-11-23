# syntax=docker/dockerfile:1

# Multi-stage build for the React + TypeScript (Vite) frontend (Stage 3,
# Requirement 4.2).
#
# Stage 1 (builder) installs dependencies and produces the static production
# build. Stage 2 (runtime) serves the built static assets from a slim nginx
# image; no Node runtime ships in the final image.

# --- Stage 1: build the static assets ----------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies from the lockfile for a reproducible build.
COPY package.json package-lock.json ./
RUN npm ci

# Build the production bundle (tsc type-check + Vite build) into dist/.
COPY . .
RUN npm run build

# --- Stage 2: serve with nginx ------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# SPA-friendly config (history fallback to index.html).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static assets only.
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
