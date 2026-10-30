"""Structured platform sources (APIs, embedded JSON, HTML cards)."""
from __future__ import annotations

import html
import json
import os
import re

from bs4 import BeautifulSoup

from .common import (
    Event, RELEVANT, TODAY, detect_type, get, iso, looks_turkish, parse_en_range_end,
    parse_iso, parse_tr_date,
)


def devpost() -> list[Event]:
    out = []
    for page in range(1, 30):
        data = get(
            "https://devpost.com/api/hackathons",
            params={"status[]": ["open", "upcoming"], "page": page},
        ).json()
        items = data.get("hackathons") or []
        if not items:
            break
        for h in items:
            loc = (h.get("displayed_location") or {}).get("location")
            prize = re.sub(r"<[^>]+>", "", h.get("prize_amount") or "") or None
            thumb = h.get("thumbnail_url") or ""
            out.append(Event(
                title=h["title"],
                url=h["url"],
                source="Devpost",
                type=detect_type(h["title"]) or "hackathon",
                organizer=h.get("organization_name"),
                location=loc,
                online=(loc or "").lower() == "online",
                turkey=looks_turkish(loc),
                deadline=iso(parse_en_range_end(h.get("submission_period_dates"))),
                prize=prize if prize not in ("$0", "0") else None,
                image=("https:" + thumb) if thumb.startswith("//") else thumb or None,
                tags=[t["name"] for t in h.get("themes", [])],
            ))
    return out


def mlh() -> list[Event]:
    out, seen = [], set()
    dec = json.JSONDecoder()
    for season in (TODAY.year, TODAY.year + 1):
        try:
            page = get(f"https://mlh.io/seasons/{season}/events").text
        except Exception:
            continue
        # Event objects are embedded as JSON (sometimes with escaped slashes).
        for m in re.finditer(r'\{"id":"[0-9a-f-]{36}","slug":', page):
            try:
                obj, _ = dec.raw_decode(page, m.start())
            except ValueError:
                continue
            if obj.get("slug") in seen or not obj.get("startsAt"):
                continue
            seen.add(obj["slug"])
            end = parse_iso(obj.get("endsAt"))
            if end and end < TODAY:
                continue
            fmt = obj.get("formatType")
            out.append(Event(
                title=obj["name"],
                url=obj.get("websiteUrl") or f"https://mlh.io/events/{obj['slug']}",
                source="MLH",
                type=detect_type(obj["name"]) or "hackathon",
                location=obj.get("location"),
                online=fmt == "digital",
                turkey=looks_turkish(obj.get("location")),
                start=iso(parse_iso(obj.get("startsAt"))),
                end=iso(end),
                image=obj.get("backgroundUrl"),
                tags=(obj.get("customFields") or {}).get("hackathon_focus") or [],
            ))
    return out


LUMA_API = "https://api.lu.ma/discover/get-paginated-events"
LUMA_QUERIES = ["hackathon", "datathon", "ideathon", "hackaton", "buildathon", "game jam"]
# Turkish cities: geo discovery returns everything nearby, so we keyword-filter.
LUMA_PLACES = [(41.01, 28.96), (39.93, 32.86), (38.42, 27.14)]


def _luma_event(entry: dict) -> Event | None:
    ev = entry.get("event") or {}
    name = ev.get("name") or ""
    desc = " ".join((entry.get("calendar") or {}).get("name", "").split())
    kind = detect_type(name)
    if not kind:
        return None
    geo = ev.get("geo_address_info") or {}
    loc = geo.get("city_state") or geo.get("address")
    online = ev.get("location_type") in ("online", "zoom")
    hosts = [h.get("name") for h in entry.get("hosts") or [] if h.get("name")]
    return Event(
        title=name,
        url=f"https://luma.com/{ev.get('url')}",
        source="Luma",
        type=kind,
        organizer=(entry.get("calendar") or {}).get("name") or (hosts[0] if hosts else None),
        location="Online" if online and not loc else loc,
        online=online,
        turkey=geo.get("country_code") == "TR" or looks_turkish(loc, name),
        start=iso(parse_iso(ev.get("start_at"))),
        end=iso(parse_iso(ev.get("end_at"))),
        image=ev.get("cover_url"),
        summary=desc or None,
    )


def luma() -> list[Event]:
    out = []
    reqs = [{"query": q, "pagination_limit": 50} for q in LUMA_QUERIES]
    reqs += [{"latitude": lat, "longitude": lon, "pagination_limit": 50} for lat, lon in LUMA_PLACES]
    for params in reqs:
        try:
            data = get(LUMA_API, params=params).json()
        except Exception as e:
            print(f"  luma {params}: {e}")
            continue
        for entry in data.get("entries", []):
            ev = _luma_event(entry)
            if ev:
                out.append(ev)
    return out


def coderspace() -> list[Event]:
    out = []
    page = get("https://coderspace.io/etkinlikler").text
    for raw in re.findall(r'<script[^>]*ld\+json[^>]*>(.*?)</script>', page, re.S):
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        if d.get("@type") != "Event":
            continue
        name, desc = d.get("name", ""), d.get("description", "")
        kind = detect_type(name, desc)
        if not kind:
            continue
        loc = d.get("location") or {}
        online = "Online" in d.get("eventAttendanceMode", "")
        img = d.get("image")
        out.append(Event(
            title=html.unescape(name),
            url=loc.get("url") or d.get("url") or "https://coderspace.io/etkinlikler",
            source="Coderspace",
            type=kind,
            organizer="Coderspace",
            location="Online" if online else (loc.get("name") or "Türkiye"),
            online=online,
            turkey=True,
            start=iso(parse_iso(d.get("startDate"))),
            end=iso(parse_iso(d.get("endDate"))),
            image=img[0] if isinstance(img, list) and img else img,
            summary=html.unescape(desc) or None,
        ))
    return out


def techcareer() -> list[Event]:
    out = []
    for slug in ("hackathon", "datathon", "ideathon", "bootcamp-yarisma", "yarisma"):
        try:
            page = get(f"https://www.techcareer.net/{slug}").text
        except Exception:
            continue
        m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
        if not m:
            continue
        props = json.loads(m.group(1)).get("props", {}).get("pageProps", {})
        for key in ("openEvents", "alternativeEvents"):
            for item in (props.get(key) or {}).get("data", []) or []:
                a = item.get("attributes") or {}
                if a.get("isCompleted"):
                    continue
                kind = detect_type(a.get("title"), a.get("eventType"))
                if not kind:
                    continue
                type_slug = a.get("eventTypeSlug") or slug
                out.append(Event(
                    title=a.get("title"),
                    url=a.get("externalLink") or f"https://www.techcareer.net/{type_slug}/{a.get('slug')}",
                    source="Techcareer",
                    type=kind,
                    organizer="Techcareer.net",
                    location="Türkiye",
                    turkey=True,
                    deadline=a.get("deadline"),
                    prize=a.get("prize"),
                    image=a.get("image"),
                    summary=a.get("subTitle"),
                ))
    return out


def youthall() -> list[Event]:
    out = []
    soup = BeautifulSoup(get("https://www.youthall.com/tr/events/").text, "html.parser")
    for card in soup.select("article.events-card"):
        a = card.select_one("a.events-card__link")
        img = card.select_one("img.events-card__img")
        title = img.get("alt") if img else (card.get_text(" ", strip=True)[:80])
        text = card.get_text(" ", strip=True)
        kind = detect_type(title, text)
        if not (a and kind):
            continue
        when = card.select_one(".events-card__when .events-card__val")
        dl = card.select_one(".events-card__deadline-val")
        org = card.select_one(".events-card__org-name")
        out.append(Event(
            title=title,
            url="https://www.youthall.com" + a["href"] if a["href"].startswith("/") else a["href"],
            source="Youthall",
            type=kind,
            organizer=org.get_text(strip=True) if org else None,
            location="Türkiye",
            online="online" in text.lower(),
            turkey=True,
            end=iso(parse_tr_date(when.get_text(" ", strip=True) if when else None)),
            deadline=iso(parse_tr_date(dl.get_text(strip=True) if dl else None)),
            image=img.get("src") if img else None,
        ))
    return out


def anbean() -> list[Event]:
    out = []
    soup = BeautifulSoup(get("https://www.anbeankampus.co/etkinlikler").text, "html.parser")
    for card in soup.select("div.mini-eventCard"):
        a = card.find("a", href=True)
        h6 = card.find("h6")
        if not (a and h6):
            continue
        title = h6.get_text(strip=True)
        typ = card.select_one(".mini-eventCard-headerType")
        typ_text = typ.get_text(" ", strip=True) if typ else ""
        kind = detect_type(title, typ_text)
        if not kind:
            continue
        dates = {}
        for item in card.select(".mini-eventCard-dateItem"):
            spans = [s.get_text(strip=True) for s in item.find_all("span")]
            if len(spans) >= 2:
                dates[spans[0]] = spans[1]
        img = card.select_one("img.mini-eventCard-HeaderImage")
        desc = card.select_one(".mini-eventCard-titleDescription p")
        href = a["href"]
        out.append(Event(
            title=title,
            url="https://www.anbeankampus.co" + href if href.startswith("/") else href,
            source="Anbean Kampüs",
            type=kind,
            location="Türkiye",
            turkey=True,
            start=iso(parse_tr_date(dates.get("Başlangıç Tarihi"))),
            end=iso(parse_tr_date(dates.get("Bitiş Tarihi"))),
            deadline=iso(parse_tr_date(dates.get("Son Başvuru"))),
            image=img.get("src") if img else None,
            summary=desc.get_text(strip=True) if desc else None,
        ))
    return out


def kaggle() -> list[Event]:
    """Optional: needs KAGGLE_USERNAME / KAGGLE_KEY secrets."""
    user, key = os.getenv("KAGGLE_USERNAME"), os.getenv("KAGGLE_KEY")
    if not (user and key):
        return []
    out = []
    data = get(
        "https://www.kaggle.com/api/v1/competitions/list",
        params={"sortBy": "latestDeadline", "page": 1},
        auth=(user, key),
    ).json()
    for c in data:
        ref = c.get("ref") or ""
        out.append(Event(
            title=c.get("title"),
            url=ref if ref.startswith("http") else f"https://www.kaggle.com/competitions/{ref}",
            source="Kaggle",
            type="datathon",
            organizer=c.get("organizationName") or "Kaggle",
            location="Online",
            online=True,
            deadline=iso(parse_iso(c.get("deadline"))),
            prize=c.get("reward"),
            summary=c.get("description"),
            tags=[t.get("name") for t in c.get("tags") or [] if t.get("name")],
        ))
    return out


ALL = {
    "Devpost": devpost,
    "MLH": mlh,
    "Luma": luma,
    "Coderspace": coderspace,
    "Techcareer": techcareer,
    "Youthall": youthall,
    "Anbean Kampüs": anbean,
    "Kaggle": kaggle,
}

__all__ = ["ALL", "RELEVANT"]
