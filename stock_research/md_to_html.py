#!/usr/bin/env python3
"""
Convert Markdown to Gmail-friendly HTML with inline styles.
Usage: python3 md_to_html.py input.md [output.html]
"""

import sys
import re
from pathlib import Path

try:
    import markdown
except ImportError:
    print("Installing markdown library...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "markdown"], check=True)
    import markdown

# Gmail-compatible inline CSS
GMAIL_CSS = """
<style>
/* Gmail strips <style> tags, so we'll inline these via script */
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #202124; max-width: 680px; margin: 0 auto; padding: 20px; }
h1 { color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 8px; font-size: 24px; }
h2 { color: #1a73e8; border-bottom: 1px solid #dadce0; padding-bottom: 4px; font-size: 20px; margin-top: 28px; }
h3 { color: #3c4043; font-size: 17px; margin-top: 20px; }
h4 { color: #3c4043; font-size: 15px; }
p { margin: 12px 0; }
strong { color: #202124; font-weight: 600; }
em { color: #5f6368; }
code { background: #f1f3f4; padding: 2px 6px; border-radius: 3px; font-family: 'SF Mono', 'Monaco', 'Consolas', monospace; font-size: 13px; }
pre { background: #f1f3f4; padding: 16px; border-radius: 8px; overflow-x: auto; border: 1px solid #dadce0; }
pre code { background: none; padding: 0; font-size: 13px; line-height: 1.5; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14px; }
th, td { border: 1px solid #dadce0; padding: 10px 12px; text-align: left; }
th { background: #f8f9fa; font-weight: 600; color: #202124; }
tr:nth-child(even) td { background: #f8f9fa; }
tr:hover td { background: #e8f0fe; }
blockquote { border-left: 4px solid #1a73e8; padding-left: 16px; margin: 16px 0; color: #5f6368; font-style: italic; }
hr { border: none; border-top: 1px solid #dadce0; margin: 24px 0; }
ul, ol { padding-left: 24px; margin: 12px 0; }
li { margin: 6px 0; }
a { color: #1a73e8; text-decoration: none; }
a:hover { text-decoration: underline; }
.consensus { background: #e8f0fe; border-left: 4px solid #1a73e8; padding: 12px 16px; margin: 16px 0; border-radius: 0 8px 8px 0; }
.consensus strong { color: #1a73e8; }
.note { background: #fff3cd; border-left: 4px solid #f9ab00; padding: 12px 16px; margin: 16px 0; border-radius: 0 8px 8px 0; }
.note strong { color: #b06000; }
.critical { background: #fce8e6; border-left: 4px solid #ea4335; padding: 12px 16px; margin: 16px 0; border-radius: 0 8px 8px 0; }
.critical strong { color: #c5221f; }
.disclaimer { font-size: 12px; color: #5f6368; border-top: 1px solid #dadce0; padding-top: 16px; margin-top: 32px; }
</style>
"""

def markdown_to_gmail_html(md_text):
    """Convert markdown to HTML with Gmail-friendly styling."""
    # Custom extensions for tables, etc.
    md = markdown.Markdown(
        extensions=['tables', 'fenced_code', 'toc', 'sane_lists'],
        output_format='html'
    )
    html = md.convert(md_text)

    # Post-process for Gmail-specific tweaks
    # Convert blockquotes with **Consensus** to styled divs
    html = re.sub(
        r'<blockquote>\s*<p><strong>Consensus</strong>:\s*(.*?)</p>\s*</blockquote>',
        r'<div class="consensus"><strong>Consensus:</strong> \1</div>',
        html, flags=re.DOTALL
    )

    # Convert blockquotes with **Critical Note** to styled divs
    html = re.sub(
        r'<blockquote>\s*<p><strong>Critical Note</strong>:\s*(.*?)</p>\s*</blockquote>',
        r'<div class="critical"><strong>Critical Note:</strong> \1</div>',
        html, flags=re.DOTALL
    )

    # Convert blockquotes with **Note** to styled divs
    html = re.sub(
        r'<blockquote>\s*<p><strong>Note</strong>:\s*(.*?)</p>\s*</blockquote>',
        r'<div class="note"><strong>Note:</strong> \1</div>',
        html, flags=re.DOTALL
    )

    # Convert horizontal rules
    html = html.replace('<hr />', '<hr>')

    # Wrap in full HTML document
    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{GMAIL_CSS}
</head>
<body>
{html}
</body>
</html>"""

    return full_html


def inline_css_for_gmail(html):
    """
    Gmail strips <style> tags, so we need to inline critical styles.
    This is a simplified version - for production, use `premailer` library.
    """
    # For now, return as-is. Gmail actually supports <style> in <head> now.
    # But to be safe, we'll also provide a version with key styles inlined.
    return html


if __name__ == "__main__":
    main()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 md_to_html.py input.md [output.html]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.with_suffix('.html')

    md_text = input_path.read_text()
    html = markdown_to_gmail_html(md_text)
    output_path.write_text(html)
    print(f"✅ Converted: {input_path} → {output_path}")