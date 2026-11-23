# Stage 1: Build static site
FROM node:24-alpine AS builder

WORKDIR /app

# Copy package descriptors and lockfile
COPY package.json package-lock.json ./

# Install dependencies reproducing package-lock
RUN npm ci

# Copy application source files
COPY . .

# Compile and build the production static files
RUN npm run build

# Stage 2: Serve using non-root Nginx
FROM nginx:1.27-alpine AS runner

# Remove default configuration and static files
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/* /etc/nginx/nginx.conf

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy production static files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Grant ownership to the non-root nginx user (UID 101)
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx

USER nginx

EXPOSE 5183

CMD ["nginx", "-g", "daemon off;"]
