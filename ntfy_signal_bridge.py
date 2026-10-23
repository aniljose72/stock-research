#!/usr/bin/env python3
"""
ntfy.sh → Signal bridge (simplified)
Uses ntfy HTTP API to poll for messages.
"""

import requests
import json
import subprocess
import time
import sys
import signal
from datetime import datetime

NTFY_TOPIC = "stock-research-deploy"
SIGNAL_NUMBER = "+12144783359"
SIGNAL_RECIPIENT = "+12144783359"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}/json"

class NtfySignalBridge:
    def __init__(self, topic: str, signal_number: str, recipient: str):
        self.topic = topic
        self.signal_number = signal_number
        self.recipient = recipient
        self.running = True
        self.last_id = None
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print(f"\n🛑 Shutting down...")
        self.running = False
    
    def send_signal(self, message: str) -> bool:
        """Send message via signal-cli."""
        try:
            cmd = [
                "signal-cli", "-u", self.signal_number, "send",
                "-m", message,
                self.recipient
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"  ✅ Signal sent")
                return True
            else:
                print(f"  ❌ Signal failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("  ❌ Signal timeout")
            return False
        except Exception as e:
            print(f"  ❌ Signal error: {e}")
            return False
    
    def format_message(self, event: dict) -> str:
        """Format ntfy event for Signal."""
        title = event.get("title", "Stock Research")
        message = event.get("message", "")
        priority = event.get("priority", 3)
        
        priority_emoji = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}.get(priority, "")
        
        return f"{priority_emoji} {title}\n\n{message}"
    
    def poll_ntfy(self):
        """Poll ntfy HTTP API for new messages."""
        params = {"since": self.last_id} if self.last_id else {}
        
        try:
            resp = requests.get(NTFY_URL, params=params, timeout=30, stream=True)
            if resp.status_code != 200:
                print(f"  ⚠️  ntfy HTTP {resp.status_code}")
                return
            
            for line in resp.iter_lines():
                if not self.running:
                    break
                if not line:
                    continue
                
                try:
                    event = json.loads(line.decode('utf-8'))
                    
                    if event.get("event") == "message":
                        msg_id = event.get("id")
                        if msg_id and msg_id != self.last_id:
                            self.last_id = msg_id
                            
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📨 Received: {event.get('title', 'No title')}")
                            
                            message = self.format_message(event)
                            self.send_signal(message)
                            
                except json.JSONDecodeError:
                    continue
                    
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  ntfy poll error: {e}")
    
    def run(self):
        print(f"🔔 ntfy.sh → Signal bridge (HTTP polling)")
        print(f"   Topic: {self.topic}")
        print(f"   Signal: {self.signal_number} → {self.recipient}")
        print(f"   Polling every 5 seconds...")
        print(f"   Press Ctrl+C to stop\n")
        
        # Test signal-cli
        try:
            result = subprocess.run(
                ["signal-cli", "-u", self.signal_number, "send", "-m", "Bridge started", self.recipient],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                print(f"❌ signal-cli test failed: {result.stderr}")
                return
            print("✅ signal-cli verified")
        except Exception as e:
            print(f"❌ signal-cli error: {e}")
            return
        
        print(f"\n🔔 Polling ntfy.sh/{self.topic} every 5s...")
        print(f"   Press Ctrl+C to stop\n")
        
        while self.running:
            self.poll_ntfy()
            time.sleep(5)  # Poll every 5 seconds

def main():
    print("🔔 ntfy.sh → Signal Bridge (HTTP Polling)")
    print("=" * 50)
    
    # Verify signal-cli
    try:
        result = subprocess.run(
            ["signal-cli", "-u", SIGNAL_NUMBER, "send", "-m", "Bridge test", SIGNAL_NUMBER],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print(f"❌ signal-cli test failed: {result.stderr}")
            sys.exit(1)
        print("✅ signal-cli verified")
    except Exception as e:
        print(f"❌ signal-cli error: {e}")
        sys.exit(1)
    
    bridge = NtfySignalBridge(NTFY_TOPIC, SIGNAL_NUMBER, SIGNAL_NUMBER)
    bridge.run()

if __name__ == "__main__":
    main()