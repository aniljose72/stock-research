# Stock Research

Stock analysis with email/SMS notifications for RKLB, ASTS, SPCX.

## Installation

```bash
pip install -e .
```

## Usage

### Send Email (Gmail - full HTML)
```bash
send-email "RKLB Analysis" "$(cat research/RKLB.md)" -a research/RKLB.md
```

### Send SMS (T-Mobile - with GitHub link)
```bash
send-email "RKLB Alert" "Buy $48-55" -a research/RKLB.md --to 2144783359@tmomail.net
```

### Setup Gmail App Password
```bash
send-email --setup
```

### Convert Markdown to HTML
```bash
md-to-html research/RKLB.md
```

## Project Structure

```
stock-research/
├── research/           # Markdown analysis files
│   ├── RKLB.md
│   ├── ASTS.md
│   └── SPCX.md
├── stock_research/     # Python package
│   ├── __init__.py
│   ├── send_email.py
│   └── md_to_html.py
├── pyproject.toml
└── README.md
```

## SMS Gateways Supported

| Carrier | Gateway |
|---------|---------|
| T-Mobile | @tmomail.net |
| Verizon | @vtext.net |
| AT&T | @txt.att.net |
| Sprint | @messaging.sprintpcs.com |
| And more... | See `send_email.py` |

## Disclaimer

Not financial advice. Research based on public sentiment and financial data.