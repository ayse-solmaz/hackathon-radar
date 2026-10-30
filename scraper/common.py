"""Shared helpers: HTTP session, event model, type detection, date parsing."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"})


def get(url: str, **kw) -> requests.Response:
    r = session.get(url, timeout=30, **kw)
    r.raise_for_status()
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = "utf-8"
    return r


TODAY = datetime.now(timezone.utc).date()

# Order matters: the first match wins.
TYPE_PATTERNS = [
    ("datathon", r"datathon|data\s*challenge|veri\s*(bilimi\s*)?(yarışma|maraton)|kaggle"),
    ("ideathon", r"ideathon|ideaton|fikir\s*maraton|fikir\s*yarışma|girişimcilik\s*yarışma|case\s*(study\s*)?competition|vaka\s*yarışma"),
    ("hackathon", r"hack[\s-]?a?th?on|hackaton|hackathonu|buildathon|codeathon|makeathon|designathon|game\s*jam|gamejam|hack\s*day"),
    ("yarisma", r"yarışma|yarisma|challenge|competition|contest|kod\s*maratonu|teknofest"),
]

RELEVANT = re.compile("|".join(p for _, p in TYPE_PATTERNS), re.I)


def detect_type(*texts: str | None) -> str | None:
    blob = " ".join(t for t in texts if t)
    for name, pat in TYPE_PATTERNS:
        if re.search(pat, blob, re.I):
            return name
    return None


@dataclass
class Event:
    title: str
    url: str
    source: str
    type: str = "hackathon"
    organizer: str | None = None
    location: str | None = None
    online: bool | None = None
    turkey: bool = False
    start: str | None = None      # ISO date
    end: str | None = None
    deadline: str | None = None   # last day to apply
    prize: str | None = None
    image: str | None = None
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    first_seen: str | None = None

    @property
    def id(self) -> str:
        key = re.sub(r"[?#].*$", "", self.url.lower()).rstrip("/")
        return hashlib.sha1(key.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        return d


TR_HINT = re.compile(
    r"türkiye|turkiye|turkey|istanbul|İstanbul|ankara|izmir|İzmir|bursa|antalya|kocaeli|"
    r"eskişehir|konya|kayseri|trabzon|samsun|gaziantep|\.tr\b|\bTR\b",
    re.I,
)


def looks_turkish(*texts: str | None) -> bool:
    return bool(TR_HINT.search(" ".join(t for t in texts if t)))


# ---------- dates ----------

TR_MONTHS = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5,
    "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}
EN_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def iso(d: date | datetime | None) -> str | None:
    if d is None:
        return None
    if isinstance(d, datetime):
        d = d.date()
    return d.isoformat()


def parse_iso(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None


def infer_year(month: int, day: int) -> date | None:
    """Dates without a year: pick the occurrence closest to today (allowing ~2 months back)."""
    try:
        d = date(TODAY.year, month, day)
    except ValueError:
        return None
    if (TODAY - d).days > 60:
        d = d.replace(year=TODAY.year + 1)
    elif (d - TODAY).days > 300:
        d = d.replace(year=TODAY.year - 1)
    return d


def parse_tr_date(text: str | None) -> date | None:
    """'19 Ekim', '05 Aralık 2026', '06 – 07 Kasım' (returns the last day)."""
    if not text:
        return None
    t = text.lower().replace("i̇", "i")
    days_months = re.findall(r"(\d{1,2})(?:\s*[–-]\s*\d{1,2})?\s+([a-zçğıöşü]+)\s*(\d{4})?", t)
    for day, mon, year in reversed(days_months):
        m = TR_MONTHS.get(mon)
        if not m:
            continue
        # for ranges like "06 – 07 Kasım" take the second number
        rng = re.search(rf"\d{{1,2}}\s*[–-]\s*(\d{{1,2}})\s+{mon}", t)
        dd = int(rng.group(1)) if rng else int(day)
        if year:
            try:
                return date(int(year), m, dd)
            except ValueError:
                return None
        return infer_year(m, dd)
    m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", t)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def parse_en_range_end(text: str | None) -> date | None:
    """Devpost style: 'Aug 26 - Oct 30, 2026', 'Oct 01 - 15, 2026', 'Dec 01, 2026 - Jan 10, 2027'."""
    if not text:
        return None
    parts = [p.strip() for p in text.split(" - ")]
    last = parts[-1]
    year = re.search(r"(\d{4})", last)
    m = re.match(r"([A-Za-z]{3})[a-z]*\s+(\d{1,2})", last)
    if not m:  # 'Oct 01 - 15, 2026'
        first = re.match(r"([A-Za-z]{3})", parts[0])
        dd = re.match(r"(\d{1,2})", last)
        if not (first and dd):
            return None
        mon, day = first.group(1), dd.group(1)
    else:
        mon, day = m.group(1), m.group(2)
    month = EN_MONTHS.get(mon.lower())
    if not month:
        return None
    if year:
        try:
            return date(int(year.group(1)), month, int(day))
        except ValueError:
            return None
    return infer_year(month, int(day))
