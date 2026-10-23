#!/usr/bin/env python3
"""
Simple ntfy.sh → Signal bridge for Mac
Uses streaming HTTP with timeout to poll for new messages.
"""

import requests
import json
import subprocess
import time
import sys
import signal

NTFY_TOPIC = "stock-research-deploy"
SIGNAL_NUMBER = "+12144783359"
SIGNAL_RECIPIENT = "+12144783359"
NTFY_STREAM = f"https://ntfy.sh/{NTFY_TOPIC}/json"

class SimpleBridge:
    def __init__(self):
        self.running = True
        self.last_id = None
        signal.signal(signal.SIGINT, self._handler)
        signal.signal(signal.SIGTERM, self._handler)
    
    def _handler(self, signum, frame):
        print("\n🛑 Stopping...")
        self.running = False
    
    def send_signal(self, title: str, message: str, priority: int = 3) -> bool:
        """Send via signal-cli on Mac."""
        emoji = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}.get(priority, "")
        full_msg = f"{emoji} {title}\n\n{message}"
        
        try:
            result = subprocess.run([
                "signal-cli", "-u", "+12144783359", "send",
                "-m", full_msg, "+12144783359"
            ], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                print(f"  ✅ Signal sent: {title}")
                return True
            else:
                print(f"  ❌ Signal error: {result.stderr}")
                return False
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False
    
    def poll_once(self):
        """Single poll - read from streaming endpoint until message or timeout."""
        try:
            resp = requests.get(NTFY_STREAM, stream=True, timeout=(3, 10))  # (connect, read)
            
            if resp.status_code != 200:
                return
            
            for line in resp.iter_lines(decode_unicode=True):
                if not self.running:
                    break
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if event.get("event") == "message":
                        msg_id = event.get("id")
                        if self.last_id and msg_id == self.last_id:
                            return  # Already seen
                        
                        if self.last_id is None:
                            self.last_id = msg_id
                            return  # First run, just record
                        
                        # New message!
                        title = event.get("title", "Deploy")
                        message = event.get("message", "")
                        priority = event.get("priority", 3)
                        
                        print(f"📩 {title}")
                        self.send_signal(title, event.get("message", ""), event.get("priority", 3))
                        self.last_id = msg_id
                        return
                    elif event.get("event") == "open":
                        continue  # Skip open events
                        
                except json.JSONDecodeError:
                    continue
                    
        except requests.exceptions.ReadTimeout:
            pass  # Expected - we use timeout to break the stream
        except Exception as e:
            print(f"Poll error: {e}")
    
    def send_signal(self, title: str, message: str, priority: int = 3) -> bool:
        """Send via signal-cli on Mac."""
        emoji = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}.get(priority, "")
        full_msg = f"{emoji} {title}\n\n{message}"
        
        try:
            result = subprocess.run([
                "signal-cli", "-u", "+12144783359", "send",
                "-m", full_msg, "+12144783359"
            ], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                print(f"  ✅ Signal sent: {title}")
                return True
            else:
                print(f"  ❌ Signal error: {result.stderr}")
                return False
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False
    
    def run(self):
        # Test signal-cli
        try:
            subprocess.run(["signal-cli", "-u", "+12144783359", "send", "-m", "Bridge started", "+12144783359"], 
                          capture_output=True, timeout=10, check=True)
            print("✅ signal-cli OK")
        except Exception as e:
            print(f"❌ signal-cli error: {e}")
            return
        
        # Initialize last_id from latest message
        try:
            resp = requests.get(NTFY_STREAM, stream=True, timeout=3)
            for line in resp.iter_lines(decode_unicode=True):
                if line:
                    event = json.loads(line)
                    if event.get("event") == "message":
                        self.last_id = event.get("id")
                        break
        except:
            pass
        
        print(f"🔔 Polling ntfy.sh/stock-research-deploy every 15s...")
        print("Press Ctrl+C to stop\n")
        
        while self.running:
            try:
                self.poll_once()
                time.sleep(15)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)

def main():
    print("🔔 ntfy.sh → Signal Bridge (streaming)")
    print("=" * 40)
    
    # Test signal-cli
    try:
        subprocess.run(["signal-cli", "-u", "+12144783359", "send", "-m", "Test", "+12144783359"], 
                      capture_output=True, timeout=10, check=True)
        print("✅ signal-cli OK")
    except Exception as e:
        print(f"❌ signal-cli error: {e}")
        sys.exit(1)
    
    bridge = SimpleBridge()
    bridge.run()

if __name__ == "__main__":
    main()