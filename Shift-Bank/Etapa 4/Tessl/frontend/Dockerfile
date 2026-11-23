# Multi-stage Docker build for React Frontend
# Stage 1: Build production static bundle
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve compiled artifacts with Nginx as non-root user
FROM nginx:alpine

# Support running as unprivileged user 'nginx'
RUN touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid /var/cache/nginx /var/log/nginx /etc/nginx/conf.d

COPY --from=builder /app/dist /usr/share/nginx/html

USER nginx

EXPOSE 8080 8443

CMD ["nginx", "-g", "daemon off;"]
