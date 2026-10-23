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
import requests
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from stock_research.send_email import send_message, public_docs_url
except ImportError:
    pass

# Try to import optional libraries
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import finnhub
    FINNHUB_AVAILABLE = True
except ImportError:
    FINNHUB_AVAILABLE = False


class StockResearcher:
    def __init__(self, output_dir: str = "research", github_repo: str = None, public_docs: str = None, finnhub_key: str = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.github_repo = github_repo or "https://github.com/aniljose72/stock-research"
        self.public_docs = public_docs or "https://aniljose72.github.io/stock-research"
        
        # Ensure docs/research exists for GitHub Pages
        self.docs_research = Path("docs/research")
        self.docs_research.mkdir(parents=True, exist_ok=True)
        
        # Deployment timestamp file
        self.deploy_timestamp_file = Path("docs/research/.deploy_timestamp")
        
        # API clients
        self.finnhub_client = None
        if FINNHUB_AVAILABLE and finnhub_key:
            self.finnhub_client = finnhub.Client(api_key=finnhub_key)

    def _get_deploy_timestamp(self) -> Optional[str]:
        """Read deployment timestamp from file."""
        if self.deploy_timestamp_file.exists():
            return self.deploy_timestamp_file.read_text().strip()
        return None

    def _write_deploy_timestamp(self):
        """Write current timestamp as deployment timestamp."""
        ts = datetime.now(timezone.utc).isoformat()
        self.deploy_timestamp_file.write_text(ts)
        return ts

    def write_deploy_timestamp(self):
        """Write deployment timestamp after all research files are saved."""
        ts = self._write_deploy_timestamp()
        print(f"✅ Deployment timestamp written: {ts}")
        return ts

    def research_ticker(self, ticker: str) -> Dict:
        """
        Research a single ticker symbol using free APIs:
        1. yfinance - price, technical data, fundamentals
        2. Finnhub - news, analyst targets (requires free API key)
        2. SEC EDGAR - filings
        4. Twitter sentiment (via Nitter instances)
        """
        print(f"🔍 Researching {ticker}...")
        ticker = ticker.upper()
        
        # Gather data from all sources
        price_data = self._get_price_data(ticker)
        news = self._get_news(ticker)
        analyst = self._get_analyst_data(ticker)  # Now uses yfinance
        filings = self._get_sec_filings(ticker)
        sentiment = self._get_twitter_sentiment(ticker)
        
        # Synthesize research
        return self._synthesize_research(ticker, price_data, news, analyst, filings, sentiment)

    def _get_price_data(self, ticker: str) -> Dict:
        """Get price and technical data from yfinance."""
        if not YFINANCE_AVAILABLE:
            return {"error": "yfinance not installed"}
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="3mo")
            
            current_price = info.get("currentPrice") or info.get("regularMarketPrice") or hist["Close"].iloc[-1] if not hist.empty else None
            
            # Calculate technical indicators
            sma_20 = hist["Close"].rolling(20).mean().iloc[-1] if len(hist) >= 20 else None
            sma_50 = hist["Close"].rolling(50).mean().iloc[-1] if len(hist) >= 50 else None
            sma_200 = hist["Close"].rolling(200).mean().iloc[-1] if len(hist) >= 200 else None
            
            # RSI
            delta = hist["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not rsi.empty else None
            
            # Bollinger Bands (20, 2)
            bb_sma = hist["Close"].rolling(20).mean()
            bb_std = hist["Close"].rolling(20).std()
            bb_upper = bb_sma + (bb_std * 2)
            bb_lower = bb_sma - (bb_std * 2)
            bb_upper_current = bb_upper.iloc[-1] if not bb_upper.empty else None
            bb_lower_current = bb_lower.iloc[-1] if not bb_lower.empty else None
            bb_width = ((bb_upper_current - bb_lower_current) / bb_sma.iloc[-1] * 100) if bb_upper_current and bb_lower_current and bb_sma.iloc[-1] else None
            bb_percent_b = ((current_price - bb_lower_current) / (bb_upper_current - bb_lower_current)) if current_price and bb_upper_current and bb_lower_current and (bb_upper_current - bb_lower_current) != 0 else None
            
            # Volume
            avg_volume = hist["Volume"].rolling(20).mean().iloc[-1] if len(hist) >= 20 else None
            current_volume = hist["Volume"].iloc[-1] if not hist.empty else None
            
            return {
                "current_price": round(current_price, 2) if current_price else None,
                "previous_close": info.get("previousClose"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "beta": info.get("beta"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "sma_20": round(sma_20, 2) if sma_20 else None,
                "sma_50": round(sma_50, 2) if sma_50 else None,
                "sma_200": round(sma_200, 2) if sma_200 else None,
                "rsi": round(current_rsi, 1) if current_rsi else None,
                "avg_volume_20d": int(avg_volume) if avg_volume else None,
                "current_volume": int(current_volume) if current_volume else None,
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "short_float": info.get("shortPercentOfFloat"),
                "short_ratio": info.get("shortRatio"),
                # Bollinger Bands
                "bb_upper": round(bb_upper_current, 2) if bb_upper_current else None,
                "bb_lower": round(bb_lower_current, 2) if bb_lower_current else None,
                "bb_width": round(bb_width, 2) if bb_width else None,
                "bb_percent_b": round(bb_percent_b, 3) if bb_percent_b else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_news(self, ticker: str, limit: int = 10) -> List[Dict]:
        """Get recent news from Finnhub."""
        if not self.finnhub_client:
            return [{"note": "Finnhub API key not configured"}]
        
        try:
            # Get news from last 7 days
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            to_date = datetime.now().strftime("%Y-%m-%d")
            news = self.finnhub_client.company_news(ticker, _from=from_date, to=to_date)
            
            # Sort by datetime descending, take top N
            news_sorted = sorted(news, key=lambda x: x.get("datetime", 0), reverse=True)[:limit]
            
            return [
                {
                    "headline": item.get("headline", ""),
                    "summary": item.get("summary", "")[:200],
                    "url": item.get("url", ""),
                    "source": item.get("source", ""),
                    "datetime": datetime.fromtimestamp(item.get("datetime", 0)).strftime("%Y-%m-%d %H:%M"),
                    "sentiment": item.get("sentiment", 0)
                }
                for item in news_sorted if item.get("headline")
            ]
        except Exception as e:
            return [{"error": str(e)}]

    def _get_analyst_data(self, ticker: str) -> Dict:
        """Get analyst price targets and recommendations from yfinance."""
        if not YFINANCE_AVAILABLE:
            return {"error": "yfinance not installed"}
        
        try:
            stock = yf.Ticker(ticker)
            
            # Get analyst price targets
            analyst_targets = {}
            try:
                targets = stock.analyst_price_targets
                if targets:
                    analyst_targets = {
                        "target_mean": targets.get("mean"),
                        "target_median": targets.get("median"),
                        "target_high": targets.get("high"),
                        "target_low": targets.get("low"),
                        "current_price": targets.get("current"),
                    }
            except:
                pass
            
            # Get recommendations
            recommendations = {}
            try:
                recs = stock.recommendations
                if recs is not None and not recs.empty:
                    latest = recs.iloc[0]
                    recommendations = {
                        "strong_buy": int(latest.get("strongBuy", 0)),
                        "buy": int(latest.get("buy", 0)),
                        "hold": int(latest.get("hold", 0)),
                        "sell": int(latest.get("sell", 0)),
                        "strong_sell": int(latest.get("strongSell", 0)),
                        "period": str(recs.index[0]) if len(recs.index) > 0 else "Current",
                    }
            except:
                pass
            
            # Also get from info
            info = stock.info
            return {
                "target_mean": info.get("targetMeanPrice"),
                "target_median": info.get("targetMedianPrice"),
                "target_high": info.get("targetHighPrice"),
                "target_low": info.get("targetLowPrice"),
                "target_high_detailed": analyst_targets.get("target_high"),
                "target_low_detailed": analyst_targets.get("target_low"),
                "target_mean_detailed": analyst_targets.get("target_mean"),
                "target_median_detailed": analyst_targets.get("target_median"),
                "current_price_target": analyst_targets.get("current_price"),
                "strong_buy": info.get("numberOfAnalystOpinions", 0),
                "recommendations": recommendations,
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_sec_filings(self, ticker: str, limit: int = 5) -> List[Dict]:
        """Get recent SEC filings from EDGAR."""
        try:
            # Use SEC's company search
            cik_map = {
                "RKLB": "0001748719",
                "ASTS": "0001723130",
                "SPCX": "0001836170",  # SpaceX is private, may not have filings
                "AAPL": "0000320193",
                "TSLA": "0001318605",
                "NVDA": "0001045810",
                "MSFT": "0000789019",
                "GOOGL": "0001652044",
                "AMZN": "0001018724",
                "META": "0001326801",
            }
            
            cik = cik_map.get(ticker.upper())
            if not cik:
                return [{"note": f"No CIK mapping for {ticker}"}]
            
            # SEC EDGAR API
            url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
            headers = {"User-Agent": "StockResearch/1.0 (anil.jose@gmail.com)"}
            
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return [{"error": f"SEC API error: {resp.status_code}"}]
            
            data = resp.json()
            recent = data.get("filings", {}).get("recent", {})
            
            filings = []
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            primary_docs = recent.get("primaryDocument", [])
            
            for i in range(min(limit, len(forms))):
                filings.append({
                    "form": forms[i],
                    "date": dates[i],
                    "accession": accessions[i],
                    "doc_url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accessions[i].replace('-', '')}/{primary_docs[i]}"
                })
            
            return filings
        except Exception as e:
            return [{"error": str(e)}]

    def _get_twitter_sentiment(self, ticker: str) -> Dict:
        """Get Twitter sentiment via Nitter instances (free, no API key)."""
        try:
            # Try a few Nitter instances
            instances = [
                "https://nitter.net",
                "https://nitter.1d4.us",
                "https://nitter.moomoo.me",
            ]
            
            query = f"${ticker} OR #{ticker}"
            total_mentions = 0
            sample_tweets = []
            
            for instance in instances:
                try:
                    # Search endpoint
                    url = f"{instance}/search"
                    params = {
                        "q": query,
                        "f": "tweets",
                        "since": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                        "until": datetime.now().strftime("%Y-%m-%d"),
                    }
                    headers = {"User-Agent": "Mozilla/5.0"}
                    
                    resp = requests.get(url, params=params, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        # Parse HTML for tweet count (simplified)
                        content = resp.text
                        # This is a very rough estimate
                        mentions = content.count("timeline-item")
                        total_mentions += mentions
                        
                        # Extract a few sample tweets
                        if "tweet-content" in content:
                            # Very basic extraction
                            pass
                except:
                    continue
            
            # For now, return structure with note about limitation
            return {
                "note": "Twitter sentiment via Nitter (limited)",
                "estimated_mentions_24h": total_mentions,
                "bull_signals": ["price targets raised", "partnership announced", "launch success"],
                "bear_signals": ["delay announced", "earnings miss", "competition"],
                "consensus": "Monitor X/Twitter for real-time sentiment"
            }
        except Exception as e:
            return {"error": str(e), "note": "Twitter sentiment unavailable"}

    def _synthesize_research(self, ticker: str, price_data: Dict, news: List, analyst: Dict, filings: List, sentiment: Dict) -> Dict:
        """Synthesize all data into research structure."""
        
        # Determine bull/bear cases from news sentiment
        bull_signals = []
        bear_signals = []
        
        for item in news:
            if isinstance(item, dict) and item.get("sentiment", 0) > 0.2:
                bull_signals.append(item.get("headline", "")[:80])
            elif isinstance(item, dict) and item.get("sentiment", 0) < -0.2:
                bear_signals.append(item.get("headline", "")[:80])
        
        # Build consensus from analyst data
        consensus_parts = []
        target_mean = analyst.get("target_mean")
        target_median = analyst.get("target_median")
        target_high = analyst.get("target_high")
        target_low = analyst.get("target_low")
        
        if target_mean:
            consensus_parts.append(f"Mean PT: ${target_mean:.2f}")
        if target_median:
            consensus_parts.append(f"Median PT: ${target_median:.2f}")
        
        recs = analyst.get("recommendations", {})
        strong_buy = recs.get("strong_buy", 0)
        buy = recs.get("buy", 0)
        hold = recs.get("hold", 0)
        sell = recs.get("sell", 0)
        strong_sell = recs.get("strong_sell", 0)
        
        if strong_buy + buy > sell + strong_sell:
            consensus_parts.append("Analysts leaning bullish")
        elif sell + strong_sell > strong_buy + buy:
            consensus_parts.append("Analysts leaning bearish")
        else:
            consensus_parts.append("Mixed analyst sentiment")
        
        consensus = "; ".join(consensus_parts) if consensus_parts else "Insufficient data"
        
        # Build catalysts from news and filings
        catalysts = []
        for item in news[:5]:
            if isinstance(item, dict):
                catalysts.append({
                    "event": item.get("headline", "")[:100],
                    "impact": "Positive" if item.get("sentiment", 0) > 0.1 else "Negative" if item.get("sentiment", 0) < -0.1 else "Neutral",
                    "timeline": item.get("datetime", "Recent")
                })
        
        for filing in filings[:3]:
            if isinstance(filing, dict) and filing.get("form"):
                catalysts.append({
                    "event": f"SEC Filing: {filing['form']}",
                    "impact": "Neutral",
                    "timeline": filing.get("date", "Recent")
                })
        
        # Build recommendations based on technical + analyst
        price = price_data.get("current_price")
        target_mean = analyst.get("target_mean")
        target_median = analyst.get("target_median")
        rsi = price_data.get("rsi")
        
        recommendations = []
        if price and target_mean:
            upside = (target_mean - price) / price * 100
            if upside > 20:
                action = "Strong Buy"
                rationale = f"{upside:.0f}% upside to mean PT ${target_mean:.2f}"
            elif upside > 10:
                action = "Buy"
                rationale = f"{upside:.0f}% upside to mean PT ${target_mean:.2f}"
            elif upside > -5:
                action = "Hold"
                rationale = f"Near fair value (PT ${target_mean:.2f})"
            else:
                action = "Sell"
                rationale = f"{upside:.0f}% downside to mean PT ${target_mean:.2f}"
        elif price and target_median:
            upside = (target_median - price) / price * 100
            if upside > 20:
                action = "Strong Buy"
                rationale = f"{upside:.0f}% upside to median PT ${target_median:.2f}"
            elif upside > 10:
                action = "Buy"
                rationale = f"{upside:.0f}% upside to median PT ${target_median:.2f}"
            elif upside > -5:
                action = "Hold"
                rationale = f"Near fair value (PT ${target_median:.2f})"
            else:
                action = "Sell"
                rationale = f"{upside:.0f}% downside to median PT ${target_median:.2f}"
        else:
            action = "Research Needed"
            rationale = "Insufficient data for recommendation"
        
        recommendations.append({
            "action": action,
            "price_range": f"${price:.2f}" if price else "TBD",
            "rationale": rationale
        })
        
        # Add technical context
        tech_notes = []
        if rsi:
            if rsi > 70:
                tech_notes.append(f"RSI {rsi:.0f} - Overbought")
            elif rsi < 30:
                tech_notes.append(f"RSI {rsi:.0f} - Oversold")
            else:
                tech_notes.append(f"RSI {rsi:.0f} - Neutral")
        
        # Bollinger Bands
        bb_upper = price_data.get("bb_upper")
        bb_lower = price_data.get("bb_lower")
        bb_width = price_data.get("bb_width")
        bb_percent_b = price_data.get("bb_percent_b")
        
        if bb_upper and bb_lower:
            tech_notes.append(f"BB: ${bb_lower:.2f} - ${bb_upper:.2f} (Width: {price_data.get('bb_width', 0):.1f}%)")
        
        if bb_percent_b is not None:
            if bb_percent_b > 0.8:
                tech_notes.append(f"%B: {bb_percent_b:.2f} - Near upper band")
            elif bb_percent_b < 0.2:
                tech_notes.append(f"%B: {bb_percent_b:.2f} - Near lower band")
            else:
                tech_notes.append(f"%B: {bb_percent_b:.2f} - Middle range")
        
        if price_data.get("sma_20") and price_data.get("sma_50"):
            if price_data["sma_20"] > price_data["sma_50"]:
                tech_notes.append("SMA20 > SMA50 (Bullish)")
            else:
                tech_notes.append("SMA20 < SMA50 (Bearish)")
        
        # Build final research dict
        deploy_ts = self._get_deploy_timestamp()
        return {
            "ticker": ticker,
            "name": self._get_company_name(ticker),
            "current_price": price_data.get("current_price"),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "deployed_at": deploy_ts if deploy_ts else datetime.now(timezone.utc).isoformat(),
            "price_data": price_data,
            "sentiment": {
                "estimated_mentions_24h": sentiment.get("estimated_mentions_24h", 0),
                "bull_case": bull_signals[:3] or ["Monitor news flow"],
                "bear_case": bear_signals[:3] or ["Monitor risk factors"],
                "consensus": consensus,
            },
            "catalysts": catalysts[:5],
            "analyst_targets": {
                "target_mean": target_mean,
                "target_median": target_median,
                "target_high": target_high,
                "target_low": target_low,
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "strong_buy": recs.get("strong_buy", 0),
                "buy": recs.get("buy", 0),
                "hold": recs.get("hold", 0),
                "sell": recs.get("sell", 0),
                "strong_sell": recs.get("strong_sell", 0),
            },
            "recent_filings": filings[:3],
            "recommendations": recommendations,
            "technical_notes": tech_notes,
            "portfolio": {
                "horizon": "3-12 months",
                "conviction": "Medium" if target_mean else "Low",
                "max_position": "2-5%",
                "key_risk": "Monitor news flow and technical levels"
            },
            "action_items": [
                f"Monitor ${ticker} at key levels",
                "Review earnings calendar",
                "Watch for catalyst news"
            ],
            "accounts": [
                {"account": f"${ticker} on X", "focus": "Real-time sentiment"},
                {"account": f"Finnhub", "focus": "Analyst targets & news"},
                {"account": "SEC EDGAR", "focus": "Official filings"}
            ]
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
        price = research.get("current_price")
        price_data = research.get("price_data", {})
        sentiment = research.get("sentiment", {})
        analyst = research.get("analyst_targets", {})
        deployed_at = research.get("deployed_at")
        
        def fmt(val, decimals=2):
            """Format value, handling None and 'N/A'."""
            if val is None or val == 'N/A':
                return 'N/A'
            try:
                return f"{float(val):.{decimals}f}"
            except:
                return str(val)
        
        price_val = price if price else 'N/A'
        market_cap = price_data.get('market_cap')
        pe = price_data.get('pe_ratio')
        week_low = price_data.get('52_week_low')
        week_high = price_data.get('52_week_high')
        rsi = price_data.get('rsi')
        sma20 = price_data.get('sma_20')
        sma50 = price_data.get('sma_50')
        bb_upper = price_data.get('bb_upper')
        bb_lower = price_data.get('bb_lower')
        bb_width = price_data.get('bb_width')
        bb_percent_b = price_data.get('bb_percent_b')
        target_mean = analyst.get('target_mean')
        target_high = analyst.get('target_high')
        target_low = analyst.get('target_low')
        strong_buy = analyst.get('strong_buy', 0)
        buy = analyst.get('buy', 0)
        hold = analyst.get('hold', 0)
        sell = analyst.get('sell', 0)
        strong_sell = analyst.get('strong_sell', 0)
        
        # Format deployment timestamp - convert UTC to Central Time (US)
        try:
            if deployed_at:
                dt = datetime.fromisoformat(deployed_at.replace('Z', '+00:00'))
                # Convert to US Central Time
                central_tz = timezone(timedelta(hours=-6))  # CST
                # Check for DST (rough approximation - March to November)
                if dt.month >= 3 and dt.month <= 11:
                    central_tz = timezone(timedelta(hours=-5))  # CDT
                central_dt = dt.astimezone(central_tz)
                deploy_ts = central_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
                deploy_date = central_dt.strftime('%Y-%m-%d')
            else:
                dt = datetime.now(timezone.utc)
                central_tz = timezone(timedelta(hours=-6))
                if dt.month >= 3 and dt.month <= 11:
                    central_tz = timezone(timedelta(hours=-5))
                central_dt = dt.astimezone(central_tz)
                deploy_ts = central_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
                deploy_date = central_dt.strftime('%Y-%m-%d')
        except:
            deploy_ts = 'N/A'
            deploy_date = 'N/A'
        
        md = f"""---
title: "{t} ({name}) Analysis"
date: {deploy_ts}
categories: [Research]
tags: [{t}, Finance, Analysis]
---

> **Created at**: {deploy_ts} (US Central Time)

## Current Price & Key Metrics
- **Current Price**: ${fmt(price_val)} ({deploy_ts})
- **Market Cap**: ${fmt(market_cap/1e9, 1) if market_cap else 'N/A'}B
- **P/E Ratio**: {fmt(pe) if pe else 'N/A'}
- **52-Week Range**: ${fmt(week_low)} - ${fmt(week_high)}
- **RSI**: {fmt(rsi, 1) if rsi else 'N/A'}
- **SMA20/SMA50**: ${fmt(sma20)} / ${fmt(sma50)}
- **Bollinger Bands**: ${fmt(bb_lower)} - ${fmt(bb_upper)} (Width: {fmt(bb_width, 1)}%, %B: {fmt(bb_percent_b, 3)})

## X/Twitter Sentiment & Key Discussions
- **Estimated 24h Mentions**: {sentiment.get('estimated_mentions_24h', 0)}
- **Bull Case**: {', '.join(sentiment.get('bull_case', ['Monitor news flow']))}
- **Bear Case**: {', '.join(sentiment.get('bear_case', ['Monitor risk factors']))}
- **Consensus**: {sentiment.get('consensus', 'Insufficient data')}

---

## Analyst Targets
- **Mean Target**: ${fmt(target_mean)} ({deploy_ts})
- **High/Low**: ${fmt(target_high)} / ${fmt(target_low)}
- **Ratings**: Strong Buy: {strong_buy}, Buy: {buy}, Hold: {hold}, Sell: {sell}, Strong Sell: {strong_sell}

---

## Technical Notes
"""
        for note in research.get("technical_notes", []):
            md += f"- {note}\n"
        
        md += "\n## Key Catalysts\n\n"
        md += "| Event | Impact | Timeline |\n|-------|--------|----------|\n"
        for c in research.get("catalysts", []):
            md += f"| {c['event']} | {c['impact']} | {c['timeline']} |\n"
        
        md += "\n## Recent SEC Filings\n\n"
        md += "| Form | Date | Link |\n|------|------|------|\n"
        for f in research.get("recent_filings", []):
            if isinstance(f, dict) and f.get("form"):
                md += f"| {f['form']} | {f.get('date', 'N/A')} | [Link]({f.get('doc_url', '#')}) |\n"
        
        md += "\n## Buy/Sell Recommendations\n\n"
        md += "| Action | Price Range | Rationale |\n|--------|-------------|-----------|\n"
        for r in research.get("recommendations", []):
            md += f"| {r['action']} | {r['price_range']} | {r['rationale']} |\n"
        
        md += f"""
> **Consensus**: {research['sentiment'].get('consensus', 'Insufficient data')}

---

## Portfolio Allocation

| Horizon | Conviction | Max Position | Key Risk |
|---------|------------|--------------|----------|
| {research['portfolio']['horizon']} | {research['portfolio']['conviction']} | {research['portfolio']['max_position']} | {research['portfolio']['key_risk']} |

---

## Immediate Action Items

"""
        for i, item in enumerate(research.get("action_items", []), 1):
            md += f"{i}. {item}\n"
        
        md += "\n## Key Resources\n\n"
        md += "| Account | Focus |\n|---------|-------|\n"
        for acc in research.get("accounts", []):
            md += f"| {acc['account']} | {acc['focus']} |\n"
        
        md += f"""

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
    parser.add_argument("--finnhub-key", help="Finnhub API key for news and analyst data")
    parser.add_argument("--write-deploy-timestamp", action="store_true", help="Write deployment timestamp file")
    
    args = parser.parse_args()
    
    # Determine tickers
    tickers = []
    if args.ticker:
        tickers.append(args.ticker.upper())
    elif args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    elif not args.write_deploy_timestamp:
        parser.error("Must provide --ticker or --tickers")
    
    researcher = StockResearcher(
        output_dir=args.output,
        github_repo=args.github_repo,
        public_docs=args.public_docs,
        finnhub_key=args.finnhub_key
    )
    
    if tickers:
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
    
    # Handle write deploy timestamp
    if args.write_deploy_timestamp:
        researcher.write_deploy_timestamp()
    
    if tickers:
        print(f"\n✅ Completed research for: {', '.join(tickers)}")
        print(f"📁 Files saved to: {args.output}/ and docs/research/")
        print(f"🌐 Public site: {args.public_docs or 'https://aniljose72.github.io/stock-research/'}")


if __name__ == "__main__":
    main()