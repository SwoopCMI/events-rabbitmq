# 🚀 Complete Setup Guide for RabbitMQ with Slack Alerts on Render

## 🏗️ How It All Works

### **Architecture Overview**

```
┌─────────────────────────────────────────────────────────┐
│  Render Container                                       │
│                                                         │
│  ┌──────────────────┐    ┌──────────────────┐           │
│  │  start-services  │───▶│   RabbitMQ       │           │
│  │      .sh         │    │   Server         │           │
│  └──────────────────┘    │   :5672          │           │
│           │              │   Management     │           │
│           │              │   :15672         │           │
│           ▼              └──────────────────┘           │
│  ┌──────────────────┐             │                     │
│  │  monitor.py      │◀────────────┘                     │
│  │  (Python)        │                                   │
│  │                  │                                   │
│  │  Checks every    │                                   │
│  │  60 seconds      │                                   │
│  └──────────────────┘                                   │
│           │                                             │
│           │  Sends alerts                               │
│           ▼                                             │
│     ┌─────────┐                                         │
└─────┤ Slack   ├─────────────────────────────────────────┘
      │ Webhook │
      └─────────┘
```

### **Component Breakdown**

1. **Dockerfile** - Builds container with:
   - RabbitMQ 4.0 with Management & Prometheus plugins
   - Python 3 for monitoring script
   - Dependencies (aiohttp for async HTTP)

2. **start-services.sh** - Orchestrates startup:
   - Starts RabbitMQ server in background
   - Waits for RabbitMQ API to be ready
   - Launches monitoring script
   - Handles graceful shutdown

3. **monitor.py** - Smart monitoring script:
   - Connects to RabbitMQ Management API (localhost:15672)
   - Checks queues, nodes, resources every 60 seconds
   - Sends Slack alerts only when issues are detected
   - Anti-spam: 5-minute cooldown between duplicate alerts

4. **rabbitmq.conf** - RabbitMQ configuration:
   - Enables management interface
   - Sets memory/disk thresholds
   - Configures Prometheus metrics
   - Sets connection limits

## 📋 Step-by-Step Setup

### **Part 1: Slack Webhook Setup** (5 minutes)

#### **1. Create Slack Incoming Webhook**

1. Go to your Slack workspace in a browser
2. Navigate to: **Settings & Administration** → **Manage Apps**
3. Search for **"Incoming Webhooks"** 
4. Click **Add to Slack**
5. Choose the channel where you want alerts (e.g., `#rabbitmq-alerts` or `#production-alerts`)
6. Click **Add Incoming WebHooks Integration**
7. **Copy the Webhook URL** - it looks like:
   ```
   https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
   ```
8. (Optional) Customize the name and icon
9. Click **Save Settings**

✅ **Test your webhook:**
```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🧪 Test message - RabbitMQ monitoring setup!"}' \
  https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```
You should see the test message appear in your Slack channel!

---

### **Part 2: Deploy to Render** (10 minutes)

#### **Option A: Deploy from GitHub (Recommended)**

**1. Push Your Code to GitHub**
```bash
cd /Users/macuser/Source/events-rabbitmq

# Check what files we have
git status

# Add all files
git add .

# Commit
git commit -m "Add comprehensive RabbitMQ monitoring with Slack alerts"

# Push to GitHub
git push origin master
```

**2. Create Service in Render**

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository: `SwoopCMI/events-rabbitmq`
4. Configure the service:
   - **Name:** `rabbitmq` (or your preferred name)
   - **Environment:** `Docker`
   - **Branch:** `master`
   - **Plan:** Choose based on your needs (Starter or higher)
   - **Advanced:** Add a disk (see step 3)

**3. Add Persistent Disk**

1. In the service settings, scroll to **Disks**
2. Click **Add Disk**
3. Configure:
   - **Name:** `rabbitmq`
   - **Mount Path:** `/var/lib/rabbitmq`
   - **Size:** `10 GB` (adjust as needed)
4. Click **Save**

**4. Configure Environment Variables**

In the **Environment** tab, add these variables:

**Required:**
```
SLACK_WEBHOOK_URL = https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Auto-generated (Render will create these):**
- `RABBITMQ_ERLANG_COOKIE` - Click "Generate Value"
- `RABBITMQ_DEFAULT_PASS` - Click "Generate Value"

**Already set in render.yaml:**
- `RABBITMQ_DEFAULT_USER` = `rabbitmq`
- `RABBITMQ_HOST` = `localhost`
- `RABBITMQ_PORT` = `15672`

**Optional (Customize Alert Thresholds):**
```
ALERT_MAX_QUEUE_LENGTH = 1000
ALERT_MAX_UNACKED_MESSAGES = 500
ALERT_MIN_CONSUMERS = 1
ALERT_MAX_MEMORY_PERCENT = 80
ALERT_MAX_DISK_PERCENT = 85
ALERT_PROCESSING_HALT_THRESHOLD = 100
MONITORING_INTERVAL = 60
```

5. Click **Save Changes**

**5. Deploy**

1. Click **Manual Deploy** → **Deploy latest commit**
2. Watch the logs - you should see:
   ```
   Building...
   Starting...
   🚀 Starting RabbitMQ with monitoring...
   📡 Starting RabbitMQ server...
   ✅ RabbitMQ is ready!
   👀 Starting monitoring script...
   ```
3. Wait for deployment to complete (~5-10 minutes first time)

---

#### **Option B: Use render.yaml (Blueprint)**

**1. Push Code to GitHub** (same as Option A, step 1)

**2. Use Render Blueprint**

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **Blueprint**
3. Connect your repo: `SwoopCMI/events-rabbitmq`
4. Render will detect the `render.yaml` file
5. Review the configuration
6. **Add SLACK_WEBHOOK_URL** manually (it's marked as `sync: false`)
7. Click **Apply**

---

### **Part 3: Verify Setup** (5 minutes)

#### **1. Check Deployment**

In Render dashboard, view your service logs. You should see:
```
🚀 Starting RabbitMQ with monitoring...
📡 Starting RabbitMQ server...
⏳ Waiting for RabbitMQ to start...
✅ RabbitMQ is ready!
👀 Starting monitoring script...
🎉 Both services started successfully!
```

#### **2. Check Slack**

Within a few minutes, you should receive:
```
🟢 RabbitMQ Monitoring Started
Host: localhost:15672
Monitoring: Queue health, Processing rates, Resource usage
Check interval: 60s
```

#### **3. Access RabbitMQ Management Interface**

1. In Render dashboard, find your service URL: `https://your-service.onrender.com`
2. Access management: `https://your-service.onrender.com:15672`
   - **Username:** Value of `RABBITMQ_DEFAULT_USER` (rabbitmq)
   - **Password:** Check `RABBITMQ_DEFAULT_PASS` in Render environment variables
3. You should see the RabbitMQ dashboard

**Note:** Render web services use dynamic port mapping. You might need to use the internal hostname for your applications to connect.

---

### **Part 4: Connect Your Applications** (Variable)

#### **Getting Connection Details**

From Render dashboard, note:
- **Internal hostname:** `your-service-name:5672` (for apps on Render)
- **External hostname:** `your-service.onrender.com:5672` (may require port forwarding)
- **Username:** Value in `RABBITMQ_DEFAULT_USER` 
- **Password:** Value in `RABBITMQ_DEFAULT_PASS`

#### **Example Connection String**
```
amqp://rabbitmq:YOUR_PASSWORD@your-service:5672/
```

#### **For Applications on Render**

Set these environment variables in your application:
```
RABBITMQ_HOST=rabbitmq  # Your RabbitMQ service name
RABBITMQ_PORT=5672
RABBITMQ_USER=rabbitmq
RABBITMQ_PASS=your_generated_password
RABBITMQ_URL=amqp://rabbitmq:your_generated_password@rabbitmq:5672/
```

---

## 🧪 Testing Your Monitoring

### **Test 1: Verify Monitoring Works**
Already done! You got the startup notification in Slack ✅

### **Test 2: Trigger a Queue Backup Alert**

**Using the Management UI:**
1. Go to `https://your-service.onrender.com:15672`
2. Navigate to **Queues** tab
3. Add a new queue: `test-queue`
4. Go to the queue and publish messages:
   - Click on `test-queue`
   - Expand **Publish message**
   - Click **Publish message** 1000+ times (or use the API)

**Within 60 seconds**, you should get:
```
🚨 QUEUE BACKUP DETECTED
Queue: test-queue
Messages: 1,001 (threshold: 1,000)
```

### **Test 3: Trigger Processing Halt Alert**

1. Create a queue with messages (as above)
2. Don't create any consumers
3. Keep publishing messages

**Within 60 seconds**, you should get:
```
🔍 MISSING CONSUMERS
Queue: test-queue has 150 messages
Consumers: 0 (minimum: 1)
```

---

## 🎛️ Customization

### **Adjusting Alert Thresholds**

In Render dashboard → Environment variables:

**Less sensitive (fewer alerts):**
```
ALERT_MAX_QUEUE_LENGTH=5000
ALERT_MAX_MEMORY_PERCENT=90
MONITORING_INTERVAL=300  # Check every 5 minutes
```

**More sensitive (catch issues earlier):**
```
ALERT_MAX_QUEUE_LENGTH=500
ALERT_MAX_MEMORY_PERCENT=70
MONITORING_INTERVAL=30  # Check every 30 seconds
```

### **Changing Check Frequency**

```
MONITORING_INTERVAL=30   # Every 30 seconds (more frequent)
MONITORING_INTERVAL=120  # Every 2 minutes (less frequent)
```

---

## 🔍 Troubleshooting

### **Problem: Not receiving Slack alerts**

**Check:**
1. `SLACK_WEBHOOK_URL` is set correctly in Render
2. Test webhook manually with curl (see Part 1)
3. Check service logs for errors: `Failed to send Slack alert`
4. Verify webhook hasn't been deleted in Slack

### **Problem: RabbitMQ won't start**

**Check logs for:**
- Port conflicts
- Disk space issues
- Memory limits
- Check Render service logs

### **Problem: Monitoring script crashes**

**Check:**
- Python dependencies installed (`aiohttp`)
- Environment variables set correctly
- API connectivity (RabbitMQ management port 15672)

### **Problem: Can't connect applications to RabbitMQ**

**For apps on Render:**
- Use service name: `rabbitmq:5672`
- Use internal networking (services in same team)

**For external apps:**
- Render web services may need TCP proxy for port 5672
- Consider using Render Private Services

---

## 📊 What Happens Next

### **Normal Operations**

- Monitoring checks every 60 seconds
- No alerts = everything healthy
- You'll see logs in Render: `✅ Health check completed`

### **When Issues Occur**

1. **Alert sent to Slack** with problem details
2. **5-minute cooldown** prevents spam
3. **Another alert when resolved** (coming back online)
4. **Logs in Render** show what was detected

### **Alert Example Flow**

```
Minute 0: Queue has 900 messages (OK)
Minute 1: Queue has 1100 messages → 🚨 Alert sent to Slack
Minute 2-6: No more alerts (cooldown)
Minute 7: If still over 1000, would alert again
```

---

## 🎯 Quick Reference

### **Important URLs**
- **Render Dashboard:** https://dashboard.render.com/
- **RabbitMQ Management:** `https://your-service.onrender.com:15672`
- **Prometheus Metrics:** `https://your-service.onrender.com:15692/metrics`

### **Default Credentials**
- **Username:** `rabbitmq`
- **Password:** Check Render environment variable `RABBITMQ_DEFAULT_PASS`

### **Key Files**
- `Dockerfile` - Container build instructions
- `monitor.py` - Monitoring script (this sends alerts)
- `start-services.sh` - Startup orchestration
- `rabbitmq.conf` - RabbitMQ configuration
- `render.yaml` - Render deployment config
- `requirements.txt` - Python dependencies

---

## ✅ Deployment Checklist

- [ ] Slack webhook created and tested
- [ ] Code pushed to GitHub
- [ ] Render service created
- [ ] Disk attached (10GB at `/var/lib/rabbitmq`)
- [ ] `SLACK_WEBHOOK_URL` environment variable set
- [ ] Service deployed successfully
- [ ] Received startup notification in Slack
- [ ] Can access RabbitMQ management UI
- [ ] Tested triggering an alert
- [ ] Applications configured to connect

---

Need help? Check the logs in Render dashboard or see `ALERT_EXAMPLES.md` for what each alert means!