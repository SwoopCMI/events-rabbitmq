#!/usr/bin/env python3
"""
Comprehensive RabbitMQ Monitoring with Smart Slack Alerts
Detects queue backups, processing halts, resource issues, and more.
"""

import asyncio
import aiohttp
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AlertThresholds:
    """Production-ready alert thresholds"""
    max_queue_length: int = 1000
    max_unacknowledged_messages: int = 500
    min_consumers_per_queue: int = 1
    max_memory_usage_percent: int = 80
    max_disk_usage_percent: int = 85
    processing_halt_threshold: int = 100  # messages with no consumption
    connection_failure_threshold: int = 3
    
class RabbitMQMonitor:
    def get_queue_config(self, queue_name):
        """Return (threshold, cooldown) for a given queue name"""
        if queue_name in self.long_job_queues:
            return self.long_job_threshold, self.long_job_cooldown
        return self.thresholds.max_queue_length, self.default_alert_cooldown

    def __init__(self):
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_port = os.getenv('RABBITMQ_PORT', '15672')
        self.rabbitmq_user = os.getenv('RABBITMQ_DEFAULT_USER', 'rabbitmq')
        self.rabbitmq_password = os.getenv('RABBITMQ_DEFAULT_PASS', 'guest')
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        
        self.base_url = f"http://{self.rabbitmq_host}:{self.rabbitmq_port}/api"
        self.auth = aiohttp.BasicAuth(self.rabbitmq_user, self.rabbitmq_password)
        
        self.thresholds = AlertThresholds()
        self.last_alerts = {}  # Track last alert times to prevent spam
        # Per-queue custom config for long-running queues (env support)
        # Comma-separated queue names
        long_job_queues_env = os.getenv('LONG_JOB_QUEUES', '')
        self.long_job_queues = [q.strip() for q in long_job_queues_env.split(',') if q.strip()] or [
            "colateral-events-production-location-ranges.delay",
            "colateral-events-production-location-ranges"
        ]
        # Per-queue threshold and cooldown (env override, fallback to defaults)
        self.long_job_threshold = int(os.getenv('LONG_JOB_QUEUE_THRESHOLD', '1000000'))
        self.long_job_cooldown = int(os.getenv('LONG_JOB_QUEUE_COOLDOWN', '10800'))
        self.default_alert_cooldown = int(os.getenv('DEFAULT_ALERT_COOLDOWN', '1800'))

        self.alert_cooldown = self.default_alert_cooldown  # 5 minutes cooldown between same alerts (default)
        self.connection_failures = 0
        
    async def send_slack_alert(self, message: str, severity: str = "warning"):
        """Send rich alert to Slack with proper formatting"""
        if not self.slack_webhook_url:
            logger.warning("No Slack webhook URL configured, skipping alert")   
            return
            
        color = {
            "critical": "#FF0000",
            "warning": "#FFA500", 
            "info": "#36A64F"
        }.get(severity, "#FFA500")
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"🐰 RabbitMQ Alert - {severity.upper()}",
                    "text": message,
                    "footer": f"RabbitMQ Monitor - {self.rabbitmq_host}",
                    "ts": int(time.time())
                }
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.slack_webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack alert sent: {message}")
                    else:
                        logger.error(f"Failed to send Slack alert: {response.status}")
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")

    def should_send_alert(self, alert_key: str, cooldown: int = None) -> bool:
        """Prevent alert spam with intelligent cooldown (per alert_key)"""
        now = time.time()
        cd = cooldown if cooldown is not None else self.default_alert_cooldown
        if alert_key in self.last_alerts:
            if now - self.last_alerts[alert_key] < cd:
                return False
        self.last_alerts[alert_key] = now
        return True

    async def get_api_data(self, endpoint: str) -> Optional[Dict]:
        """Robust API data fetching with error handling"""
        url = f"{self.base_url}/{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, auth=self.auth, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        self.connection_failures = 0
                        return await response.json()
                    else:
                        logger.error(f"API request failed: {response.status} - {url}")
                        return None
        except Exception as e:
            self.connection_failures += 1
            logger.error(f"Error fetching {endpoint}: {e}")
            return None

    async def check_queue_health(self):
        """🚨 CRITICAL: Detect queue backups and processing issues"""
        queues = await self.get_api_data("queues")
        if not queues:
            return
        for queue in queues:
            queue_name = queue.get('name', 'unknown')
            vhost = queue.get('vhost', '/')
            # Per-queue config
            queue_threshold, queue_cooldown = self.get_queue_config(queue_name)
            # 🔥 QUEUE BACKUP DETECTION
            messages = queue.get('messages', 0)
            if messages > queue_threshold:
                alert_key = f"queue_backup_{queue_name}"
                if self.should_send_alert(alert_key, queue_cooldown):
                    await self.send_slack_alert(
                        f"🚨 **QUEUE BACKUP DETECTED**\n"
                        f"Queue: `{queue_name}`\n"
                        f"Messages: **{messages:,}** (threshold: {queue_threshold:,})\n"
                        f"VHost: `{vhost}`\n"
                        f"🔧 *Action needed: Check consumers or increase capacity*",
                        "critical"
                    )
            # ⚠️ UNACKNOWLEDGED MESSAGES
            unacked = queue.get('messages_unacknowledged', 0)
            if unacked > self.thresholds.max_unacknowledged_messages:
                alert_key = f"unacked_{queue_name}"
                if self.should_send_alert(alert_key, queue_cooldown):
                    await self.send_slack_alert(
                        f"⚠️ **HIGH UNACKNOWLEDGED MESSAGES**\n"
                        f"Queue: `{queue_name}`\n"
                        f"Unacked: **{unacked:,}** (threshold: {self.thresholds.max_unacknowledged_messages:,})\n"
                        f"🔧 *Consumers may be slow or failing to ack*",
                        "warning"
                    )
            # 👥 CONSUMER MONITORING
            consumers = queue.get('consumers', 0)
            if messages > 0 and consumers < self.thresholds.min_consumers_per_queue:
                alert_key = f"no_consumers_{queue_name}"
                if self.should_send_alert(alert_key, queue_cooldown):
                    await self.send_slack_alert(
                        f"🔍 **MISSING CONSUMERS**\n"
                        f"Queue: `{queue_name}` has **{messages:,}** messages\n"
                        f"Consumers: **{consumers}** (minimum: {self.thresholds.min_consumers_per_queue})\n"
                        f"🔧 *Start consumer processes immediately*",
                        "warning"
                    )
            # ⏹️ PROCESSING HALT DETECTION
            message_stats = queue.get('message_stats', {})
            publish_rate = message_stats.get('publish_details', {}).get('rate', 0)
            consume_rate = message_stats.get('deliver_get_details', {}).get('rate', 0)
            # Alert if messages are piling up but nothing is being consumed
            if (messages > self.thresholds.processing_halt_threshold and 
                consume_rate == 0 and publish_rate > 0):
                alert_key = f"processing_halt_{queue_name}"
                if self.should_send_alert(alert_key, queue_cooldown):
                    await self.send_slack_alert(
                        f"⏹️ **PROCESSING COMPLETELY HALTED**\n"
                        f"Queue: `{queue_name}`\n"
                        f"Messages: **{messages:,}**\n"
                        f"Publish rate: **{publish_rate:.2f}/s**\n"
                        f"Consume rate: **{consume_rate:.2f}/s** ❌\n"
                        f"🔧 *Check consumer health immediately!*",
                        "critical"
                    )

    async def check_node_health(self):
        """💾 Monitor system resources and node health"""
        nodes = await self.get_api_data("nodes")
        if not nodes:
            return
            
        for node in nodes:
            node_name = node.get('name', 'unknown')
            
            # 💾 MEMORY USAGE MONITORING
            mem_used = node.get('mem_used', 0)
            mem_limit = node.get('mem_limit', 1)
            mem_percent = (mem_used / mem_limit) * 100 if mem_limit > 0 else 0
            
            if mem_percent > self.thresholds.max_memory_usage_percent:
                alert_key = f"memory_{node_name}"
                if self.should_send_alert(alert_key):
                    severity = "critical" if mem_percent > 90 else "warning"
                    await self.send_slack_alert(
                        f"💾 **HIGH MEMORY USAGE**\n"
                        f"Node: `{node_name}`\n"
                        f"Memory: **{mem_percent:.1f}%** (threshold: {self.thresholds.max_memory_usage_percent}%)\n"
                        f"Used: {mem_used:,} bytes\n"
                        f"🔧 *Consider scaling or checking for memory leaks*",
                        severity
                    )
            
            # 💿 DISK USAGE MONITORING  
            disk_free = node.get('disk_free', 1)
            disk_limit = node.get('disk_free_limit', 0)
            if disk_limit > 0 and disk_free > 0:
                disk_used_percent = (1 - (disk_free / disk_limit)) * 100
                if disk_used_percent > self.thresholds.max_disk_usage_percent:
                    alert_key = f"disk_{node_name}"
                    if self.should_send_alert(alert_key):
                        await self.send_slack_alert(
                            f"💿 **HIGH DISK USAGE**\n"
                            f"Node: `{node_name}`\n"
                            f"Disk usage: **{disk_used_percent:.1f}%** (threshold: {self.thresholds.max_disk_usage_percent}%)\n"
                            f"Free: {disk_free:,} bytes\n"
                            f"🔧 *Clean up or increase disk space*",
                            "critical"
                        )
            
            # 🔴 NODE STATUS
            running = node.get('running', False)
            if not running:
                alert_key = f"node_down_{node_name}"
                if self.should_send_alert(alert_key):
                    await self.send_slack_alert(
                        f"🚨 **NODE DOWN**\n"
                        f"Node: `{node_name}` is not running!\n"
                        f"🔧 *Immediate restart required*",
                        "critical"
                    )

    async def check_connections(self):
        """🔌 Monitor API connectivity"""
        if self.connection_failures >= self.thresholds.connection_failure_threshold:
            alert_key = "connection_failures"
            if self.should_send_alert(alert_key):
                await self.send_slack_alert(
                    f"🔌 **API CONNECTION FAILED**\n"
                    f"Failed attempts: **{self.connection_failures}**\n"
                    f"Host: `{self.rabbitmq_host}:{self.rabbitmq_port}`\n"
                    f"🔧 *Check RabbitMQ service health*",
                    "critical"
                )

    async def run_health_check(self):
        """Execute comprehensive health monitoring"""
        logger.info("🔍 Running comprehensive RabbitMQ health checks...")
        
        try:
            await asyncio.gather(
                self.check_queue_health(),
                self.check_node_health(), 
                self.check_connections()
            )
            logger.info("✅ Health check completed")
        except Exception as e:
            logger.error(f"❌ Error during health checks: {e}")
            await self.send_slack_alert(
                f"❌ **MONITORING ERROR**\n"
                f"Health check failed: {str(e)}\n"
                f"🔧 *Check monitoring service*",
                "critical"
            )

    async def start_monitoring(self, interval: int = 60):
        """🚀 Start comprehensive monitoring with smart alerting"""
        logger.info(f"🚀 Starting comprehensive RabbitMQ monitoring (interval: {interval}s)")
        
        # Startup notification
        await self.send_slack_alert(
            f"🟢 **RabbitMQ Monitoring Started**\n"
            f"Host: `{self.rabbitmq_host}:{self.rabbitmq_port}`\n"
            f"Monitoring: Queue health, Processing rates, Resource usage\n"
            f"Check interval: {interval}s",
            "info"
        )
        
        while True:
            await self.run_health_check()
            await asyncio.sleep(interval)

if __name__ == "__main__":
    monitor = RabbitMQMonitor()
    
    # Load thresholds from environment variables
    monitor.thresholds.max_queue_length = int(os.getenv('ALERT_MAX_QUEUE_LENGTH', '1000'))
    monitor.thresholds.max_unacknowledged_messages = int(os.getenv('ALERT_MAX_UNACKED_MESSAGES', '500'))
    monitor.thresholds.min_consumers_per_queue = int(os.getenv('ALERT_MIN_CONSUMERS', '1'))
    monitor.thresholds.max_memory_usage_percent = int(os.getenv('ALERT_MAX_MEMORY_PERCENT', '80'))
    monitor.thresholds.max_disk_usage_percent = int(os.getenv('ALERT_MAX_DISK_PERCENT', '85'))
    monitor.thresholds.processing_halt_threshold = int(os.getenv('ALERT_PROCESSING_HALT_THRESHOLD', '100'))
    
    # Monitoring interval
    interval = int(os.getenv('MONITORING_INTERVAL', '60'))
    
    try:
        asyncio.run(monitor.start_monitoring(interval))
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")