#!/usr/bin/env python3
"""Update news.json from official cybersecurity RSS feeds; standard library only."""
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "news.json"
FEEDS = [
    ("美國 CISA", "https://www.cisa.gov/cybersecurity-advisories/all.xml"),
    ("英國 NCSC", "https://www.ncsc.gov.uk/api/1/services/v1/news-rss-feed.xml"),
]


def content(node, name):
    child = node.find(name)
    return "" if child is None else " ".join("".join(child.itertext()).split())


def date_iso(value):
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).date().isoformat()
    except (TypeError, ValueError, OverflowError):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return ""


def fetch_feed(source, url):
    req = Request(url, headers={"User-Agent": "CyberSafetyGuide/1.0 (RSS news aggregator)", "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
    with urlopen(req, timeout=22) as response:
        xml = response.read(3_000_000)
    root = ET.fromstring(xml)
    records = []
    for item in root.findall(".//item"):
        title = content(item, "title")
        link = content(item, "link")
        date = date_iso(content(item, "pubDate"))
        if title and link.startswith("https://"):
            records.append({"title": title[:240], "source": source, "date": date, "url": link})
    # Atom fallback for feeds without RSS items.
    if not records:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//a:entry", ns):
            title = content(entry, "{http://www.w3.org/2005/Atom}title")
            link_el = entry.find("a:link[@rel='alternate']", ns) or entry.find("a:link", ns)
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            date = date_iso(content(entry, "{http://www.w3.org/2005/Atom}published") or content(entry, "{http://www.w3.org/2005/Atom}updated"))
            if title and link.startswith("https://"):
                records.append({"title": title[:240], "source": source, "date": date, "url": link})
    if not records:
        raise ValueError("No valid RSS/Atom articles found")
    return records


def main():
    collected = []
    for name, url in FEEDS:
        try:
            batch = fetch_feed(name, url)
            collected.extend(batch)
            print(f"{name}: {len(batch)} items")
        except Exception as exc:
            print(f"WARNING: {name} feed unavailable: {type(exc).__name__}: {exc}")
    if not collected:
        raise SystemExit("All feeds failed. Keeping existing news.json unchanged.")
    seen = set()
    deduped = []
    for item in sorted(collected, key=lambda x: x["date"], reverse=True):
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        deduped.append(item)
    # Do not rewrite the file when feeds are temporarily unchanged.
    payload = {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "items": deduped[:30]}
    if OUTPUT.exists():
        try:
            old = json.loads(OUTPUT.read_text(encoding="utf-8"))
            if old.get("items") == payload["items"]:
                print("No article changes; leaving news.json unchanged")
                return
        except (ValueError, OSError):
            pass
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['items'])} articles to {OUTPUT.name}")


if __name__ == "__main__":
    main()
