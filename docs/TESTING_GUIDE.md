# 🧪 Complete Testing Guide

This guide walks you through testing ALL aspects of the RabbitMQ monitoring system.

## 📋 Prerequisites

```bash
# Install test dependencies
pip install pika requests

# Or if you prefer poetry/pipenv
pip install -r requirements.txt pika requests
```

## 🚀 Quick Start Testing

### 1️⃣ Start RabbitMQ with Monitoring

```bash
# Build and start
docker-compose up --build -d

# Verify services are running
docker-compose exec rabbitmq ps aux

# You should see rabbitmq-server and python monitor.py processes
# Both should be running as rabbitmq user
```

### 2️⃣ Test Slack Webhook (Optional but Recommended)

```bash
1. ✅ Deploy to Render with `SLACK_WEBHOOK_URL` set
2. ✅ Test webhook: `python3 tests/test_slack_webhook.py`
```

You should see: ✅ SUCCESS! Test message sent to Slack

### 3️⃣ Run Complete Monitoring Test Suite

```bash
**5. Run the test suite**

```bash
# Run all tests
python3 tests/test_full_monitoring.py
```

---

## 🧪 Test Suite Overview

The test suite covers **10 comprehensive scenarios**:

### ✅ Test 1: RabbitMQ Connectivity
- Verifies RabbitMQ Management API is accessible
- Checks RabbitMQ version

### ✅ Test 2: Management Plugins
- Confirms management plugin is enabled (port 15672)
- Confirms Prometheus plugin is enabled (port 15692)

### ✅ Test 3: Queue Backup Alert 🚨
**Trigger:** Creates queue with 1,100+ messages (threshold: 1,000)
**Expected Alert:** "🚨 QUEUE BACKUP DETECTED"
**Wait Time:** ~70 seconds

### ✅ Test 4: Missing Consumers Alert ⚠️
**Trigger:** Queue with 150 messages but NO consumers
**Expected Alert:** "🔍 MISSING CONSUMERS"
**Wait Time:** ~70 seconds

### ✅ Test 5: Unacknowledged Messages Alert ⚠️
**Trigger:** Consumer that doesn't acknowledge 550+ messages (threshold: 500)
**Expected Alert:** "⚠️ HIGH UNACKNOWLEDGED MESSAGES"
**Wait Time:** ~70 seconds

### ✅ Test 6: Processing Halt Detection 🚨
**Trigger:** Active publishing but ZERO consumption
**Expected Alert:** "⏹️ PROCESSING COMPLETELY HALTED"
**Wait Time:** ~70 seconds

### ✅ Test 7: Node Health Monitoring
- Checks node is running
- Verifies memory usage is within threshold
- Verifies disk space is available

### ✅ Test 8: Prometheus Metrics
- Confirms metrics endpoint is accessible
- Validates key metrics are present:
  - `rabbitmq_queue_messages_ready`
  - `rabbitmq_queue_messages_unacked`
  - `rabbitmq_queue_consumers`
  - `rabbitmq_build_info`

### ✅ Test 9: Monitoring Script Status
- Verifies monitoring script is running as a process

### ✅ Test 10: Alert Cooldown Mechanism
- Tests that duplicate alerts are suppressed for 5 minutes
- Ensures you don't get spammed with repeated alerts

---

## 📊 Expected Output

### Successful Test Run

```
🧪 RabbitMQ Monitoring Test Suite
Host: localhost:5672
Monitoring Interval: 60s

============================================================
                TEST 1: RabbitMQ Connectivity              
============================================================

✅ PASS - RabbitMQ API accessible
     Version: 4.0.0

============================================================
                TEST 2: Management Plugins                 
============================================================

✅ PASS - Management plugin enabled
     Port 15672
✅ PASS - Prometheus plugin enabled
     Port 15692

... [tests continue] ...

============================================================
                      TEST SUMMARY                         
============================================================

Total Tests: 23
Passed: 23
Time: 420.5s

✅ ALL TESTS PASSED!

📨 Important: Check your Slack channel for alerts!
Expected alerts during this test:
  1. Queue backup detected
  2. Missing consumers
  3. High unacknowledged messages
  4. Processing completely halted

Note: Alerts may take up to 60s to appear
```

---

## 🔍 Manual Testing Scenarios

### Scenario A: Test Memory Alert

```bash
# Lower memory threshold temporarily
docker-compose down
export ALERT_MAX_MEMORY_PERCENT=10
docker-compose up -d

# Create memory pressure (publish large messages)
python3 << EOF
import pika
credentials = pika.PlainCredentials('rabbitmq', 'testpassword123')
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost', 5672, '/', credentials))
channel = connection.channel()
channel.queue_declare(queue='memory_test', durable=True)

# Publish 10MB messages
for i in range(100):
    channel.basic_publish(exchange='', routing_key='memory_test', body='x' * 10_000_000)
    print(f"Published {i+1} large messages")
    
connection.close()
EOF

# Wait and check Slack for memory alert
```

### Scenario B: Test Connection Failure Alert

```bash
# Stop RabbitMQ temporarily by restarting the container
docker-compose restart rabbitmq

# Wait 1-2 minutes for restart
# Monitor will detect temporary disconnection and reconnect
```

### Scenario C: Test Node Down Alert

```bash
# Simulate node crash
docker-compose stop rabbitmq

# Monitoring will stop (container stopped)
# Docker/Render will auto-restart the container
# Then restart
docker-compose start rabbitmq
```

### Scenario D: Inspect Queues Manually

```bash
# Access Management UI
open http://localhost:15672
# Login: rabbitmq / testpassword123

# Or via API
curl -u rabbitmq:testpassword123 http://localhost:15672/api/queues | jq
```

---

## 🐛 Troubleshooting Tests

### Test Fails: "RabbitMQ API not accessible"

**Solution:**
```bash
# Check if RabbitMQ is running
docker-compose ps

# Check logs
docker-compose logs rabbitmq

# Restart if needed
docker-compose restart rabbitmq
```

### Test Fails: "Prometheus plugin not enabled"

**Solution:**
```bash
# Check plugins
docker-compose exec rabbitmq rabbitmq-plugins list

# Enable if needed
docker-compose exec rabbitmq rabbitmq-plugins enable rabbitmq_prometheus
```

### No Alerts Received in Slack

**Checklist:**
1. ✅ Webhook URL is correct: `echo $SLACK_WEBHOOK_URL`
2. ✅ Test webhook: `python3 test_slack_webhook.py`
3. ✅ Check monitor logs: `docker-compose logs -f rabbitmq | grep -i monitor`
4. ✅ Verify thresholds are being exceeded
5. ✅ Wait full monitoring interval (60s default)

### Tests Taking Too Long

The test suite runs for ~7 minutes because:
- Each alert test waits 70 seconds for the monitoring interval
- This is by design to test real-world behavior

**Speed up testing:**
```bash
# Set shorter monitoring interval (ONLY for testing)
export MONITORING_INTERVAL=15
docker-compose up -d
python3 test_full_monitoring.py
```

⚠️ **Warning:** Don't use short intervals in production (causes overhead)

---

## 📈 Viewing Metrics

### Prometheus Metrics

```bash
# View all metrics
curl http://localhost:15692/metrics

# Filter specific metrics
curl http://localhost:15692/metrics | grep rabbitmq_queue_messages

# Pretty print with jq
curl http://localhost:15692/metrics | grep rabbitmq_queue_messages_ready
```

### Management API

```bash
# Overview
curl -u rabbitmq:testpassword123 http://localhost:15672/api/overview | jq

# All queues
curl -u rabbitmq:testpassword123 http://localhost:15672/api/queues | jq

# Specific queue
curl -u rabbitmq:testpassword123 http://localhost:15672/api/queues/%2F/test_queue_backup | jq

# Nodes
curl -u rabbitmq:testpassword123 http://localhost:15672/api/nodes | jq

# Connections
curl -u rabbitmq:testpassword123 http://localhost:15672/api/connections | jq
```

---

## 🔧 Testing with Custom Thresholds

```bash
# Create custom .env file
cat > .env << EOF
RABBITMQ_DEFAULT_USER=rabbitmq
RABBITMQ_DEFAULT_PASS=testpassword123
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Custom thresholds for testing
ALERT_MAX_QUEUE_LENGTH=100
ALERT_MAX_UNACKED_MESSAGES=50
ALERT_MIN_CONSUMERS=1
ALERT_MAX_MEMORY_PERCENT=70
ALERT_MAX_DISK_PERCENT=80
MONITORING_INTERVAL=30
EOF

# Restart with new config
docker-compose down
docker-compose up -d

# Run tests
python3 test_full_monitoring.py
```

---

## 📝 Test Report

After running tests, you should see these alerts in Slack:

| Alert Type | Test # | Expected Message | Status |
|-----------|--------|------------------|--------|
| Queue Backup | 3 | 🚨 QUEUE BACKUP DETECTED | ⬜ |
| Missing Consumers | 4 | 🔍 MISSING CONSUMERS | ⬜ |
| Unacked Messages | 5 | ⚠️ HIGH UNACKNOWLEDGED MESSAGES | ⬜ |
| Processing Halt | 6 | ⏹️ PROCESSING COMPLETELY HALTED | ⬜ |
| Cooldown Test | 10 | Only ONE alert (not repeated) | ⬜ |

Check off each alert as you receive it!

---

## 🧹 Cleanup After Testing

```bash
# Remove test queues
python3 << EOF
import pika
credentials = pika.PlainCredentials('rabbitmq', 'testpassword123')
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
for queue in ['test_queue_backup', 'test_no_consumers', 'test_unacked', 'test_processing_halt', 'test_cooldown']:
    try:
        channel.queue_delete(queue=queue)
        print(f"Deleted {queue}")
    except:
        pass
connection.close()
EOF

# Or reset everything
docker-compose down -v
docker-compose up -d
```

---

## 🚀 Production Testing Checklist

Before deploying to production:

- [ ] All 10 automated tests pass
- [ ] Slack webhook is configured and tested
- [ ] Received at least 4 different alert types in Slack
- [ ] Verified alert cooldown works (no spam)
- [ ] Checked Prometheus metrics endpoint
- [ ] Confirmed Docker auto-restarts on crashes
- [ ] Tested with production-like thresholds
- [ ] Reviewed and adjusted monitoring interval
- [ ] Documented any custom thresholds for your team
- [ ] Set up Grafana Cloud (optional, recommended)

---

## 🆘 Getting Help

**Check logs:**
```bash
# All logs
docker-compose logs -f

# Monitor script only
docker-compose logs -f rabbitmq | grep monitor

# RabbitMQ only
docker-compose logs -f rabbitmq | grep -i rabbitmq
```

**Interactive debugging:**
```bash
# Get shell in container
docker-compose exec rabbitmq bash

# Check running processes
ps aux | grep -E "rabbitmq|python"

# Tail container logs
docker-compose logs -f rabbitmq | grep monitor

# Manually run monitor (for debugging)
/opt/venv/bin/python /usr/local/bin/monitor.py
```

**Common issues and solutions in LOCAL_TESTING.md**

---

## 📚 Additional Resources

- **Local setup:** `LOCAL_TESTING.md`
- **Monitoring docs:** `MONITORING_SETUP.md`
- **Deployment guide:** `DEPLOYMENT_GUIDE.md`
- **RabbitMQ Management:** http://localhost:15672
- **Prometheus Metrics:** http://localhost:15692/metrics
