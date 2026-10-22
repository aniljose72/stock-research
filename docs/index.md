---
title: "Stock Research"
layout: default
---

# Stock Research Analysis

Public research for **RKLB**, **ASTS/ASTX**, **SPCX** based on X (Twitter) sentiment, financial news, and analyst reports.

---

## Research Posts

{% assign sorted = site.research | sort: 'last_updated' | reverse %}
{% for post in sorted %}
<article class="research-summary">
  <h2><a href="{{ post.url }}">{{ post.title }}</a></h2>
  <p class="meta">
    <strong>Last Updated:</strong> {{ post.last_updated | date: "%B %d, %Y" }} |
    <strong>Current Price:</strong> {{ post.current_price }}
  </p>
  <p>{{ post.excerpt | strip_html | truncatewords: 50 }}</p>
  <a href="{{ post.url }}" class="read-more">Read Analysis →</a>
</article>
<hr>
{% endfor %}

---

## Quick Summary

| Ticker | Horizon | Conviction | Current Price | Key Catalyst |
|--------|---------|------------|---------------|--------------|
| **RKLB** | 3-5 years | High | ~$52-53 | Neutron delay to 2027, backlog >$3B |
| **ASTS** | 2-3 years | Speculative | ~$20-25 | AT&T deal, Block 2 launches |
| **ASTX** | Intraday | N/A | 2x ASTS | Day-trade only (decay) |
| **SPCX** | 5+ years | Very High | ~$147-159 | TSMC Terafab talks, Starlink D2C |

---

## Disclaimer

This research is based on public X/Twitter sentiment and financial data — **not financial advice**. Always do your own due diligence and consider position sizing/risk tolerance.

---

*Source: [GitHub Repository]({{ site.github.repository_url }})*