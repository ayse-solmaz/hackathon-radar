"""Social media, university and community announcements via web search.

Instagram, TikTok, X and LinkedIn block scraping, so we use a search API
(Serper.dev = Google results) with site: queries limited to the last month.
If ANTHROPIC_API_KEY is set, Claude reads each snippet and decides whether it
really announces an open competition and extracts title/deadline/organizer.
Without it a keyword + date heuristic is used.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .common import Event, RELEVANT, TODAY, detect_type, iso, looks_turkish, parse_iso, parse_tr_date, session

KW = '(hackathon OR datathon OR ideathon OR "fikir maratonu" OR hackaton)'

# (label shown on the site, query)
QUERIES = [
    ("LinkedIn", f"site:linkedin.com/posts {KW} başvuru"),
    ("LinkedIn", f"site:linkedin.com/events {KW}"),
    ("Instagram", f"site:instagram.com {KW} başvuru"),
    ("X", f"(site:x.com OR site:twitter.com) {KW} başvuru"),
    ("TikTok", f"site:tiktok.com {KW}"),
    ("Üniversite", f"site:edu.tr {KW} başvuru"),
    ("Üniversite", f'site:edu.tr ("yarışma" OR "challenge") başvuru son tarih yazılım'),
    ("Topluluk", f"(site:kommunity.com OR site:gdg.community.dev OR site:eventbrite.com) {KW} türkiye"),
    ("Topluluk", f"(site:patika.dev OR site:globalaihub.com OR site:btkakademi.gov.tr OR site:kariyer.net) {KW}"),
    ("Topluluk", f"(site:teknofest.org OR site:tubitak.gov.tr) yarışma başvuru"),
    ("Topluluk", f"(site:medium.com OR site:dev.to) {KW} türkiye başvuru"),
    ("Web", f"{KW} başvurular başladı {TODAY.year}"),
    ("Web", f"{KW} son başvuru tarihi"),
    ("Web", f"{KW} türkiye ödül başvuru"),
]

CACHE = Path(__file__).resolve().parent.parent / "data" / "llm_cache.json"


def serper(query: str, key: str) -> list[dict]:
    r = session.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": key, "Content-Type": "application/json"},
        json={"q": query, "gl": "tr", "hl": "tr", "num": 20, "tbs": "qdr:m"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("organic", [])


# ---------- Claude extraction ----------

class Item(BaseModel):
    index: int
    is_open_competition: bool
    title: str
    type: Literal["hackathon", "ideathon", "datathon", "yarisma"]
    organizer: str | None
    deadline: str | None
    event_date: str | None
    location: str | None
    online: bool | None
    turkey: bool


class Batch(BaseModel):
    items: list[Item]


PROMPT = """Aşağıda web aramasından gelen sonuçlar var (LinkedIn/Instagram/X/TikTok gönderileri, üniversite ve topluluk sayfaları).
Bugünün tarihi: {today}.

Her sonuç için karar ver:
- is_open_competition: Bu sonuç belirli bir hackathon, ideathon, datathon veya yazılım/teknoloji/girişimcilik yarışmasının duyurusu mu VE başvurusu hâlâ açık ya da etkinlik henüz gerçekleşmemiş mi? Kazanan duyuruları, "katıldık/kazandık" paylaşımları, genel bloglar, iş ilanları, listeler veya tarihi geçmiş etkinlikler için false.
- title: etkinliğin kısa resmi adı (gönderi metni değil).
- type: hackathon | ideathon | datathon | yarisma
- organizer: düzenleyen kurum/kulüp/şirket, bilinmiyorsa null.
- deadline: son başvuru tarihi YYYY-MM-DD, yoksa null. event_date: etkinlik tarihi YYYY-MM-DD, yoksa null. Yıl yazmıyorsa bugüne en yakın gelecek tarihi seç.
- location: şehir veya "Online", bilinmiyorsa null. online: true/false/null. turkey: Türkiye'de ya da Türkiye'den katılıma açık Türkçe duyuru ise true.

Sonuçlar:
{items}"""


def classify_with_claude(results: list[dict]) -> dict[str, dict]:
    import anthropic

    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    todo = [r for r in results if r["link"] not in cache]
    client = anthropic.Anthropic()
    model = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")

    for i in range(0, len(todo), 15):
        chunk = todo[i:i + 15]
        listing = "\n\n".join(
            f"[{n}] {r.get('title', '')}\nURL: {r['link']}\nTarih: {r.get('date', '-')}\n{r.get('snippet', '')}"
            for n, r in enumerate(chunk)
        )
        try:
            resp = client.messages.parse(
                model=model,
                max_tokens=16000,
                output_config={"effort": "low"},
                messages=[{"role": "user", "content": PROMPT.format(today=TODAY.isoformat(), items=listing)}],
                output_format=Batch,
            )
        except anthropic.APIStatusError as e:
            print(f"  claude error {e.status_code}: {e.message}")
            continue
        except anthropic.APIConnectionError as e:
            print(f"  claude connection error: {e}")
            continue
        if resp.stop_reason == "refusal" or resp.parsed_output is None:
            continue
        for item in resp.parsed_output.items:
            if 0 <= item.index < len(chunk):
                cache[chunk[item.index]["link"]] = item.model_dump() | {"checked": TODAY.isoformat()}

    # forget entries older than 60 days so the cache stays small
    cache = {k: v for k, v in cache.items()
             if (TODAY - (parse_iso(v.get("checked")) or TODAY)).days < 60}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return cache


# ---------- heuristic fallback ----------

DEAD = re.compile(r"kazanan|birinci olduk|kazandık|tamamlandı|sona erdi|winners|we won|congratulations|tebrik", re.I)


def heuristic(r: dict) -> dict | None:
    text = f"{r.get('title', '')} {r.get('snippet', '')}"
    kind = detect_type(text)
    if not kind or DEAD.search(text):
        return None
    dl = None
    m = re.search(r"(son başvuru|deadline|başvuru(lar)?\s*(için)?\s*son)[^.]{0,40}", text, re.I)
    if m:
        dl = parse_tr_date(m.group(0))
    title = re.split(r"\s[|\-–]\s|on Instagram|on LinkedIn|on X:|on TikTok", r.get("title", ""))[0].strip()
    return {
        "is_open_competition": True, "title": title or r.get("title"), "type": kind,
        "organizer": None, "deadline": iso(dl), "event_date": None,
        "location": None, "online": None, "turkey": looks_turkish(text) or ".tr" in r["link"],
    }


CLAUDE_FILE = CACHE.parent / "claude_found.json"
SOCIAL = ("LinkedIn", "Instagram", "X", "TikTok")
TYPES = ("hackathon", "ideathon", "datathon", "yarisma")


def from_claude_code() -> list[Event]:
    """Results written by the Claude Code GitHub Action step (subscription, no API key)."""
    if not CLAUDE_FILE.exists():
        print("  data/claude_found.json yok (Claude Code adımı çalışmadı)")
        return []
    try:
        raw = json.loads(CLAUDE_FILE.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"  claude_found.json okunamadı: {e}")
        return []
    items = raw.get("events", []) if isinstance(raw, dict) else raw
    out = []
    for d in items:
        if not isinstance(d, dict) or not d.get("title") or not str(d.get("url", "")).startswith("http"):
            continue
        platform = d.get("platform") or "Web"
        kind = d.get("type") if d.get("type") in TYPES else (detect_type(d["title"], d.get("summary")) or "yarisma")
        out.append(Event(
            title=d["title"],
            url=d["url"],
            source=platform,
            type=kind,
            organizer=d.get("organizer"),
            location=d.get("location"),
            online=d.get("online"),
            turkey=bool(d.get("turkey")),
            start=d.get("event_date"),
            deadline=d.get("deadline"),
            summary=d.get("summary"),
            tags=["sosyal"] if platform in SOCIAL else [],
        ))
    return out


def collect() -> list[Event]:
    key = os.getenv("SERPER_API_KEY")
    if not key:
        print("  SERPER_API_KEY yok, Serper araması atlandı")
        return []

    results: dict[str, dict] = {}
    for label, q in QUERIES:
        try:
            for r in serper(q, key):
                if r.get("link") and RELEVANT.search(f"{r.get('title', '')} {r.get('snippet', '')}"):
                    results.setdefault(r["link"], r | {"label": label})
        except Exception as e:
            print(f"  search failed ({label}): {e}")
    print(f"  {len(results)} arama sonucu")

    use_llm = bool(os.getenv("ANTHROPIC_API_KEY"))
    info = classify_with_claude(list(results.values())) if use_llm else {}

    out = []
    for link, r in results.items():
        d = info.get(link) if use_llm else heuristic(r)
        if not d or not d.get("is_open_competition"):
            continue
        out.append(Event(
            title=d["title"],
            url=link,
            source=r["label"],
            type=d["type"],
            organizer=d.get("organizer"),
            location=d.get("location"),
            online=d.get("online"),
            turkey=bool(d.get("turkey")),
            start=d.get("event_date"),
            deadline=d.get("deadline"),
            summary=(r.get("snippet") or "")[:280] or None,
            image=r.get("imageUrl"),
            tags=["sosyal"] if r["label"] in SOCIAL else [],
        ))
    return out
