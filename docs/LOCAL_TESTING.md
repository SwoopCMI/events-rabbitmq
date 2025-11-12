# 🧪 Local Testing Guide

## Quick Start

### 1️⃣ Build and Run with Docker Compose

```bash
# Build and start
docker-compose up --build

# Or run in detached mode
docker-compose up --build -d

# View logs
docker-compose logs -f
```

### 2️⃣ Configure Environment (Optional)

Copy and edit the environment file:

```bash
cp .env.example .env
# Edit .env with your settings
```

**For local testing without Slack alerts**, leave `SLACK_WEBHOOK_URL` empty or unset.

---

## 🔍 Verification Steps

### Check RabbitMQ is Running

```bash
# Check running processes
docker-compose exec rabbitmq ps aux

# Should see rabbitmq-server and python monitor.py processes
# Both running as rabbitmq user (not root)
```

### Access Management UI

Open in browser: **http://localhost:15672**

- Username: `rabbitmq` (or value from `.env`)
- Password: `testpassword123` (or value from `.env`)

### Check Prometheus Metrics

```bash
curl http://localhost:15692/metrics
```

You should see Prometheus-style metrics output.

### Verify Monitoring Script

```bash
# Check monitor logs
docker-compose logs -f rabbitmq | grep -i monitor

# You should see:
# ✅ RabbitMQ is ready! Starting monitoring...
# 🚀 Starting comprehensive RabbitMQ monitoring...
# 🟢 RabbitMQ Monitoring Started
```

---

## 🧪 Test Alert Scenarios

### Test 1: Create a Queue with Many Messages

```python
# test_queue_backup.py
import pika
import os

credentials = pika.PlainCredentials('rabbitmq', 'testpassword123')
connection = pika.BlockingConnection(
    pika.ConnectionParameters('localhost', 5672, '/', credentials)
)
channel = connection.channel()

# Create queue and publish 1500 messages (threshold is 1000)
channel.queue_declare(queue='test_queue', durable=True)

for i in range(1500):
    channel.basic_publish(
        exchange='',
        routing_key='test_queue',
        body=f'Message {i}'
    )
    if i % 100 == 0:
        print(f"Published {i} messages...")

print("✅ Published 1500 messages - should trigger alert!")
connection.close()
```

Run it:
```bash
pip install pika
python tests/test_queue_backup.py
```

**Expected**: Slack alert about queue backup (if webhook configured)

### Test 2: Check Process Auto-Restart

```bash
# Container will auto-restart if it crashes (Docker handles this)
docker-compose restart rabbitmq

# Monitor logs - should see clean startup
docker-compose logs -f rabbitmq
```

### Test 3: Check Memory Thresholds

Lower the threshold temporarily to test alerts:

```bash
# Stop container
docker-compose down

# Edit docker-compose.yml or .env
# Set ALERT_MAX_MEMORY_PERCENT=10

# Restart
docker-compose up -d

# Check logs for memory alerts
docker-compose logs -f
```

---

## 🐛 Debugging

### View Logs

```bash
# All container logs
docker-compose logs -f rabbitmq

# Filter for monitoring
docker-compose logs -f rabbitmq | grep -i monitor

# Filter for errors
docker-compose logs -f rabbitmq | grep -i error
```

### Interactive Shell

```bash
# Get a shell in the container
docker-compose exec rabbitmq bash

# Check processes (should run as rabbitmq user, not root)
ps aux | grep -E "rabbitmq|python"

# Verify user
whoami  # Should output: rabbitmq

# Test monitor script manually (uses venv)
/opt/venv/bin/python /usr/local/bin/monitor.py
```

### Check RabbitMQ API Directly

```bash
# Overview
curl -u rabbitmq:testpassword123 http://localhost:15672/api/overview | jq

# Queues
curl -u rabbitmq:testpassword123 http://localhost:15672/api/queues | jq

# Nodes
curl -u rabbitmq:testpassword123 http://localhost:15672/api/nodes | jq
```

### Test Without Slack

If you don't have a Slack webhook, the monitor will log warnings but continue:

```bash
# Monitor will show:
# WARNING - No Slack webhook URL configured, skipping alert
```

This is normal for local testing.

---

## 🧹 Cleanup

```bash
# Stop containers
docker-compose down

# Remove volumes (deletes all queues/messages)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

---

## 📊 Expected Behavior

### ✅ Healthy Startup

```
rabbitmq_1  | 🚀 Starting RabbitMQ with monitoring (running as rabbitmq user)...
rabbitmq_1  | 📡 Starting RabbitMQ server...
rabbitmq_1  | ... [RabbitMQ startup logs] ...
rabbitmq_1  | ⏳ Waiting for RabbitMQ Management API to be ready...
rabbitmq_1  | ✅ RabbitMQ is ready! Starting monitoring...
rabbitmq_1  | 🚀 Starting comprehensive RabbitMQ monitoring (interval: 60s)
rabbitmq_1  | 🔍 Running comprehensive RabbitMQ health checks...
rabbitmq_1  | ✅ Health check completed
```

### ✅ Process Status

```bash
$ docker-compose exec rabbitmq ps aux | grep -E "rabbitmq|python"
rabbitmq  89  ... /usr/lib/erlang/erts-*/bin/beam.smp ... (RabbitMQ)
rabbitmq 156  ... /opt/venv/bin/python /usr/local/bin/monitor.py
```

### ✅ Ports Accessible

- **5672**: AMQP protocol ✅
- **15672**: Management UI ✅
- **15692**: Prometheus metrics ✅

---

## 🚀 Common Issues

### Issue: "Cannot connect to RabbitMQ API"

**Solution**: RabbitMQ is still starting. Wait 10-30 seconds.

### Issue: Monitor keeps restarting

**Solution**: Check if credentials are correct in environment variables. Check logs for connection errors.

### Issue: No Slack alerts

**Solution**: 
1. Check `SLACK_WEBHOOK_URL` is set correctly
2. This is expected if webhook is not configured (local testing)

### Issue: Port already in use

**Solution**: Stop existing RabbitMQ instances:
```bash
# Check what's using the port
lsof -i :5672
lsof -i :15672

# Stop existing containers
docker ps | grep rabbit
docker stop <container_id>
```

---

## 📝 Next Steps After Local Testing

Once everything works locally:

1. ✅ Commit your changes
2. ✅ Push to GitHub
3. ✅ Set `SLACK_WEBHOOK_URL` in Render dashboard
4. ✅ Deploy to Render
5. ✅ Monitor Render logs for successful startup
