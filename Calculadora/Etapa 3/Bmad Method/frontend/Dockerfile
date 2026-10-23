# ==============================================================================
# Stage 1: Build Static Assets
# ==============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency files first
COPY package.json package-lock.json* ./

# Clean installation of dependencies
RUN npm ci

# Copy full application codebase
COPY . .

# Run static production build compilation
RUN npm run build

# ==============================================================================
# Stage 2: Production Nginx Server
# ==============================================================================
FROM nginx:alpine AS runner

# Remove default configuration and copy our custom lightweight config
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy production static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
