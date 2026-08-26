# OffPrem

Restaurant technology news, deals, economics, and marketing — published by Popcorn GTM.

## Structure

- `index.html`, `article.html`, `about.html`, `category-*.html`, `roundup.html` — the site pages
- `styles.css` — shared design system
- `data/roundup.json`, `data/ticker.json` — live data files, rebuilt weekly (see below)
- `js/ticker.js` — reads `data/ticker.json` and populates the homepage ticker on every page
- `scripts/fetch_roundup.py` — pulls real headlines from restaurant-industry RSS feeds, sorts
  them into OffPrem's five beats by keyword, and writes the two JSON files above
- `.github/workflows/weekly-roundup.yml` — runs the script every Sunday night automatically

## How the weekly automation works

1. Every Sunday at ~11 PM ET, GitHub Actions runs `scripts/fetch_roundup.py`.
2. The script pulls headlines from a small list of public restaurant-trade RSS feeds
   (see the `FEEDS` list at the top of the script — edit freely).
3. It **never rewrites or reproduces article text.** It only stores each item's headline,
   source name, original link, and publish date. Every item on the site links straight to
   the original publisher.
4. It writes `data/roundup.json` (the full curated digest, shown on `roundup.html`) and
   `data/ticker.json` (a shorter list for the scrolling ticker on every page).
5. The Action commits and pushes those two files back to this repo.
6. If this repo is connected to Netlify via Git (Netlify → Add new site → Import from Git),
   that push triggers an automatic redeploy — no manual drag-and-drop needed, ever again.

## Editing the feed list

Open `scripts/fetch_roundup.py` and edit the `FEEDS` list near the top. Add a trade source's
RSS URL and a short label; remove one that stops being useful. If a feed URL goes stale, the
script logs a warning and skips it — it won't break the rest of the run.

## Editing the category rules

Same file, `CATEGORY_RULES` — keyword lists that sort headlines into News / Deals / Economics /
Marketing / Happenings. Tune freely.

## Running it manually

```
pip install -r requirements.txt
python3 scripts/fetch_roundup.py
```
