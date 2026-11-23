# Stage 1: Build the React TypeScript application
FROM node:24-alpine AS builder

WORKDIR /build

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve the production assets with Nginx
FROM nginxinc/nginx-unprivileged:alpine AS runner

# Copy the custom Nginx proxy config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build output from builder stage
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 5183

CMD ["nginx", "-g", "daemon off;"]
