#!/usr/bin/env python3
"""Update news.json from official cybersecurity RSS feeds; standard library only."""
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from html import unescape
import time
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "news.json"
# Verified manual titles for representative advisories. Keep identifiers in original form.
MANUAL_TRANSLATIONS = {
    "CISA Adds Four Known Exploited Vulnerabilities to Catalog": "CISA 將四項已知遭利用的漏洞加入目錄",
    "Elecbrakes EB2, VM1, ELBC2000": "Elecbrakes EB2、VM1、ELBC2000 資安公告",
    "libumqtt": "libumqtt 資安公告",
    "Autonomy Logic OpenPLC Runtime": "Autonomy Logic OpenPLC Runtime 資安公告",
}

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



def translate_title(title):
    """Machine translate public article titles; empty means unavailable, not a fabricated title.

    MyMemory free public endpoint may throttle or go offline; original titles stay intact.
    """
    if title in MANUAL_TRANSLATIONS:
        return MANUAL_TRANSLATIONS[title]
    if re.search(r"[\u4e00-\u9fff]", title):
        return title
    params = urlencode({"q": title[:400], "langpair": "en|zh-TW"})
    req = Request("https://api.mymemory.translated.net/get?" + params,
                  headers={"User-Agent": "CyberSafetyGuide/2.0 (educational public RSS translation)"})
    with urlopen(req, timeout=12) as response:
        data = json.load(response)
    code = data.get("responseStatus")
    translation = unescape(str(data.get("responseData", {}).get("translatedText", ""))).strip()
    if str(code) != "200" or not translation or not re.search(r"[\u4e00-\u9fff]", translation):
        return ""
    if any(x in translation.lower() for x in ("mymemory warning", "query length", "daily quota", "too many requests")):
        return ""
    # Explicit Traditional Chinese conversion if OpenCC is available (see workflow).
    try:
        from opencc import OpenCC
        translation = OpenCC("s2twp").convert(translation)
    except ImportError:
        pass
    return translation[:280]


def add_translations(items, previously_saved):
    cache = {(x.get("url"), x.get("title")): x.get("title_zh", "")
             for x in previously_saved if isinstance(x, dict) and x.get("title_zh")}
    successes = 0
    for i, item in enumerate(items):
        pair = (item["url"], item["title"])
        zh = cache.get(pair) or MANUAL_TRANSLATIONS.get(item["title"], "")
        if not zh:
            try:
                zh = translate_title(item["title"])
                if zh:
                    successes += 1
                time.sleep(.15)  # Be considerate of public translation service.
            except Exception as exc:
                print(f"WARNING: translation unavailable for {item['title'][:60]!r}: {exc}")
        if zh:
            item["title_zh"] = zh
    print(f"Translated {successes} new titles; others retained from cache/manual or English fallback")
    return items

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
    # Preserve previously translated titles so daily runs do not re-translate everything.
    old = {}
    if OUTPUT.exists():
        try:
            old = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    items = add_translations(deduped[:30], old.get("items", []))
    payload = {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "items": items}
    if old.get("items") == items:
        print("No article changes; leaving news.json unchanged")
        return
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['items'])} articles to {OUTPUT.name}")


if __name__ == "__main__":
    main()
