# Multi-stage production Dockerfile for the React frontend
# Stage 1: Build React static assets using Vite
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency definition files
COPY package*.json ./

# Clean install of all dependencies
RUN npm ci

# Copy configuration files and source code
COPY postcss.config.js tailwind.config.js tsconfig.json vite.config.ts index.html ./
COPY src ./src

# Build production distribution
ENV VITE_API_URL=http://localhost:8000/api/v1/evaluate
RUN npm run build

# Stage 2: Serve compiled assets with Nginx
FROM nginx:1.25-alpine AS runner

# Remove default configuration and assets
RUN rm -rf /usr/share/nginx/html/* && rm /etc/nginx/conf.d/default.conf

# Copy compiled assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our optimized, security-hardened nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
