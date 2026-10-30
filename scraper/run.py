"""Collect all sources, keep events still open, write site/data/events.json.

Usage: python -m scraper.run
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from . import social, sources
from .common import Event, TODAY, iso, parse_iso

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "data" / "events.json"

# Social posts rarely state a parsable date; keep them this long after first seen.
UNDATED_TTL_DAYS = 21


def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\b(20\d\d|hackathon|hackathonu|datathon|ideathon)\b", " ", t)
    return re.sub(r"[^a-z0-9]+", "", t)


def is_active(e: Event) -> bool:
    deadline = parse_iso(e.deadline)
    if deadline:
        return deadline >= TODAY
    last = parse_iso(e.end) or parse_iso(e.start)
    if last:
        return last >= TODAY
    seen = parse_iso(e.first_seen) or TODAY
    return (TODAY - seen).days <= UNDATED_TTL_DAYS


def clean_dates(e: Event) -> None:
    for f in ("start", "end", "deadline"):
        setattr(e, f, iso(parse_iso(getattr(e, f))))


def main() -> None:
    previous = {}
    if OUT.exists():
        previous = {e["id"]: e for e in json.loads(OUT.read_text(encoding="utf-8")).get("events", [])}

    collected: list[Event] = []
    stats: dict[str, int] = {}
    collectors = dict(sources.ALL) | {"Sosyal & Web": social.collect}
    for name, fn in collectors.items():
        t0 = time.time()
        try:
            items = fn()
        except Exception as e:  # one broken site must not kill the run
            print(f"[{name}] HATA: {e}")
            items = []
        stats[name] = len(items)
        print(f"[{name}] {len(items)} kayıt ({time.time() - t0:.1f}s)")
        collected.extend(items)

    # dedupe: same URL, or same normalized title (platform listings first, social last)
    by_id: dict[str, Event] = {}
    titles: set[str] = set()
    for e in collected:
        if not e.title or not e.url:
            continue
        key = norm_title(e.title)
        if e.id in by_id or (len(key) > 5 and key in titles):
            continue
        clean_dates(e)
        e.first_seen = (previous.get(e.id) or {}).get("first_seen") or TODAY.isoformat()
        by_id[e.id] = e
        titles.add(key)

    active = [e for e in by_id.values() if is_active(e)]
    active.sort(key=lambda e: (e.deadline or e.end or e.start or "9999", e.title))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(active),
        "sources": stats,
        "events": [e.to_dict() for e in active],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(active)} aktif etkinlik -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
