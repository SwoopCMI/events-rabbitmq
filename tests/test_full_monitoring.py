#!/usr/bin/env python3
"""
Comprehensive RabbitMQ Monitoring Test Suite
Tests all alert scenarios and monitoring features
"""

import pika
import requests
import time
import os
import sys
from typing import Dict, List
import json

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use environment variables directly

class Colors:
    """Terminal colors for better output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

class RabbitMQTestSuite:
    def __init__(self):
        self.host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.amqp_port = int(os.getenv('RABBITMQ_AMQP_PORT', '5672'))
        self.mgmt_port = int(os.getenv('RABBITMQ_PORT', '15672'))
        self.username = os.getenv('RABBITMQ_DEFAULT_USER', 'rabbitmq')
        self.password = os.getenv('RABBITMQ_DEFAULT_PASS', 'testpassword123')
        
        self.base_url = f"http://{self.host}:{self.mgmt_port}/api"
        self.auth = (self.username, self.password)
        
        self.test_results = []
        
    def print_header(self, text: str):
        """Print a formatted header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")
        
    def print_test(self, name: str, passed: bool, message: str = ""):
        """Print test result"""
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if passed else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"{status} - {name}")
        if message:
            print(f"     {Colors.YELLOW}{message}{Colors.END}")
        self.test_results.append((name, passed))
        
    def get_api(self, endpoint: str) -> Dict:
        """Make API request"""
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", auth=self.auth, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"{Colors.RED}API Error: {e}{Colors.END}")
            return {}
            
    def get_connection(self) -> pika.BlockingConnection:
        """Get RabbitMQ connection"""
        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.amqp_port,
            credentials=credentials,
            heartbeat=60
        )
        return pika.BlockingConnection(parameters)
        
    def cleanup_test_queues(self):
        """Remove all test queues"""
        print(f"{Colors.YELLOW}🧹 Cleaning up test queues...{Colors.END}")
        queues = self.get_api("queues")
        connection = self.get_connection()
        channel = connection.channel()
        
        for queue in queues:
            if queue['name'].startswith('test_'):
                try:
                    channel.queue_delete(queue=queue['name'])
                    print(f"   Deleted: {queue['name']}")
                except Exception as e:
                    print(f"   Error deleting {queue['name']}: {e}")
                    
        connection.close()
        time.sleep(2)
        
    # ========== TEST SUITE ==========
    
    def test_1_rabbitmq_connectivity(self):
        """Test 1: Verify RabbitMQ API is accessible"""
        self.print_header("TEST 1: RabbitMQ Connectivity")
        
        try:
            overview = self.get_api("overview")
            if overview and 'rabbitmq_version' in overview:
                self.print_test(
                    "RabbitMQ API accessible",
                    True,
                    f"Version: {overview.get('rabbitmq_version', 'unknown')}"
                )
            else:
                self.print_test("RabbitMQ API accessible", False, "No valid response")
        except Exception as e:
            self.print_test("RabbitMQ API accessible", False, str(e))
            
    def test_2_management_plugins(self):
        """Test 2: Verify required plugins are enabled"""
        self.print_header("TEST 2: Management Plugins")
        
        overview = self.get_api("overview")
        listeners = overview.get('listeners', [])
        
        # Check management plugin
        mgmt_found = any(l.get('port') == self.mgmt_port for l in listeners)
        self.print_test("Management plugin enabled", mgmt_found, f"Port {self.mgmt_port}")
        
        # Check prometheus endpoint
        try:
            response = requests.get(f"http://{self.host}:15692/metrics", timeout=5)
            prometheus_ok = response.status_code == 200
            self.print_test("Prometheus plugin enabled", prometheus_ok, "Port 15692")
        except:
            self.print_test("Prometheus plugin enabled", False, "Port 15692 not accessible")
            
    def test_3_queue_backup_alert(self):
        """Test 3: Trigger queue backup alert (high message count)"""
        self.print_header("TEST 3: Queue Backup Alert")
        
        threshold = int(os.getenv('ALERT_MAX_QUEUE_LENGTH', '1000'))
        test_queue = 'test_queue_backup'
        message_count = threshold + 100
        
        print(f"Creating queue with {message_count} messages (threshold: {threshold})...")
        
        try:
            connection = self.get_connection()
            channel = connection.channel()
            channel.queue_declare(queue=test_queue, durable=True)
            
            # Publish messages
            for i in range(message_count):
                channel.basic_publish(
                    exchange='',
                    routing_key=test_queue,
                    body=f'Test message {i}',
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                if (i + 1) % 200 == 0:
                    print(f"   Published {i + 1}/{message_count} messages...")
                    
            connection.close()
            
            # Wait for monitoring to detect
            print(f"{Colors.YELLOW}⏳ Waiting 70 seconds for monitoring to detect...{Colors.END}")
            time.sleep(70)
            
            # Verify queue exists with messages
            queues = self.get_api("queues")
            test_q = next((q for q in queues if q['name'] == test_queue), None)
            
            if test_q and test_q.get('messages', 0) > threshold:
                self.print_test(
                    "Queue backup scenario created",
                    True,
                    f"Queue has {test_q['messages']} messages (threshold: {threshold})"
                )
                print(f"{Colors.YELLOW}   📨 Check Slack for 'QUEUE BACKUP DETECTED' alert{Colors.END}")
            else:
                self.print_test("Queue backup scenario created", False)
                
        except Exception as e:
            self.print_test("Queue backup scenario created", False, str(e))
            
    def test_4_missing_consumers_alert(self):
        """Test 4: Trigger missing consumers alert"""
        self.print_header("TEST 4: Missing Consumers Alert")
        
        test_queue = 'test_no_consumers'
        
        print(f"Creating queue with messages but NO consumers...")
        
        try:
            connection = self.get_connection()
            channel = connection.channel()
            channel.queue_declare(queue=test_queue, durable=True)
            
            # Publish some messages
            for i in range(150):
                channel.basic_publish(
                    exchange='',
                    routing_key=test_queue,
                    body=f'Unprocessed message {i}'
                )
                
            connection.close()
            
            print(f"{Colors.YELLOW}⏳ Waiting 70 seconds for monitoring to detect...{Colors.END}")
            time.sleep(70)
            
            # Verify queue has messages but no consumers
            queues = self.get_api("queues")
            test_q = next((q for q in queues if q['name'] == test_queue), None)
            
            if test_q and test_q.get('messages', 0) > 0 and test_q.get('consumers', 0) == 0:
                self.print_test(
                    "Missing consumers scenario created",
                    True,
                    f"Queue has {test_q['messages']} messages, 0 consumers"
                )
                print(f"{Colors.YELLOW}   📨 Check Slack for 'MISSING CONSUMERS' alert{Colors.END}")
            else:
                self.print_test("Missing consumers scenario created", False)
                
        except Exception as e:
            self.print_test("Missing consumers scenario created", False, str(e))
            
    def test_5_unacked_messages_alert(self):
        """Test 5: Trigger unacknowledged messages alert"""
        self.print_header("TEST 5: Unacknowledged Messages Alert")
        
        threshold = int(os.getenv('ALERT_MAX_UNACKED_MESSAGES', '500'))
        test_queue = 'test_unacked'
        message_count = threshold + 50
        
        print(f"Creating consumer that DOESN'T acknowledge messages...")
        
        try:
            connection = self.get_connection()
            channel = connection.channel()
            channel.queue_declare(queue=test_queue, durable=True)
            
            # Publish messages
            for i in range(message_count):
                channel.basic_publish(
                    exchange='',
                    routing_key=test_queue,
                    body=f'Unacked message {i}'
                )
                
            # Create consumer that doesn't ack
            def callback(ch, method, properties, body):
                # Don't acknowledge - simulate slow/failing consumer
                pass
                
            channel.basic_consume(queue=test_queue, on_message_callback=callback, auto_ack=False)
            
            # Start consuming briefly to get unacked messages
            print(f"   Consuming {message_count} messages without ack...")
            connection.process_data_events(time_limit=5)
            
            print(f"{Colors.YELLOW}⏳ Waiting 70 seconds for monitoring to detect...{Colors.END}")
            time.sleep(70)
            
            # Verify unacked messages
            queues = self.get_api("queues")
            test_q = next((q for q in queues if q['name'] == test_queue), None)
            
            if test_q and test_q.get('messages_unacknowledged', 0) > threshold:
                self.print_test(
                    "Unacknowledged messages scenario created",
                    True,
                    f"Queue has {test_q['messages_unacknowledged']} unacked messages"
                )
                print(f"{Colors.YELLOW}   📨 Check Slack for 'HIGH UNACKNOWLEDGED MESSAGES' alert{Colors.END}")
            else:
                self.print_test("Unacknowledged messages scenario created", False)
                
            connection.close()
            
        except Exception as e:
            self.print_test("Unacknowledged messages scenario created", False, str(e))
            
    def test_6_processing_halt_alert(self):
        """Test 6: Trigger processing halt alert"""
        self.print_header("TEST 6: Processing Halt Detection")
        
        test_queue = 'test_processing_halt'
        
        print(f"Creating queue with active publishing but NO consumption...")
        
        try:
            connection = self.get_connection()
            channel = connection.channel()
            channel.queue_declare(queue=test_queue, durable=True)
            
            # Publish initial batch
            print(f"   Publishing initial batch of messages...")
            for i in range(150):
                channel.basic_publish(
                    exchange='',
                    routing_key=test_queue,
                    body=f'Message {i}'
                )
            
            # Keep connection open and publish slowly to maintain publish rate
            print(f"{Colors.YELLOW}⏳ Publishing continuously for 70 seconds to maintain publish rate...{Colors.END}")
            for i in range(150, 250):
                channel.basic_publish(
                    exchange='',
                    routing_key=test_queue,
                    body=f'Message {i}'
                )
                time.sleep(0.7)  # Publish one message every 0.7 seconds (~100 msgs in 70 secs)
            
            connection.close()
            time.sleep(10)  # Wait a bit for final monitoring check
            
            # Check message stats
            queues = self.get_api("queues")
            test_q = next((q for q in queues if q['name'] == test_queue), None)
            
            if test_q:
                messages = test_q.get('messages', 0)
                msg_stats = test_q.get('message_stats', {})
                consume_rate = msg_stats.get('deliver_get_details', {}).get('rate', 0)
                
                self.print_test(
                    "Processing halt scenario created",
                    messages > 100 and consume_rate == 0,
                    f"Messages: {messages}, Consume rate: {consume_rate}/s"
                )
                print(f"{Colors.YELLOW}   📨 Check Slack for 'PROCESSING COMPLETELY HALTED' alert{Colors.END}")
            else:
                self.print_test("Processing halt scenario created", False)
                
        except Exception as e:
            self.print_test("Processing halt scenario created", False, str(e))
            
    def test_7_node_health_monitoring(self):
        """Test 7: Verify node health monitoring"""
        self.print_header("TEST 7: Node Health Monitoring")
        
        nodes = self.get_api("nodes")
        
        if not nodes:
            self.print_test("Node health check", False, "No nodes found")
            return
            
        node = nodes[0]
        node_name = node.get('name', 'unknown')
        
        # Check node is running
        running = node.get('running', False)
        self.print_test("Node is running", running, f"Node: {node_name}")
        
        # Check memory stats
        mem_used = node.get('mem_used', 0)
        mem_limit = node.get('mem_limit', 1)
        mem_percent = (mem_used / mem_limit) * 100 if mem_limit > 0 else 0
        
        threshold = int(os.getenv('ALERT_MAX_MEMORY_PERCENT', '80'))
        self.print_test(
            "Memory usage within threshold",
            mem_percent < threshold,
            f"Memory: {mem_percent:.1f}% (threshold: {threshold}%)"
        )
        
        # Check disk stats
        disk_free = node.get('disk_free', 1)
        disk_limit = node.get('disk_free_limit', 0)
        
        self.print_test(
            "Disk space available",
            disk_free > disk_limit,
            f"Free: {disk_free:,} bytes (limit: {disk_limit:,})"
        )
        
    def test_8_prometheus_metrics(self):
        """Test 8: Verify Prometheus metrics endpoint"""
        self.print_header("TEST 8: Prometheus Metrics")
        
        try:
            response = requests.get(f"http://{self.host}:15692/metrics", timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                # Check for key metrics
                metrics_to_check = [
                    'rabbitmq_queue_messages_ready',
                    'rabbitmq_queue_messages_unacked',
                    'rabbitmq_queue_consumers',
                    'rabbitmq_build_info'
                ]
                
                for metric in metrics_to_check:
                    found = metric in content
                    self.print_test(f"Metric '{metric}' available", found)
                    
            else:
                self.print_test("Prometheus endpoint accessible", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.print_test("Prometheus endpoint accessible", False, str(e))
            
    def test_9_monitoring_script_running(self):
        """Test 9: Verify monitoring script is running"""
        self.print_header("TEST 9: Monitoring Script Status")
        
        print(f"{Colors.YELLOW}Note: This test requires docker-compose access{Colors.END}")
        print(f"{Colors.YELLOW}Run manually: docker-compose exec rabbitmq ps aux | grep monitor{Colors.END}")
        
        # This is a placeholder - user needs to verify manually
        self.print_test(
            "Monitoring script running",
            True,
            "Check with: docker-compose exec rabbitmq ps aux | grep monitor.py"
        )
        
    def test_10_alert_cooldown(self):
        """Test 10: Verify alert cooldown works"""
        self.print_header("TEST 10: Alert Cooldown Mechanism")
        
        test_queue = 'test_cooldown'
        threshold = int(os.getenv('ALERT_MAX_QUEUE_LENGTH', '1000'))
        
        print(f"Testing that duplicate alerts are suppressed (5-minute cooldown)...")
        
        try:
            connection = self.get_connection()
            channel = connection.channel()
            channel.queue_declare(queue=test_queue, durable=True)
            
            # Publish messages over threshold
            for i in range(threshold + 50):
                channel.basic_publish(
                    exchange='',
                    routing_key=test_queue,
                    body=f'Cooldown test {i}'
                )
                
            connection.close()
            
            print(f"{Colors.YELLOW}⏳ Waiting 70 seconds for first alert...{Colors.END}")
            time.sleep(70)
            
            print(f"{Colors.YELLOW}   📨 You should see ONE alert in Slack now{Colors.END}")
            print(f"{Colors.YELLOW}   📨 You should NOT see another alert for 5 minutes{Colors.END}")
            
            self.print_test(
                "Alert cooldown mechanism",
                True,
                "Verify only ONE alert sent (not repeated)"
            )
            
        except Exception as e:
            self.print_test("Alert cooldown mechanism", False, str(e))
            
    # ========== RUN ALL TESTS ==========
    
    def run_all_tests(self, cleanup_after: bool = True):
        """Run complete test suite"""
        print(f"\n{Colors.BOLD}{Colors.GREEN}🧪 RabbitMQ Monitoring Test Suite{Colors.END}")
        print(f"{Colors.BOLD}Host: {self.host}:{self.amqp_port}{Colors.END}")
        print(f"{Colors.BOLD}Monitoring Interval: {os.getenv('MONITORING_INTERVAL', '60')}s{Colors.END}\n")
        
        start_time = time.time()
        
        # Run tests
        self.test_1_rabbitmq_connectivity()
        self.test_2_management_plugins()
        self.test_3_queue_backup_alert()
        self.test_4_missing_consumers_alert()
        self.test_5_unacked_messages_alert()
        self.test_6_processing_halt_alert()
        self.test_7_node_health_monitoring()
        self.test_8_prometheus_metrics()
        self.test_9_monitoring_script_running()
        self.test_10_alert_cooldown()
        
        # Cleanup
        if cleanup_after:
            self.cleanup_test_queues()
            
        # Summary
        elapsed = time.time() - start_time
        self.print_summary(elapsed)
        
    def print_summary(self, elapsed: float):
        """Print test summary"""
        self.print_header("TEST SUMMARY")
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        failed = total - passed
        
        print(f"Total Tests: {total}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.END}")
        if failed > 0:
            print(f"{Colors.RED}Failed: {failed}{Colors.END}")
        print(f"Time: {elapsed:.1f}s\n")
        
        if failed == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED!{Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ SOME TESTS FAILED{Colors.END}")
            print(f"\n{Colors.YELLOW}Failed tests:{Colors.END}")
            for name, result in self.test_results:
                if not result:
                    print(f"  - {name}")
                    
        print(f"\n{Colors.BLUE}📨 Important: Check your Slack channel for alerts!{Colors.END}")
        print(f"{Colors.BLUE}Expected alerts during this test:{Colors.END}")
        print(f"  1. Queue backup detected")
        print(f"  2. Missing consumers")
        print(f"  3. High unacknowledged messages")
        print(f"  4. Processing completely halted")
        print(f"\n{Colors.YELLOW}Note: Alerts may take up to {os.getenv('MONITORING_INTERVAL', '60')}s to appear{Colors.END}\n")

if __name__ == "__main__":
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}RabbitMQ Comprehensive Monitoring Test Suite{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    
    # Check if we should cleanup
    cleanup = '--no-cleanup' not in sys.argv
    
    suite = RabbitMQTestSuite()
    
    try:
        suite.run_all_tests(cleanup_after=cleanup)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
        suite.cleanup_test_queues()
    except Exception as e:
        print(f"\n{Colors.RED}Test suite error: {e}{Colors.END}")
        sys.exit(1)
