#!/usr/bin/env python3
"""
Multi-provider message sender: Email, SMS, Signal, WhatsApp.
Usage: 
  send-email "Subject" "Body" -a file.md                    # Email (Gmail)
  send-email "Subject" "Body" -a file.md --to 555@tmomail.net  # SMS
  send-email "Subject" "Body" --provider signal --to +15551234567  # Signal
  send-email "Subject" "Body" --provider whatsapp --to +15551234567  # WhatsApp
  echo "Body" | send-email "Subject" --provider signal --to +15551234567
"""

import sys
import os
import smtplib
import getpass
import re
import subprocess
import json
from pathlib import Path
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import requests
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "-q"], check=True)
    import requests

# ─── CONFIG ──────────────────────────────────────────────────────
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
FROM_EMAIL = "anil.jose@gmail.com"
TO_EMAIL   = "anil.jose@gmail.com"
GITHUB_REPO = "https://github.com/aniljose72/stock-research"
PUBLIC_DOCS = "https://aniljose72.github.io/stock-research"

# Signal
SIGNAL_NUMBER = "+12144783359"  # Your registered Signal number (change as needed)

# WhatsApp
WHATSAPP_INSTANT = True

# ─── SMS GATEWAYS ────────────────────────────────────────────────
SMS_GATEWAYS = {
    "tmomail.net", "vtext.net", "txt.att.net", "mms.att.net",
    "messaging.sprintpcs.com", "pm.sprint.com", "vmobl.com",
    "email.uscc.net", "mms.cricketwireless.net", "text.republicwireless.com",
    "msg.fi.google.com", "mymetropcs.com", "myboostmobile.com",
    "sms.mycricket.com", "mms.mycricket.com"
}

# ─── UTILITIES ───────────────────────────────────────────────────
def is_sms_gateway(addr: str) -> bool:
    """Check if address is an SMS/MMS gateway email."""
    if "@" in addr:
        domain = addr.lower().split("@")[-1]
        return domain in SMS_GATEWAYS
    return False

def is_phone_number(addr: str) -> bool:
    """Check if address is a phone number (starts with +)."""
    return addr.startswith("+") and addr[1:].isdigit()

def github_raw_url(filename: str) -> str:
    return f"{GITHUB_REPO}/raw/main/{filename}"

def public_docs_url(filename: str) -> str:
    name = Path(filename).stem
    return f"{PUBLIC_DOCS}/research/{name}/"

# ─── GMAIL APP PASSWORD ──────────────────────────────────────────
def load_app_password() -> Optional[str]:
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", FROM_EMAIL, "-s", "gmail_app_password", "-w"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return getpass.getpass(f"Gmail App Password for {FROM_EMAIL}: ")

# ─── MARKDOWN TO HTML ────────────────────────────────────────────
def markdown_to_html(md_text: str) -> str:
    try:
        import markdown
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "markdown", "-q"], check=True)
        import markdown

    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'sane_lists'], output_format='html')
    html = md.convert(md_text)

    # Style special blocks
    html = re.sub(
        r'<blockquote>\s*<p><strong>Consensus</strong>:\s*(.*?)</p>\s*</blockquote>',
        r'<div style="background:#e8f0fe;border-left:4px solid #1a73e8;padding:12px 16px;margin:16px 0;border-radius:0 8px 8px 0;"><strong style="color:#1a73e8;">Consensus:</strong> \1</div>',
        html, flags=re.DOTALL
    )
    html = re.sub(
        r'<blockquote>\s*<p><strong>Critical Note</strong>:\s*(.*?)</p>\s*</blockquote>',
        r'<div style="background:#fce8e6;border-left:4px solid #ea4335;padding:12px 16px;margin:16px 0;border-radius:0 8px 8px 0;"><strong style="color:#c5221f;">Critical Note:</strong> \1</div>',
        html, flags=re.DOTALL
    )
    html = re.sub(
        r'<blockquote>\s*<p><strong>Note</strong>:\s*(.*?)</p>\s*</blockquote>',
        r'<div style="background:#fff3cd;border-left:4px solid #f9ab00;padding:12px 16px;margin:16px 0;border-radius:0 8px 8px 0;"><strong style="color:#b06000;">Note:</strong> \1</div>',
        html, flags=re.DOTALL
    )

    css = """
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.6;color:#202124;max-width:680px;margin:0 auto;padding:20px}
h1{color:#1a73e8;border-bottom:2px solid #1a73e8;padding-bottom:8px;font-size:24px}
h2{color:#1a73e8;border-bottom:1px solid #dadce0;padding-bottom:4px;font-size:20px;margin-top:28px}
h3{color:#3c4043;font-size:17px;margin-top:20px}
h4{color:#3c4043;font-size:15px}
p{margin:12px 0}
strong{color:#202124;font-weight:600}
em{color:#5f6368}
code{background:#f1f3f4;padding:2px 6px;border-radius:3px;font-family:'SF Mono','Monaco','Consolas',monospace;font-size:13px}
pre{background:#f1f3f4;padding:16px;border-radius:8px;overflow-x:auto;border:1px solid #dadce0}
pre code{background:none;padding:0;font-size:13px;line-height:1.5}
table{border-collapse:collapse;width:100%;margin:16px 0;font-size:14px}
th,td{border:1px solid #dadce0;padding:10px 12px;text-align:left}
th{background:#f8f9fa;font-weight:600;color:#202124}
tr:nth-child(even) td{background:#f8f9fa}
tr:hover td{background:#e8f0fe}
blockquote{border-left:4px solid #1a73e8;padding-left:16px;margin:16px 0;color:#5f6368;font-style:italic}
hr{border:none;border-top:1px solid #dadce0;margin:24px 0}
ul,ol{padding-left:24px;margin:12px 0}
li{margin:6px 0}
a{color:#1a73e8;text-decoration:none}
.disclaimer{font-size:12px;color:#5f6368;border-top:1px solid #dadce0;padding-top:16px;margin-top:32px}
"""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>{css}</style></head>
<body>{html}</body></html>"""

# ─── PROVIDER: EMAIL (Gmail) ─────────────────────────────────────
def send_via_email(subject: str, body: str, attachment_path: Optional[str], to_email: str) -> bool:
    password = load_app_password()
    if not password:
        print("❌ No app password provided")
        return False

    is_gmail = to_email.lower().endswith("@gmail.com")
    is_sms = is_sms_gateway(to_email)

    html_body = None
    if attachment_path and (is_gmail or is_sms):
        md_path = Path(attachment_path)
        if md_path.suffix.lower() == '.md' and md_path.exists():
            md_text = md_path.read_text()
            if is_gmail:
                html_body = markdown_to_html(md_text)
                print(f"📧 Converted {md_path.name} → HTML")
            elif is_sms:
                public_link = public_docs_url(md_path.name)
                body = f"{body}\n\nFull analysis: {public_link}"
                print(f"📱 SMS mode: Added public docs link")

    if html_body:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
    else:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain"))

    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    try:
        import smtplib
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(FROM_EMAIL, password)
            server.send_message(msg)
        fmt = "HTML + plain" if html_body else ("SMS (with public link)" if is_sms else "plain text")
        print(f"✅ Email sent to {to_email} ({fmt})")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed. Check your App Password.")
        return False
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

# ─── PROVIDER: SIGNAL ────────────────────────────────────────────
def send_via_signal(subject: str, body: str, attachment_path: Optional[str], to_number: str) -> bool:
    """Send via signal-cli binary (linked device mode).

    Uses -u to specify the account number explicitly, which is required
    when multiple accounts exist in the local data directory.
    """
    message = f"{subject}\n\n{body}"

    if attachment_path:
        md_path = Path(attachment_path)
        if md_path.suffix.lower() == ".md" and md_path.exists():
            public_link = public_docs_url(md_path.name)
            message = f"{message}\n\nFull analysis: {public_link}"

    cmd = [
        "signal-cli",
        "-u", SIGNAL_NUMBER,
        "send",
        "-m", message,
        to_number,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ Signal sent to {to_number}")
            return True

        print(f"❌ Signal error: {result.stderr.strip()}")
        if "not registered" in result.stderr.lower():
            print(f"   Tip: Re-link with: signal-cli link -n \"mac-cli\"")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Signal timed out after 30 s")
        return False
    except FileNotFoundError:
        print("❌ signal-cli not found. Install with: brew install signal-cli")
        return False
    except Exception as e:
        print(f"❌ Signal error: {e}")
        return False

# ─── PROVIDER: WHATSAPP ──────────────────────────────────────────
def send_via_whatsapp(subject: str, body: str, attachment_path: Optional[str], to_number: str) -> bool:
    message = f"{subject}\n\n{body}"
    
    if attachment_path:
        md_path = Path(attachment_path)
        if md_path.suffix.lower() == '.md' and md_path.exists():
            public_link = public_docs_url(md_path.name)
            message = f"{message}\n\nFull analysis: {public_link}"

    try:
        import pywhatkit as kit
        # Clean number (remove +)
        clean_number = to_number.lstrip("+")
        print(f"📱 Opening WhatsApp Web for {to_number}...")
        kit.sendwhatmsg_instantly(clean_number, message, wait_time=15, tab_close=True)
        print(f"✅ WhatsApp sent to {to_number}")
        return True
    except Exception as e:
        print(f"❌ WhatsApp error: {e}")
        print("   Note: Requires WhatsApp Web logged in on default browser")
        return False

# ─── MAIN SEND FUNCTION ──────────────────────────────────────────
def send_message(
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
    to: Optional[str] = None,
    provider: str = "auto"
) -> bool:
    to = to or TO_EMAIL

    # Auto-detect provider
    if provider == "auto":
        if is_phone_number(to):
            provider = "signal"  # Default for phone numbers (more reliable)
        elif is_sms_gateway(to):
            provider = "email"   # SMS via email gateway
        else:
            provider = "email"

    print(f"📤 Sending via {provider.upper()} to {to}")

    if provider == "email":
        return send_via_email(subject, body, attachment_path, to)
    elif provider == "signal":
        return send_via_signal(subject, body, attachment_path, to)
    elif provider == "whatsapp":
        return send_via_whatsapp(subject, body, attachment_path, to)
    else:
        print(f"❌ Unknown provider: {provider}")
        return False

# ─── CLI ─────────────────────────────────────────────────────────
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Send messages via Email, SMS, Signal, or WhatsApp")
    parser.add_argument("subject", nargs="?", help="Message subject")
    parser.add_argument("body", nargs="?", help="Message body (or stdin)")
    parser.add_argument("-a", "--attachment", help="Markdown file to attach (adds public docs link)")
    parser.add_argument("--to", help="Recipient (email, +phone, or SMS gateway)")
    parser.add_argument("--provider", choices=["auto", "email", "signal", "whatsapp"], default="auto",
                        help="Message provider (default: auto-detect)")
    parser.add_argument("--setup", action="store_true", help="Store Gmail App Password in macOS Keychain")
    args = parser.parse_args()

    if args.setup:
        pwd = getpass.getpass("Enter Gmail App Password to store in Keychain: ")
        subprocess.run([
            "security", "add-generic-password",
            "-a", FROM_EMAIL, "-s", "gmail_app_password",
            "-w", pwd, "-U"
        ])
        print("✅ Stored in macOS Keychain")
        sys.exit(0)

    if not args.subject:
        parser.print_help()
        sys.exit(1)

    body = args.body
    if body is None:
        body = sys.stdin.read().strip()
    if not body:
        print("❌ No body provided")
        sys.exit(1)

    send_message(args.subject, body, args.attachment, args.to, args.provider)


if __name__ == "__main__":
    main()