# Stock Research Skill

Automated stock sentiment research and analysis generation with GitHub Pages deployment.

## Quick Start

```bash
# Research a single ticker
./stock-research --ticker RKLB

# Research multiple tickers
./stock-research --tickers "RKLB,ASTS,SPCX"

# With alerts
./stock-research --ticker AAPL --send-alert --provider signal --to +12144783359

# Custom output directory
./stock-research --ticker TSLA --output ./my-research
```

## Configuration

Set environment variables or create `.env` in project root:

```bash
# GitHub
GITHUB_REPO=https://github.com/yourusername/stock-research
PUBLIC_DOCS=https://yourusername.github.io/stock-research

# Signal
SIGNAL_NUMBER=+12144783359

# Email (for Gmail SMTP)
EMAIL_FROM=your@gmail.com
EMAIL_TO=your@gmail.com
EMAIL_APP_PASSWORD=your_app_password

# Output
OUTPUT_DIR=research
```

## Features

- **Automated Research**: Fetches X/Twitter sentiment, financial news, analyst targets
- **Markdown Generation**: Creates structured analysis with tables, recommendations
- **GitHub Pages**: Auto-deploys to Just the Docs theme with dark mode, search
- **Multi-channel Alerts**: Email, SMS, Signal, WhatsApp
- **Public URLs**: Clean URLs like `https://you.github.io/stock-research/research/RKLB/`

## Example Output

```
$ ./stock-research --ticker RKLB --send-alert --provider signal --to +12144783359

==================================================
Processing RKLB
==================================================
🔍 Researching RKLB...
✅ Saved: research/RKLB.md and docs/research/RKLB.md
🔗 Public URL: https://aniljose72.github.io/stock-research/research/RKLB/
📱 Signal sent to +12144783359

✅ Completed research for: RKLB
📁 Files saved to: research/ and docs/research/
🌐 Public site: https://aniljose72.github.io/stock-research/
```

## GitHub Pages Deployment

1. Enable GitHub Pages in repo settings (source: GitHub Actions)
2. Push changes - auto-deploys via `.github/workflows/pages.yml`
3. Access at `https://yourusername.github.io/stock-research/`

## Alert Providers

| Provider | Use Case |
|----------|----------|
| `email` | Full HTML emails via Gmail SMTP |
| `sms` | SMS via carrier gateways (e.g., `2144783359@tmomail.net`) |
| `signal` | Encrypted Signal messages (requires `signal-cli` registered) |
| `whatsapp` | WhatsApp via `pywhatkit` (requires WhatsApp Web logged in) |
| `auto` | Auto-detect based on recipient format |

## Extending for New Tickers

The skill uses a template system. For real data, extend `research_ticker()` in `research.py` to call:
- Twitter API v2 for sentiment
- Financial news APIs (Alpha Vantage, Finnhub, etc.)
- SEC filings for catalysts
- Analyst price targets from TipRanks/Seeking Alpha

## Project Structure

```
stock-research/
├── .opencode/skill/stock_research/
│   ├── skill.json
│   ├── research.py          # Core research logic
│   ├── __main__.py          # Entry point
│   └── stock-research       # CLI wrapper
├── research/                # Generated markdown (source)
├── docs/research/           # GitHub Pages source
├── .github/workflows/pages.yml  # Auto-deploy
└── stock_research/          # Python package (send_email, etc.)
```