#!/usr/bin/env python3
"""
Generate data/artists.yml from data/bands.txt.

This lets you manage the calendar by editing only data/bands.txt:
one band name per line.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus
import yaml

ROOT = Path(__file__).resolve().parents[1]
BANDS_FILE = ROOT / "data" / "bands.txt"
OVERRIDES_FILE = ROOT / "data" / "source_overrides.yml"
ARTISTS_FILE = ROOT / "data" / "artists.yml"

BUILT_IN_SOURCES = {
    "foo fighters": ["https://foofighters.com/tour-dates/"],
    "def leppard": ["https://defleppard.com/tour/"],
    "jack white": [
        "https://jackwhiteiii.com/tour-dates/",
        "https://www.livenation.com/artist/K8vZ917us6V/jack-white-events",
    ],
}


def clean(line: str) -> str:
    line = line.strip()
    if " #" in line:
        line = line.split(" #", 1)[0].strip()
    if "|" in line:
        line = line.split("|", 1)[0].strip()
    return line


def key(name: str) -> str:
    return " ".join(name.lower().split())


def read_bands() -> list[str]:
    if not BANDS_FILE.exists():
        raise FileNotFoundError("data/bands.txt puuttuu")

    bands: list[str] = []
    seen: set[str] = set()
    for raw in BANDS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name = clean(line)
        if not name:
            continue
        k = key(name)
        if k not in seen:
            bands.append(name)
            seen.add(k)
    return bands


def read_overrides() -> dict[str, list[str]]:
    if not OVERRIDES_FILE.exists():
        return {}
    raw = yaml.safe_load(OVERRIDES_FILE.read_text(encoding="utf-8")) or {}
    out: dict[str, list[str]] = {}
    for artist, urls in raw.items():
        if isinstance(urls, str):
            urls = [urls]
        if isinstance(urls, list):
            out[key(str(artist))] = [str(u).strip() for u in urls if str(u).strip()]
    return out


def sources_for(name: str, overrides: dict[str, list[str]]) -> list[str]:
    k = key(name)
    urls: list[str] = []
    urls += overrides.get(k, [])
    urls += BUILT_IN_SOURCES.get(k, [])

    # Best-effort fallback for new band names. This may not always parse,
    # but it gives the updater something to try before you add official URLs.
    urls.append(f"https://www.bandsintown.com/a/{quote_plus(name)}")

    seen: set[str] = set()
    deduped: list[str] = []
    for url in urls:
        if url not in seen:
            deduped.append(url)
            seen.add(url)
    return deduped


def main() -> None:
    bands = read_bands()
    overrides = read_overrides()
    artists = []
    for name in bands:
        artists.append({
            "name": name,
            "enabled": True,
            "sources": sources_for(name, overrides),
        })

    ARTISTS_FILE.write_text(
        yaml.safe_dump(artists, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"Generated {ARTISTS_FILE} with {len(artists)} artists")


if __name__ == "__main__":
    main()
