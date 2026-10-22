#!/usr/bin/env python3
"""
Stock Research Analysis Skill
Automates stock sentiment research and analysis generation.
"""

import sys
import os
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from stock_research.send_email import send_message, public_docs_url
except ImportError:
    pass


class StockResearcher:
    def __init__(self, output_dir: str = "research", github_repo: str = None, public_docs: str = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.github_repo = github_repo or "https://github.com/aniljose72/stock-research"
        self.public_docs = public_docs or "https://aniljose72.github.io/stock-research"
        
        # Ensure docs/research exists for GitHub Pages
        self.docs_research = Path("docs/research")
        self.docs_research.mkdir(parents=True, exist_ok=True)

    def research_ticker(self, ticker: str) -> Dict:
        """
        Research a single ticker symbol.
        In a real implementation, this would:
        1. Search X/Twitter for sentiment
        2. Search financial news
        3. Get analyst price targets
        4. Get key catalysts
        """
        print(f"🔍 Researching {ticker}...")
        
        # This is a template - in practice you'd use web search APIs
        # For now, return a structured template
        return {
            "ticker": ticker.upper(),
            "name": self._get_company_name(ticker),
            "current_price": "TBD",
            "last_updated": datetime.now().isoformat(),
            "sentiment": {
                "x_mentions": "TBD",
                "bull_case": ["TBD"],
                "bear_case": ["TBD"],
                "consensus": "TBD"
            },
            "catalysts": [
                {"event": "TBD", "impact": "TBD", "timeline": "TBD"}
            ],
            "recommendations": [
                {"action": "TBD", "price_range": "TBD", "rationale": "TBD"}
            ],
            "portfolio": {
                "horizon": "TBD",
                "conviction": "TBD",
                "max_position": "TBD",
                "key_risk": "TBD"
            },
            "action_items": ["TBD"],
            "accounts": [{"account": "TBD", "focus": "TBD"}]
        }

    def _get_company_name(self, ticker: str) -> str:
        """Map ticker to company name."""
        names = {
            "RKLB": "Rocket Lab",
            "ASTS": "AST SpaceMobile",
            "ASTX": "AST SpaceMobile (2x ETF)",
            "SPCX": "SpaceX",
            "AAPL": "Apple",
            "TSLA": "Tesla",
            "NVDA": "NVIDIA",
            "MSFT": "Microsoft",
            "GOOGL": "Alphabet",
            "AMZN": "Amazon",
            "META": "Meta",
        }
        return names.get(ticker.upper(), ticker.upper())

    def generate_markdown(self, research: Dict) -> str:
        """Generate markdown analysis from research data."""
        t = research["ticker"]
        name = research["name"]
        
        md = f"""---
title: "{t} ({name}) Analysis"
date: {research['last_updated'][:10]}
categories: [Research]
tags: [{t}, Finance, Analysis]
---

## X/Twitter Sentiment & Key Discussions
- **Mentions**: {research['sentiment']['x_mentions']}
- **Bull Case**: {', '.join(research['sentiment']['bull_case'])}
- **Bear Case**: {', '.join(research['sentiment']['bear_case'])}
- **Consensus**: {research['sentiment']['consensus']}

---

## Key Catalysts

| Event | Impact | Timeline |
|-------|--------|----------|
"""
        for c in research["catalysts"]:
            md += f"| {c['event']} | {c['impact']} | {c['timeline']} |\n"
        
        md += "\n## Buy/Sell Recommendations\n\n"
        md += "| Action | Price Range | Rationale |\n|--------|-------------|-----------|\n"
        for r in research["recommendations"]:
            md += f"| {r['action']} | {r['price_range']} | {r['rationale']} |\n"
        
        md += f"""
> **Consensus**: {research['sentiment']['consensus']}

---

## Portfolio Allocation

| Horizon | Conviction | Max Position | Key Risk |
|---------|------------|--------------|----------|
| {research['portfolio']['horizon']} | {research['portfolio']['conviction']} | {research['portfolio']['max_position']} | {research['portfolio']['key_risk']} |

---

## Immediate Action Items

"""
        for i, item in enumerate(research["action_items"], 1):
            md += f"{i}. {item}\n"
        
        md += "\n## Key X/Twitter Accounts to Follow\n\n"
        md += "| Account | Focus |\n|---------|-------|\n"
        for acc in research["accounts"]:
            md += f"| {acc['account']} | {acc['focus']} |\n"
        
        md += """

---

**Disclaimer**: This is research based on public sentiment and financial data — **not financial advice**. Always do your own due diligence and consider position sizing/risk tolerance.
"""
        return md

    def save_research(self, ticker: str, markdown: str) -> tuple:
        """Save research to both research/ and docs/research/ for GitHub Pages."""
        ticker = ticker.upper()
        
        # Save to research/ (source)
        research_path = self.output_dir / f"{ticker}.md"
        research_path.write_text(markdown)
        
        # Save to docs/research/ (GitHub Pages)
        docs_path = self.docs_research / f"{ticker}.md"
        docs_path.write_text(markdown)
        
        print(f"✅ Saved: {research_path} and {docs_path}")
        return research_path, docs_path

    def get_public_url(self, ticker: str) -> str:
        """Get public GitHub Pages URL for a ticker."""
        return f"{self.public_docs}/research/{ticker.upper()}/"

    def send_alert(self, ticker: str, summary: str, provider: str = "auto", to: str = None):
        """Send alert via configured provider."""
        try:
            from stock_research.send_email import send_message
            attachment = self.output_dir / f"{ticker.upper()}.md"
            public_url = self.get_public_url(ticker)
            
            body = f"{summary}\n\nFull analysis: {public_url}"
            
            send_message(
                subject=f"{ticker} Alert",
                body=body,
                attachment_path=str(attachment) if attachment.exists() else None,
                to=to,
                provider=provider
            )
        except ImportError:
            print("⚠️  send_email module not available")


def main():
    parser = argparse.ArgumentParser(description="Stock Research Analysis")
    parser.add_argument("--ticker", help="Single ticker to research")
    parser.add_argument("--tickers", help="Comma-separated list of tickers")
    parser.add_argument("--output", default="research", help="Output directory")
    parser.add_argument("--github-repo", help="GitHub repo URL")
    parser.add_argument("--public-docs", help="GitHub Pages URL")
    parser.add_argument("--send-alert", action="store_true", help="Send alerts after research")
    parser.add_argument("--provider", default="auto", choices=["auto", "email", "signal", "whatsapp", "sms"])
    parser.add_argument("--to", help="Recipient for alerts")
    
    args = parser.parse_args()
    
    # Determine tickers
    tickers = []
    if args.ticker:
        tickers.append(args.ticker.upper())
    elif args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        parser.error("Must provide --ticker or --tickers")
    
    researcher = StockResearcher(
        output_dir=args.output,
        github_repo=args.github_repo,
        public_docs=args.public_docs
    )
    
    for ticker in tickers:
        print(f"\n{'='*50}")
        print(f"Processing {ticker}")
        print(f"{'='*50}")
        
        # Research (in real implementation, this would fetch real data)
        research = researcher.research_ticker(ticker)
        
        # Generate markdown
        markdown = researcher.generate_markdown(research)
        
        # Save
        researcher.save_research(ticker, markdown)
        
        # Print public URL
        print(f"🔗 Public URL: {researcher.get_public_url(ticker)}")
        
        # Send alert if requested
        if args.send_alert:
            summary = f"{ticker}: Research completed. Check public URL for full analysis."
            researcher.send_alert(ticker, summary, args.provider, args.to)
    
    print(f"\n✅ Completed research for: {', '.join(tickers)}")
    print(f"📁 Files saved to: {args.output}/ and docs/research/")
    print(f"🌐 Public site: {args.public_docs or 'https://aniljose72.github.io/stock-research/'}")


if __name__ == "__main__":
    main()