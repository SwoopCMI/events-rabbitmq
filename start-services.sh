#!/bin/bash
set -e

echo "🚀 Starting RabbitMQ with monitoring (running as $(whoami))..."

# Start RabbitMQ in background
echo "📡 Starting RabbitMQ server..."
rabbitmq-server &
RABBITMQ_PID=$!

# Wait for RabbitMQ to be ready
echo "⏳ Waiting for RabbitMQ to start..."
sleep 10

# Wait for management API to be available
until curl -s -u "${RABBITMQ_DEFAULT_USER}:${RABBITMQ_DEFAULT_PASS}" \
    "http://localhost:15672/api/overview" > /dev/null 2>&1; do
    echo "⏳ Waiting for RabbitMQ Management API..."
    sleep 5
done

echo "✅ RabbitMQ is ready!"

# Start monitoring script using venv Python
echo "👀 Starting monitoring script..."
/opt/venv/bin/python /usr/local/bin/monitor.py &
MONITOR_PID=$!

echo "🎉 Both services started successfully!"
echo "RabbitMQ PID: $RABBITMQ_PID"
echo "Monitor PID: $MONITOR_PID"

# Function to handle shutdown
cleanup() {
    echo "🛑 Shutting down services..."
    kill $MONITOR_PID 2>/dev/null || true
    kill $RABBITMQ_PID 2>/dev/null || true
    wait
    echo "✅ Cleanup complete"
}

# Handle shutdown signals
trap cleanup SIGTERM SIGINT

# Wait for either process to exit
wait $RABBITMQ_PID $MONITOR_PID