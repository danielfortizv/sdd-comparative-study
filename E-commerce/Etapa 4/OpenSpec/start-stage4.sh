#!/usr/bin/env bash
# start-stage4.sh
# Start RabbitMQ, 4 backend services, and frontend in Linux/macOS
echo "Starting Stage 4 microservices stack..."
PORT_GATEWAY=18000
PORT_IDENTITY=18001
PORT_COMMERCE=18002
PORT_REVIEWS=18003
PORT_FRONTEND=18100

export AMQP_URL="amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_openspec"
export EVENT_NAMESPACE="stage4.openspec"
export VITE_API_URL="http://127.0.0.1:18000"

python3 -m app.identity.main > identity.log 2>&1 &
echo $! > .pid_identity

python3 -m app.commerce.main > commerce.log 2>&1 &
echo $! > .pid_commerce

python3 -m app.reviews.main > reviews.log 2>&1 &
echo $! > .pid_reviews

sleep 2

python3 -m app.gateway.main > gateway.log 2>&1 &
echo $! > .pid_gateway

cd frontend
npm run dev -- --port 18100 > ../frontend.log 2>&1 &
echo $! > ../.pid_frontend
cd ..

echo "All processes started in the background."
