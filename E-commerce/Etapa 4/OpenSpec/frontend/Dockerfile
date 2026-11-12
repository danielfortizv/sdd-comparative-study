# Stage 1: Build React Assets
FROM node:20-alpine AS builder

WORKDIR /build

# Copy package configuration
COPY package.json package-lock.json ./

# Install dependencies using npm clean install
RUN npm ci

# Copy source code and config files
COPY . .

# Set API URL build argument and environment variable
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

# Build the production-ready React application
RUN npm run build

# Stage 2: Serve via Nginx
FROM nginx:alpine AS runner

# Remove default nginx static files
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from builder stage
COPY --from=builder /build/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
