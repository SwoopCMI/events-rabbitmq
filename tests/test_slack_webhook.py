#!/usr/bin/env python3
"""
Quick test to verify Slack webhook is working
"""

import requests
import os
import sys

# Try to load .env file if python-dotenv is installed (for local testing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, use system environment variables

def test_slack_webhook():
    """Send a test message to Slack"""
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ ERROR: SLACK_WEBHOOK_URL environment variable not set")
        print("\nSet it with:")
        print("  export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/...'")
        print("\nOr add to .env file")
        return False
        
    print(f"🔗 Testing Slack webhook...")
    print(f"   URL: {webhook_url[:50]}...")
    
    # Test message
    payload = {
        "text": "🧪 *RabbitMQ Monitoring Test*\n\nIf you see this message, your Slack webhook is working correctly! ✅"
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! Test message sent to Slack")
            print("   Check your Slack channel for the message")
            return True
        else:
            print(f"\n❌ FAILED: Slack returned status code {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ FAILED: Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"\n❌ FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_slack_webhook()
    sys.exit(0 if success else 1)
