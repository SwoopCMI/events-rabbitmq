#!/usr/bin/env python3
"""
Test script to verify RabbitMQ monitoring and Slack integration
"""

import asyncio
import aiohttp
import json
import os
import time

async def test_slack_webhook():
    """Test Slack webhook connectivity"""
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        print("❌ SLACK_WEBHOOK_URL not set")
        return False
    
    payload = {
        "text": "🧪 RabbitMQ monitoring test - If you see this, Slack integration is working!"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status == 200:
                    print("✅ Slack webhook test successful")
                    return True
                else:
                    print(f"❌ Slack webhook failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Slack webhook error: {e}")
        return False

async def test_rabbitmq_api():
    """Test RabbitMQ Management API connectivity"""
    host = os.getenv('RABBITMQ_HOST', 'localhost')
    port = os.getenv('RABBITMQ_PORT', '15672')
    user = os.getenv('RABBITMQ_DEFAULT_USER', 'rabbitmq')
    password = os.getenv('RABBITMQ_DEFAULT_PASS', 'guest')
    
    url = f"http://{host}:{port}/api/overview"
    auth = aiohttp.BasicAuth(user, password)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=auth, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ RabbitMQ API accessible")
                    print(f"   Version: {data.get('rabbitmq_version', 'unknown')}")
                    print(f"   Management version: {data.get('management_version', 'unknown')}")
                    return True
                else:
                    print(f"❌ RabbitMQ API failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ RabbitMQ API error: {e}")
        return False

async def test_queue_creation():
    """Test creating a test queue to verify monitoring"""
    host = os.getenv('RABBITMQ_HOST', 'localhost')
    port = os.getenv('RABBITMQ_PORT', '15672')
    user = os.getenv('RABBITMQ_DEFAULT_USER', 'rabbitmq')
    password = os.getenv('RABBITMQ_DEFAULT_PASS', 'guest')
    
    # Create a test queue
    url = f"http://{host}:{port}/api/queues/%2F/test_monitoring_queue"
    auth = aiohttp.BasicAuth(user, password)
    
    queue_config = {
        "durable": False,
        "auto_delete": True
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Create queue
            async with session.put(url, auth=auth, json=queue_config) as response:
                if response.status in [200, 201, 204]:
                    print("✅ Test queue created successfully")
                    
                    # Publish test message
                    publish_url = f"http://{host}:{port}/api/exchanges/%2F/amq.default/publish"
                    message = {
                        "properties": {},
                        "routing_key": "test_monitoring_queue",
                        "payload": "Test message for monitoring",
                        "payload_encoding": "string"
                    }
                    
                    async with session.post(publish_url, auth=auth, json=message) as pub_response:
                        if pub_response.status == 200:
                            print("✅ Test message published")
                            
                            # Check queue has message
                            await asyncio.sleep(2)
                            async with session.get(f"http://{host}:{port}/api/queues/%2F/test_monitoring_queue", auth=auth) as queue_response:
                                if queue_response.status == 200:
                                    queue_data = await queue_response.json()
                                    messages = queue_data.get('messages', 0)
                                    print(f"✅ Queue has {messages} message(s)")
                                    return True
                        else:
                            print(f"❌ Failed to publish message: {pub_response.status}")
                else:
                    print(f"❌ Failed to create test queue: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Queue test error: {e}")
        return False

def print_config():
    """Print current monitoring configuration"""
    print("📋 Current Monitoring Configuration:")
    print(f"   RABBITMQ_HOST: {os.getenv('RABBITMQ_HOST', 'localhost')}")
    print(f"   RABBITMQ_PORT: {os.getenv('RABBITMQ_PORT', '15672')}")
    print(f"   RABBITMQ_DEFAULT_USER: {os.getenv('RABBITMQ_DEFAULT_USER', 'rabbitmq')}")
    print(f"   SLACK_WEBHOOK_URL: {'✅ Set' if os.getenv('SLACK_WEBHOOK_URL') else '❌ Not set'}")
    print(f"   ALERT_MAX_QUEUE_LENGTH: {os.getenv('ALERT_MAX_QUEUE_LENGTH', '1000')}")
    print(f"   ALERT_MAX_MEMORY_PERCENT: {os.getenv('ALERT_MAX_MEMORY_PERCENT', '80')}")
    print(f"   MONITORING_INTERVAL: {os.getenv('MONITORING_INTERVAL', '60')}s")
    print()

async def main():
    print("🧪 RabbitMQ Monitoring Test Suite")
    print("=" * 40)
    
    print_config()
    
    # Run tests
    tests = [
        ("Slack Webhook", test_slack_webhook),
        ("RabbitMQ API", test_rabbitmq_api),
        ("Queue Operations", test_queue_creation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 Test Results Summary:")
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Monitoring should work correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the configuration and try again.")
        print("\n🔧 Troubleshooting tips:")
        print("   1. Make sure RabbitMQ is running")
        print("   2. Verify SLACK_WEBHOOK_URL is set correctly")
        print("   3. Check network connectivity")
        print("   4. Confirm RabbitMQ credentials are correct")

if __name__ == "__main__":
    asyncio.run(main())