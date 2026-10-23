#!/usr/bin/env python3
"""
Run research → push to GitHub → wait for deploy → send Signal
Simple, linear pipeline.
"""

import subprocess
import time
import sys
import requests

SIGNAL_NUMBER = "+12144783359"
SIGNAL_RECIPIENT = "+12144783359"
REPO = "aniljose72/stock-research"

def run(cmd, capture=True):
    """Run command, return (success, output)."""
    print(f"  Running: {cmd[:80]}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture, text=True, timeout=300)
        print(f"  Return code: {result.returncode}")
        if result.stdout:
            print(f"  STDOUT: {result.stdout[:200]}")
        if result.stderr:
            print(f"  STDERR: {result.stderr[:200]}")
        return result.returncode == 0, result.stdout if capture else ""
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

def send_signal(title: str, message: str, priority: int = 3) -> bool:
    emoji = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}.get(priority, "")
    full = f"{emoji} {title}\n\n{message}"
    try:
        subprocess.run(
            ["signal-cli", "-u", "+12144783359", "send", "-m", full, "+12144783359"],
            capture_output=True, timeout=15, check=True
        )
        return True
    except:
        return False

def wait_for_deploy(base_dir):
    """Poll GitHub Pages until new commit is live."""
    print("⏳ Waiting for GitHub Pages to deploy...")
    
    ok, sha = run(f"cd {base_dir} && git rev-parse HEAD")
    if not ok:
        return False
    sha = sha.strip()[:7]
    
    for i in range(20):
        try:
            resp = requests.get(f"https://api.github.com/repos/aniljose72/stock-research/commits/{sha}/status", timeout=10)
            if resp.status_code == 200:
                status = resp.json().get("state")
                if status == "success":
                    print(f"✅ Deploy successful!")
                    return True
                elif status in ("failure", "error"):
                    print(f"❌ Deploy failed: {status}")
                    return False
        except:
            pass
        
        print(f"  Waiting... ({i+1}/20)")
        time.sleep(30)
    
    print("⚠️ Deploy timeout")
    return False

def main():
    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["RKLB", "ASTS", "SPCX"]
    finnhub_key = "dbd8kehr01qutcrrq7mgdbd8kehr01qutcrrq7n0"
    base_dir = "/Users/aniljose/workspace/stock-research"
    
    print(f"🚀 Starting research for: {', '.join(tickers)}")
    
    # 1. Run research
    print("\n📊 Running research...")
    for t in tickers:
        print(f"  Researching {t}...")
        ok, out = run(f"cd {base_dir} && python3 .opencode/skill/stock_research/research.py --ticker {t} --finnhub-key {finnhub_key}")
        if not ok:
            send_signal("❌ Research Failed", f"Failed for {t}: {out}", 1)
            return 1
        print(f"  ✅ {t} done")
    print("✅ Research complete")
    
    # 2. Commit and push
    print("\n📤 Pushing to GitHub...")
    ok, out = run(f"cd {base_dir} && git add research/ docs/research/ && git diff --staged --quiet || git commit -m 'Update research' && git push")
    if not ok:
        send_signal("❌ Push Failed", f"Git push failed: {out}", 1)
        return 1
    print("✅ Pushed to GitHub")
    
    # Write deployment timestamp and regenerate markdown files
    print("\n🕐 Writing deployment timestamp...")
    ok, out = run(f"cd {base_dir} && python3 .opencode/skill/stock_research/research.py --write-deploy-timestamp")
    if not ok:
        print(f"  Warning: Could not write deploy timestamp: {out}")
    
    # Regenerate all markdown files with the new deployment timestamp
    print("\n🔄 Regenerating markdown files with deployment timestamp...")
    for t in tickers:
        ok, out = run(f"cd {base_dir} && python3 .opencode/skill/stock_research/research.py --ticker {t} --finnhub-key dbd8kehr01qutcrrq7mgdbd8kehr01qutcrrq7n0")
        if not ok:
            print(f"  Warning: Could not regenerate {t}: {out}")
        else:
            print(f"  ✅ {t} regenerated")
    
    # 3. Wait for deploy
    print("\n🌐 Waiting for GitHub Pages deploy...")
    if not wait_for_deploy(base_dir):
        send_signal("❌ Deploy Timeout", "GitHub Pages didn't deploy in time", 1)
        return 1
    
    # 4. Verify page is live
    print("\n🔍 Verifying site is live...")
    try:
        resp = requests.get("https://aniljose72.github.io/stock-research/", timeout=10)
        if resp.status_code != 200:
            raise Exception(f"Status {resp.status_code}")
    except Exception as e:
        send_signal("❌ Site Down", f"GitHub Pages not responding: {e}", 1)
        return 1
    print("✅ Site is live!")
    
    # 4. Send success Signal
    tickers_list = sys.argv[1:] if len(sys.argv) > 1 else ["RKLB", "ASTS", "SPCX"]
    urls = "\n".join([f"• {t}: https://aniljose72.github.io/stock-research/research/{t}/" for t in tickers_list])
    send_signal(
        "✅ Research Complete & Deployed",
        f"All {len(tickers_list)} tickers researched and live:\n\n{urls}\n\nSite: https://aniljose72.github.io/stock-research/",
        4
    )
    
    print("\n✅ All done!")
    return 0

if __name__ == "__main__":
    sys.exit(main())