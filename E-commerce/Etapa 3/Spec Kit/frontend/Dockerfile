# Stage 1: Build the React application
FROM node:18-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --silent

COPY . .
# Set build-time env so it points to localhost:8000
ENV REACT_APP_API_URL=http://localhost:8000
RUN npm run build

# Stage 2: Serve the React application using Nginx
FROM nginx:1.25-alpine

# Copy built files from builder
COPY --from=builder /app/build /usr/share/nginx/html

# Custom nginx configuration to support React routing and listen on port 3000
RUN echo 'server { \
    listen 3000; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
