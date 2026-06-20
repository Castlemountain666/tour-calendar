#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
import yaml
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

ROOT = Path(__file__).resolve().parents[1]
ARTISTS_FILE = ROOT / "data" / "artists.yml"
MANUAL_EVENTS_FILE = ROOT / "data" / "manual_events.yml"
ICS_FILE = ROOT / "calendar.ics"
EVENTS_JSON = ROOT / "events.json"
INDEX_HTML = ROOT / "index.html"
LAST_UPDATE = ROOT / "data" / "last_update.json"

USER_AGENT = "Mozilla/5.0 (compatible; TourCalendarBot/1.0; +https://github.com/)"

@dataclass(frozen=True)
class Event:
    artist: str
    date: str
    city: str
    country: str
    venue: str
    url: str
    note: str = ""
    source_type: str = "manual"

    @property
    def sort_key(self):
        return (self.date, self.artist.lower(), self.city.lower(), self.venue.lower())

def load_yaml(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or default

def norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()

def parse_date(value: Any) -> str | None:
    if not value:
        return None
    try:
        dt = dateparser.parse(str(value))
        return dt.date().isoformat() if dt else None
    except Exception:
        return None

def active_artists() -> list[dict[str, Any]]:
    rows = load_yaml(ARTISTS_FILE, [])
    return [r for r in rows if r and r.get("enabled", True)]

def is_event_object(obj: dict[str, Any]) -> bool:
    typ = obj.get("@type") or obj.get("type")
    vals = typ if isinstance(typ, list) else [typ]
    return any(str(v).lower() in {"event", "musicevent", "festival"} for v in vals)

def walk_jsonld(obj: Any) -> Iterable[dict[str, Any]]:
    if isinstance(obj, dict):
        if is_event_object(obj):
            yield obj
        for key in ("@graph", "graph", "events", "itemListElement", "mainEntity", "subEvent"):
            if key in obj:
                yield from walk_jsonld(obj[key])
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_jsonld(item)

def decode_jsonld(text: str) -> Any | None:
    text = (text or "").strip()
    if not text:
        return None
    for candidate in (text, html.unescape(text)):
        try:
            return json.loads(candidate)
        except Exception:
            pass
    return None

def location_parts(location: Any) -> tuple[str, str, str]:
    venue = city = country = ""
    if isinstance(location, str):
        return norm(location), "", ""
    if isinstance(location, dict):
        venue = norm(location.get("name"))
        address = location.get("address")
        if isinstance(address, str):
            city = norm(address)
        elif isinstance(address, dict):
            city = norm(address.get("addressLocality") or address.get("addressRegion") or address.get("streetAddress"))
            c = address.get("addressCountry")
            country = norm(c.get("name") if isinstance(c, dict) else c)
    return venue, city, country

def fetch_html(url: str) -> str | None:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=25)
        r.raise_for_status()
        return r.text
    except Exception as exc:
        print(f"WARN: could not fetch {url}: {exc}")
        return None

def extract_jsonld_events(url: str, artist_name: str) -> list[Event]:
    raw = fetch_html(url)
    if not raw:
        return []
    soup = BeautifulSoup(raw, "html.parser")
    out: list[Event] = []
    for tag in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        data = decode_jsonld(tag.get_text() or "")
        if data is None:
            continue
        for obj in walk_jsonld(data):
            d = parse_date(obj.get("startDate"))
            if not d or d < date.today().isoformat():
                continue
            venue, city, country = location_parts(obj.get("location"))
            title = norm(obj.get("name")) or artist_name
            event_url = norm(obj.get("url")) or url
            out.append(Event(
                artist=artist_name,
                date=d,
                city=city,
                country=country,
                venue=venue or title,
                url=event_url,
                note=f"Automaattisesti luettu lähdesivulta. Title: {title}",
                source_type="auto-jsonld",
            ))
    return out

def manual_events(enabled_names: set[str]) -> list[Event]:
    rows = load_yaml(MANUAL_EVENTS_FILE, [])
    out: list[Event] = []
    for row in rows:
        if not row:
            continue
        artist = norm(row.get("artist"))
        if artist not in enabled_names:
            continue
        d = parse_date(row.get("date"))
        if not d or d < date.today().isoformat():
            continue
        out.append(Event(
            artist=artist,
            date=d,
            city=norm(row.get("city")),
            country=norm(row.get("country")),
            venue=norm(row.get("venue")),
            url=norm(row.get("url")),
            note=norm(row.get("note")),
            source_type="manual",
        ))
    return out

def collect_events() -> list[Event]:
    artists = active_artists()
    names = {norm(a.get("name")) for a in artists}
    all_events: list[Event] = []
    for artist in artists:
        name = norm(artist.get("name"))
        for url in artist.get("sources", []) or []:
            print(f"Fetching {name}: {url}")
            all_events.extend(extract_jsonld_events(url, name))
    all_events.extend(manual_events(names))
    by_key: dict[str, Event] = {}
    for ev in all_events:
        key = "|".join([ev.artist.lower(), ev.date, ev.venue.lower(), ev.city.lower()])
        old = by_key.get(key)
        if old is None or (old.source_type == "manual" and ev.source_type != "manual"):
            by_key[key] = ev
    return sorted(by_key.values(), key=lambda e: e.sort_key)

def ics_escape(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")

def fold_ics_line(line: str) -> str:
    if len(line) <= 73:
        return line
    parts = []
    while len(line) > 73:
        parts.append(line[:73])
        line = " " + line[73:]
    parts.append(line)
    return "\r\n".join(parts)

def event_uid(ev: Event) -> str:
    raw = f"{ev.artist}|{ev.date}|{ev.venue}|{ev.city}|{ev.country}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest() + "@tour-calendar"

def write_ics(events: list[Event]) -> None:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Tour Calendar//GitHub Pages//FI",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Kiertuekalenteri",
        "X-WR-CALDESC:Päivittyvä bändi- ja tapahtumakalenteri", "X-WR-TIMEZONE:Europe/Helsinki",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D",
    ]
    for ev in events:
        start = datetime.fromisoformat(ev.date).date()
        end = start + timedelta(days=1)
        summary = f"{ev.artist} – {ev.venue}"
        location = ", ".join([x for x in [ev.venue, ev.city, ev.country] if x])
        desc = f"{ev.artist} tour/event date. Source: {ev.url}. {ev.note}. Source type: {ev.source_type}"
        lines.extend([
            "BEGIN:VEVENT", f"UID:{event_uid(ev)}", f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}", f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
            f"SUMMARY:{ics_escape(summary)}", f"LOCATION:{ics_escape(location)}", f"DESCRIPTION:{ics_escape(desc)}",
            f"URL:{ev.url}", "TRANSP:TRANSPARENT", "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    ICS_FILE.write_text("\r\n".join(fold_ics_line(l) for l in lines) + "\r\n", encoding="utf-8")

def write_outputs(events: list[Event]) -> None:
    EVENTS_JSON.write_text(json.dumps([asdict(e) for e in events], ensure_ascii=False, indent=2), encoding="utf-8")
    updated = datetime.now(timezone.utc).isoformat()
    rows = "".join(
        "<tr>" +
        f"<td>{html.escape(e.date)}</td><td>{html.escape(e.artist)}</td><td>{html.escape(e.venue)}</td>" +
        f"<td>{html.escape(e.city)}</td><td>{html.escape(e.country)}</td><td>{html.escape(e.source_type)}</td>" +
        f"<td><a href='{html.escape(e.url)}'>source</a></td>" +
        "</tr>" for e in events[:500]
    )
    INDEX_HTML.write_text(f"""<!doctype html><html lang='fi'><head><meta charset='utf-8'><title>Kiertuekalenteri</title><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:2rem;line-height:1.45}}code{{background:#f2f2f2;padding:.15rem .3rem;border-radius:.25rem}}table{{border-collapse:collapse;width:100%;margin-top:1rem}}th,td{{border-bottom:1px solid #ddd;text-align:left;padding:.45rem;vertical-align:top}}th{{background:#f7f7f7}}</style></head><body><h1>Kiertuekalenteri</h1><p>Päivitetty: <code>{html.escape(updated)}</code></p><p>Tilaa kalenteri tästä: <a href='calendar.ics'><code>calendar.ics</code></a></p><p>Kalenterissa tapahtumia: <strong>{len(events)}</strong></p><table><thead><tr><th>Päivä</th><th>Artisti</th><th>Paikka</th><th>Kaupunki</th><th>Maa</th><th>Tyyppi</th><th>Lähde</th></tr></thead><tbody>{rows}</tbody></table></body></html>""", encoding="utf-8")
    LAST_UPDATE.write_text(json.dumps({
        "updated_at_utc": updated,
        "event_count": len(events),
        "auto_event_count": sum(1 for e in events if e.source_type != "manual"),
        "manual_event_count": sum(1 for e in events if e.source_type == "manual"),
        "artists": sorted({e.artist for e in events}),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

def main() -> None:
    events = collect_events()
    write_ics(events)
    write_outputs(events)
    print(f"Done. Events: {len(events)}")
    print(f"Auto events: {sum(1 for e in events if e.source_type != 'manual')}")
    print(f"Manual events: {sum(1 for e in events if e.source_type == 'manual')}")

if __name__ == "__main__":
    main()
