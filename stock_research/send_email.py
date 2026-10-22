#!/usr/bin/env python3
"""
Send email via Gmail SMTP using App Password.
Auto-converts Markdown to HTML for Gmail recipients.
Usage: python3 send_email.py "Subject" "Body text" [attachment.md]
       echo "Body" | python3 send_email.py "Subject"
"""

import sys
import os
import smtplib
import getpass
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
FROM_EMAIL = "anil.jose@gmail.com"
TO_EMAIL   = "anil.jose@gmail.com"
GITHUB_REPO = "https://github.com/aniljose72/stock-research"  # base URL for raw md files
# ─────────────────────────────────────────────────────────────────

# SMS gateway domains (for detecting phone number emails)
SMS_GATEWAYS = {
    "tmomail.net", "vtext.net", "txt.att.net", "mms.att.net",
    "messaging.sprintpcs.com", "pm.sprint.com", "vmobl.com",
    "email.uscc.net", "mms.cricketwireless.net", "text.republicwireless.com",
    "msg.fi.google.com", "mymetropcs.com", "myboostmobile.com",
    "sms.mycricket.com", "mms.mycricket.com"
}

def is_sms_gateway(email):
    """Check if email is an SMS/MMS gateway."""
    domain = email.lower().split("@")[-1]
    return domain in SMS_GATEWAYS

def github_raw_url(filename):
    """Generate GitHub raw URL for a markdown file."""
    return f"{GITHUB_REPO}/raw/main/{filename}"


def load_app_password():
    """Load Gmail App Password from keychain or prompt."""
    try:
        import subprocess
        result = subprocess.run(
            ["security", "find-generic-password", "-a", FROM_EMAIL, "-s", "gmail_app_password", "-w"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return getpass.getpass(f"Gmail App Password for {FROM_EMAIL}: ")


def markdown_to_html(md_text):
    """Convert markdown to Gmail-friendly HTML."""
    try:
        import markdown
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "markdown", "-q"], check=True)
        import markdown

    md = markdown.Markdown(
        extensions=['tables', 'fenced_code', 'sane_lists'],
        output_format='html'
    )
    html = md.convert(md_text)

    # Style consensus/critical/note blocks
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

    # Wrap with inline styles (Gmail-safe)
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


def send_email(subject, body, attachment_path=None, to_email=None):
    password = load_app_password()
    if not password:
        print("❌ No app password provided")
        return False

    to_email = to_email or TO_EMAIL
    is_gmail = to_email.lower().endswith("@gmail.com")
    is_sms = is_sms_gateway(to_email)

    # Auto-convert markdown to HTML for Gmail, add GitHub link for SMS
    html_body = None
    if attachment_path and (is_gmail or is_sms):
        md_path = Path(attachment_path)
        if md_path.suffix.lower() == '.md' and md_path.exists():
            md_text = md_path.read_text()
            if is_gmail:
                html_body = markdown_to_html(md_text)
                print(f"📧 Converted {md_path.name} → HTML")
            elif is_sms:
                # For SMS: add GitHub link to body
                github_link = github_raw_url(md_path.name)
                body = f"{body}\n\nFull analysis: {github_link}"
                print(f"📱 SMS mode: Added GitHub link")

    # Build message
    if html_body:
        msg = MIMEMultipart("alternative")
        msg["From"] = FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
    else:
        msg = MIMEMultipart()
        msg["From"] = FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

    # No file attachments - HTML rendered in body, plain text as fallback
    # (attachment_path only used to find markdown source for HTML conversion)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(FROM_EMAIL, password)
            server.send_message(msg)
        if html_body:
            fmt = "HTML + plain"
        elif is_sms:
            fmt = "SMS (with GitHub link)"
        else:
            fmt = "plain text"
        print(f"✅ Email sent to {to_email} ({fmt})")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed. Check your App Password.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    main()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Send email via Gmail")
    parser.add_argument("subject", nargs="?", help="Email subject")
    parser.add_argument("body", nargs="?", help="Email body (or stdin)")
    parser.add_argument("-a", "--attachment", help="File to attach (auto-converts .md to HTML for Gmail)")
    parser.add_argument("--to", help="Recipient email (default: anil.jose@gmail.com)")
    parser.add_argument("--setup", action="store_true", help="Store App Password in macOS Keychain")
    args = parser.parse_args()

    if args.setup:
        pwd = getpass.getpass("Enter Gmail App Password to store in Keychain: ")
        import subprocess
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

    send_email(args.subject, body, args.attachment, args.to)