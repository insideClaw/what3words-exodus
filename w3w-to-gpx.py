#!/usr/bin/env python3
"""
what3words CSV → GPX converter (no API key needed)
Scrapes coordinates from the public w3w short-link pages.

Usage: python3 w3w_to_gpx.py input.csv output.gpx

The CSV must have columns: List, 3 word address, Label
(standard what3words export format)
"""

import csv
import sys
import re
import time
import urllib.request
import urllib.error
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.5",
}

# Patterns to find lat/lng in the page HTML
# w3w embeds coords in og:image meta tags and JSON-LD
PATTERNS = [
    re.compile(r'center=([-\d.]+),([-\d.]+)'),
    re.compile(r'"latitude"\s*:\s*([-\d.]+)\s*,\s*"longitude"\s*:\s*([-\d.]+)'),
    re.compile(r'"lat"\s*:\s*([-\d.]+)\s*,\s*"lng"\s*:\s*([-\d.]+)'),
    re.compile(r'"coordinates"\s*:\s*\{\s*"lat"\s*:\s*([-\d.]+)\s*,\s*"lng"\s*:\s*([-\d.]+)'),
]

def w3w_to_coords(address):
    """Fetch coordinates for a w3w address by scraping the public page."""
    address = address.lstrip("/").strip()
    url = f"https://w3w.co/{address}"

    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            final_url = resp.geturl()
            html = resp.read().decode("utf-8", errors="ignore")

    # Many modern w3w pages redirect to a URL containing @lat,lon
    m = re.search(r'@([-\d.]+),([-\d.]+)', final_url)
    if m:
        return float(m.group(1)), float(m.group(2))
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code} for '{address}'")
        return None, None
    except Exception as e:
        print(f"    Request failed for '{address}': {e}")
        return None, None

    for pat in PATTERNS:
        m = pat.search(html)
        if m:
            try:
                return float(m.group(1)), float(m.group(2))
            except ValueError:
                continue

    # Last resort: dump a snippet so the user can see what's there
    print(f"    Could not parse coordinates for '{address}' — page snippet:")
    snippet = html[html.find("<head"):html.find("<head") + 2000] if "<head" in html else html[:2000]
    print(f"    {snippet[:300]}")
    return None, None


def build_gpx(waypoints):
    gpx = Element("gpx", {
        "version": "1.1",
        "creator": "w3w_to_gpx.py",
        "xmlns": "http://www.topografix.com/GPX/1/1",
    })
    for wp in waypoints:
        wpt = SubElement(gpx, "wpt", {
            "lat": str(wp["lat"]),
            "lon": str(wp["lon"]),
        })
        name = SubElement(wpt, "name")
        name.text = wp["label"] or wp["address"]
        desc = SubElement(wpt, "desc")
        desc.text = f"w3w: ///{wp['address']} | List: {wp['list']}"
    return gpx


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 w3w_to_gpx.py input.csv output.gpx")
        sys.exit(1)

    input_csv  = sys.argv[1]
    output_gpx = sys.argv[2]

    print(f"Reading {input_csv} ...")
    with open(input_csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"Found {len(rows)} locations. Fetching coordinates...\n")

    waypoints = []
    skipped   = 0

    for i, row in enumerate(rows, 1):
        address = (
            row.get("3 word address")
            or row.get("3word address")
            or row.get("words")
            or ""
        ).strip()
        label = (row.get("Label") or row.get("label") or "").strip()
        lst   = (row.get("List")  or row.get("list")  or "").strip()

        if not address:
            print(f"[{i}/{len(rows)}] SKIP — empty address")
            skipped += 1
            continue

        print(f"[{i}/{len(rows)}] {address}  ({label or 'no label'})", end=" ... ", flush=True)
        lat, lon = w3w_to_coords(address)

        if lat is None:
            print("SKIP")
            skipped += 1
        else:
            print(f"{lat}, {lon}")
            waypoints.append({
                "address": address,
                "label":   label,
                "list":    lst,
                "lat":     lat,
                "lon":     lon,
            })

        # Polite delay — avoid hammering their servers
        if i < len(rows):
            time.sleep(2)

    print(f"\nConverted {len(waypoints)} locations ({skipped} skipped).")

    if not waypoints:
        print("Nothing to write.")
        sys.exit(1)

    raw_xml = tostring(build_gpx(waypoints), encoding="unicode")
    pretty  = minidom.parseString(raw_xml).toprettyxml(indent="  ")

    with open(output_gpx, "w", encoding="utf-8") as f:
        f.write(pretty)

    print(f"\nGPX saved to: {output_gpx}")
    print("Import in CoMaps: Bookmarks → ⋮ → Import")


if __name__ == "__main__":
    main()
