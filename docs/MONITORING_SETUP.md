# RabbitMQ Monitoring and Alerting Setup

This guide explains how to configure Slack alerts for your RabbitMQ instance on Render.

## 🚨 Alert Scenarios Covered

The monitoring system will send Slack notifications for:

1. **Queue Backup**: When queues exceed the maximum message count
2. **Processing Halts**: When messages are being published but not consumed
3. **Unacknowledged Messages**: High number of unacked messages
4. **Missing Consumers**: Queues with messages but no consumers
5. **Resource Usage**: High memory or disk usage
6. **Connection Issues**: API connectivity problems
7. **Node Health**: RabbitMQ node status issues

## 🔧 Setup Instructions

### 1. Create a Slack Webhook

1. Go to your Slack workspace
2. Navigate to **Settings & administration** → **Manage apps**
3. Search for "Incoming Webhooks" and add it
4. Create a new webhook for the channel where you want alerts
5. Copy the webhook URL (looks like: `https://hooks.slack.com/services/...`)

### 2. Configure Render Environment Variables

In your Render dashboard, add these environment variables:

**Required:**
- `SLACK_WEBHOOK_URL`: Your Slack webhook URL from step 1

**Optional (with defaults):**
- `ALERT_MAX_QUEUE_LENGTH`: `1000` - Maximum messages per queue before alert
- `ALERT_MAX_UNACKED_MESSAGES`: `500` - Maximum unacknowledged messages
- `ALERT_MIN_CONSUMERS`: `1` - Minimum consumers per queue with messages
- `ALERT_MAX_MEMORY_PERCENT`: `80` - Memory usage threshold (%)
- `ALERT_MAX_DISK_PERCENT`: `85` - Disk usage threshold (%)
- `MONITORING_INTERVAL`: `60` - Check interval in seconds

### 3. Deploy to Render

1. Push your changes to GitHub
2. Deploy through Render dashboard or auto-deploy if configured
3. The monitoring will start automatically after deployment

## 📊 Monitoring Features

### Queue Health Monitoring
- **Queue length**: Alerts when queues grow too large
- **Consumer count**: Warns when queues have messages but no consumers
- **Processing rate**: Detects when consumption stops while publishing continues
- **Unacknowledged messages**: Monitors message acknowledgment patterns

### System Health Monitoring
- **Memory usage**: Tracks RabbitMQ memory consumption
- **Disk usage**: Monitors disk space for message persistence
- **Node status**: Checks if RabbitMQ nodes are running
- **API connectivity**: Detects management API issues

### Alert Features
- **Smart throttling**: Prevents alert spam with 5-minute cooldowns
- **Severity levels**: Different colors and priorities for different alert types
- **Rich formatting**: Clear, actionable alert messages with context
- **Automatic recovery**: Stops alerting when issues resolve

## 🎨 Alert Examples

### Critical Alerts (Red)
```
🚨 Queue `orders` has 1500 messages (threshold: 1000)
VHost: /production
```

```
⏹️ Processing appears halted on queue `notifications`
Messages: 250, Publish rate: 5.20/s, Consume rate: 0.00/s
```

### Warning Alerts (Orange)
```
⚠️ Queue `emails` has 600 unacknowledged messages (threshold: 500)
```

```
💾 Node rabbit@rabbitmq memory usage: 85.2% (threshold: 80%)
```

### Info Alerts (Green)
```
🟢 RabbitMQ monitoring started for localhost:15672
```

## 🔍 Accessing Metrics

### RabbitMQ Management Interface
- **URL**: `https://your-render-app.onrender.com:15672`
- **Username**: Value of `RABBITMQ_DEFAULT_USER` env var
- **Password**: Value of `RABBITMQ_DEFAULT_PASS` env var

### Prometheus Metrics
- **URL**: `https://your-render-app.onrender.com:15692/metrics`
- Use with Grafana, DataDog, or other monitoring tools

## ⚙️ Customizing Alerts

### Adjusting Thresholds
Update the environment variables in Render:

```yaml
# More aggressive monitoring
ALERT_MAX_QUEUE_LENGTH: 500
ALERT_MAX_MEMORY_PERCENT: 70
MONITORING_INTERVAL: 30

# More relaxed monitoring  
ALERT_MAX_QUEUE_LENGTH: 2000
ALERT_MAX_MEMORY_PERCENT: 90
MONITORING_INTERVAL: 120
```

### Adding Custom Checks
Edit `monitor.py` to add application-specific monitoring:

```python
async def check_custom_metrics(self):
    """Add your custom monitoring logic here"""
    # Example: Check specific queue patterns
    # Example: Monitor custom application metrics
    # Example: Integration with external APIs
```

## 🐛 Troubleshooting

### No Alerts Received
1. Check Slack webhook URL is correct
2. Verify environment variables in Render
3. Check logs: `render logs show <service-name>`
4. Test webhook manually: `curl -X POST -H 'Content-type: application/json' --data '{"text":"Test"}' YOUR_WEBHOOK_URL`

### False Positives
1. Adjust thresholds via environment variables
2. Monitor logs to understand alert patterns
3. Consider increasing `MONITORING_INTERVAL` for less frequent checks

### Monitoring Not Starting
1. Check Docker build logs in Render
2. Verify all files are included in repository
3. Check startup script logs for Python errors
4. Ensure RabbitMQ starts before monitoring script

## 📚 Additional Resources

- [RabbitMQ Management Plugin](https://www.rabbitmq.com/management.html)
- [RabbitMQ Prometheus Plugin](https://www.rabbitmq.com/prometheus.html)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)
- [Render Environment Variables](https://render.com/docs/environment-variables)

## 🆘 Emergency Contacts

When critical alerts fire, consider these immediate actions:

1. **Queue Backup**: Scale consumers or check for processing errors
2. **Processing Halt**: Restart consumers or check application health
3. **High Memory**: Restart RabbitMQ or investigate memory leaks
4. **High Disk**: Clean old logs or increase disk size
5. **Node Down**: Check Render service status and restart if needed