#!/usr/bin/env python3
"""
OffPrem weekly roundup builder.

Pulls real headlines from public restaurant-industry RSS feeds, sorts them
into OffPrem's five beats by keyword, and writes two small JSON files that
the site reads at page-load time:

  data/roundup.json  -> full curated digest, grouped by category
  data/ticker.json   -> flat list of the newest headlines for the homepage ticker

IMPORTANT — this script never rewrites, paraphrases, or reproduces article
text. It only stores: headline, source name, original link, and publish
date. Every item links back to the original publisher. No AI generation,
no fabricated content, no full-text scraping.

Run manually:   python3 scripts/fetch_roundup.py
Run on a schedule via the GitHub Action in .github/workflows/weekly-roundup.yml
"""

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# ---- Real, public restaurant-industry RSS feeds ----
# Add or remove feeds here any time. Keep it to reputable trade sources.
# NOTE: restaurantdive.com/feeds/news/ is confirmed working as of this build.
# The others are correct as of publication but publishers occasionally change
# their feed paths — if a source stops showing up in data/roundup.json, check
# GitHub Actions run logs (it prints a warning per broken feed, and simply
# skips it rather than failing the whole run) and update the URL below.
FEEDS = [
    {"url": "https://www.restaurantdive.com/feeds/news/", "source": "Restaurant Dive"},
    {"url": "https://www.qsrweb.com/rss/", "source": "QSR Web"},
    {"url": "https://www.restaurantbusinessonline.com/rss.xml", "source": "Restaurant Business"},
    {"url": "https://www.nrn.com/rss.xml", "source": "Nation's Restaurant News"},
]

# ---- Keyword rules for sorting into OffPrem's five beats ----
# Order matters: first matching category wins. Tune freely.
CATEGORY_RULES = [
    ("deals", [
        "raises", "funding", "series a", "series b", "series c", "acquire",
        "acquisition", "acquires", "merger", "merges", "investment", "valuation",
        "ipo", "round", "backed by", "venture", "buyout", "stake",
    ]),
    ("economics", [
        "margin", "labor cost", "wage", "inflation", "tariff", "minimum wage",
        "same-store sales", "same store sales", "earnings", "revenue", "profit",
        "cost of goods", "food cost", "unit economics", "swipe fee", "interchange",
    ]),
    ("marketing", [
        "loyalty", "rewards", "campaign", "rebrand", "marketing", "advertising",
        "brand", "positioning", "cmo", "app launch", "promotion", "influencer",
    ]),
    ("happenings", [
        "conference", "show", "expo", "summit", "trade show", "event",
        "keynote", "panel", "convention",
    ]),
]
DEFAULT_CATEGORY = "news"

LOOKBACK_DAYS = 10  # keep the digest fresh; widen if feeds are quiet
MAX_ITEMS_PER_CATEGORY = 8
MAX_TICKER_ITEMS = 12


def categorize(title: str) -> str:
    t = title.lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in t for kw in keywords):
            return category
    return DEFAULT_CATEGORY


def parse_date(entry) -> datetime:
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            return datetime(*val[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def clean_title(raw: str) -> str:
    # Strip stray HTML entities/tags that sometimes leak into feed titles
    return re.sub(r"<[^>]+>", "", raw).strip()


def fetch_all():
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    items = []
    errors = []

    for feed in FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
            if parsed.bozo and not parsed.entries:
                errors.append(f"{feed['source']}: failed to parse ({parsed.bozo_exception})")
                continue
            for entry in parsed.entries:
                title = clean_title(entry.get("title", "")).strip()
                link = entry.get("link", "").strip()
                if not title or not link:
                    continue
                pub_date = parse_date(entry)
                if pub_date < cutoff:
                    continue
                items.append({
                    "title": title,
                    "link": link,
                    "source": feed["source"],
                    "published": pub_date.strftime("%Y-%m-%d"),
                    "published_iso": pub_date.isoformat(),
                    "category": categorize(title),
                })
        except Exception as e:  # noqa: BLE001 - keep the pipeline resilient
            errors.append(f"{feed['source']}: {e}")

    return items, errors


def build_roundup(items):
    grouped = {"news": [], "deals": [], "economics": [], "marketing": [], "happenings": []}
    # newest first
    items_sorted = sorted(items, key=lambda x: x["published_iso"], reverse=True)

    seen_links = set()
    for item in items_sorted:
        if item["link"] in seen_links:
            continue
        seen_links.add(item["link"])
        cat = item["category"]
        if len(grouped.get(cat, [])) < MAX_ITEMS_PER_CATEGORY:
            grouped.setdefault(cat, []).append({
                "title": item["title"],
                "link": item["link"],
                "source": item["source"],
                "published": item["published"],
            })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": grouped,
    }


def build_ticker(items):
    items_sorted = sorted(items, key=lambda x: x["published_iso"], reverse=True)
    seen = set()
    ticker = []
    for item in items_sorted:
        if item["link"] in seen:
            continue
        seen.add(item["link"])
        ticker.append({"title": item["title"], "link": item["link"], "source": item["source"]})
        if len(ticker) >= MAX_TICKER_ITEMS:
            break
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": ticker,
    }


def main():
    items, errors = fetch_all()

    if errors:
        print("Feed warnings:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)

    if not items:
        print("No items fetched from any feed — leaving existing data files untouched.", file=sys.stderr)
        sys.exit(1)

    roundup = build_roundup(items)
    ticker = build_ticker(items)

    (DATA_DIR / "roundup.json").write_text(json.dumps(roundup, indent=2))
    (DATA_DIR / "ticker.json").write_text(json.dumps(ticker, indent=2))

    total = sum(len(v) for v in roundup["categories"].values())
    print(f"Wrote {total} curated items across {len(roundup['categories'])} categories.")
    print(f"Wrote {len(ticker['items'])} ticker headlines.")


if __name__ == "__main__":
    main()
