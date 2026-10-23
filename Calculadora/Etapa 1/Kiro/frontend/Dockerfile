# syntax=docker/dockerfile:1

# Frontend image (Requirement 32): multi-stage build -> static assets served
# by Nginx with SPA fallback and an /api reverse proxy. Stage 3 task 46.

# --- Stage 1: build ---
FROM node:20-alpine AS build
WORKDIR /app
# Install deps against the lockfile for reproducible builds.
COPY package.json package-lock.json* ./
RUN npm ci
# Build the production bundle (tsc --noEmit && vite build) into /app/dist.
COPY . .
RUN npm run build

# --- Stage 2: serve ---
FROM nginx:alpine AS serve
# Replace the default site config with the SPA + /api proxy config.
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Copy only the compiled static assets from the build stage (32.1, 32.2).
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
