# RabbitMQ on Render with Monitoring & Alerts

This is a template repo for running a RabbitMQ instance as a **web service** on Render with comprehensive monitoring and Slack alerting capabilities.

It uses the [official Dockerfile](https://hub.docker.com/_/rabbitmq) and backs RabbitMQ with a [Render disk](https://render.com/docs/disks), making it resilient to data loss in the case of restarts or deploys.

## 🚨 Monitoring & Alerting Features

### Automated Slack Alerts for:
- **Queue backups** - When queues exceed message thresholds
- **Processing halts** - When messages aren't being consumed
- **Resource issues** - High memory or disk usage  
- **Connection problems** - API connectivity issues
- **System health** - Node status and performance

### Real-time Monitoring:
- Queue length and consumer count tracking
- Message processing rate monitoring
- Memory and disk usage alerts
- Unacknowledged message detection
- Automatic recovery notifications

## 🚀 Quick Setup

### 1. Deploy Basic RabbitMQ
See https://render.com/docs/deploy-rabbitmq.

### 2. Configure Slack Alerts
1. Create a Slack webhook in your workspace
2. In Render dashboard, add environment variable:
   ```
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```
3. Redeploy the service

### 3. Customize Alert Thresholds (Optional)
Add these environment variables in Render:
- `ALERT_MAX_QUEUE_LENGTH=1000` - Queue size threshold
- `ALERT_MAX_MEMORY_PERCENT=80` - Memory usage threshold  
- `ALERT_MIN_CONSUMERS=1` - Minimum consumers per queue
- `MONITORING_INTERVAL=60` - Check frequency in seconds

## 📊 Access Points

- **RabbitMQ Management**: `https://your-app.onrender.com:15672`
- **Prometheus Metrics**: `https://your-app.onrender.com:15692/metrics`

## 📚 Documentation

- [**Complete Setup Guide**](docs/MONITORING_SETUP.md) - Detailed configuration instructions
- [**Deployment Guide**](docs/DEPLOYMENT_GUIDE.md) - Step-by-step Render deployment
- [**Alert Examples**](docs/ALERT_EXAMPLES.md) - Sample notifications and meanings
- [**Testing Guide**](docs/TESTING_GUIDE.md) - Comprehensive testing instructions
- [**Local Testing**](docs/LOCAL_TESTING.md) - Local development setup

## 🧪 Testing

Run the monitoring test suite locally:
```bash
python3 tests/test_monitoring.py
```

This will verify Slack integration and RabbitMQ API connectivity.
