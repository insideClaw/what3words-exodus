#!/usr/bin/env python3
"""
what3words CSV → GPX converter
Uses Playwright to click Navigate → Google Maps and extract full-precision
coordinates from the resulting URL.

Usage: python3 w3w-to-gpx.py input.csv output.gpx

The CSV must have columns: List, 3 word address, Label
(standard what3words export format)

Requirements: pip install playwright && playwright install chromium
"""

import csv
import sys
import re
import asyncio
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from playwright.async_api import async_playwright


GOOGLE_MAPS_PATTERN = re.compile(r'destination=([-\d.]+),([-\d.]+)')


async def dismiss_overlays(page):
    """Remove all blocking overlays via JS."""
    await page.evaluate("""
        // FundingChoices consent
        document.querySelectorAll('.fc-consent-root, .fc-dialog-overlay, [class*="consent"]').forEach(el => el.remove());
        // w3w's own modals (fixed inset-0 z-50 overlays)
        document.querySelectorAll('[data-state="open"][aria-hidden="true"], div.fixed.inset-0.z-50').forEach(el => el.remove());
        // Any radix-ui dialog overlays
        document.querySelectorAll('[data-radix-portal]').forEach(el => el.remove());
    """)
    await page.wait_for_timeout(500)


async def w3w_to_coords(page, address):
    """Navigate to w3w page, click Navigate, pick Google Maps, extract coords."""
    address = address.lstrip("/").strip()
    url = f"https://what3words.com/{address}"

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)
        await dismiss_overlays(page)

        # Click the Navigate button (data-testid="navigate-button" from the error log)
        nav_btn = page.locator('[data-testid="navigate-button"]')
        await nav_btn.wait_for(state="visible", timeout=10000)
        await nav_btn.click(force=True)
        await page.wait_for_timeout(2000)

        # Look for Google Maps link in the navigation dropdown/panel
        gmaps_link = page.locator('a[href*="google.com/maps"], a[href*="maps.google"]').first
        await gmaps_link.wait_for(state="visible", timeout=10000)
        href = await gmaps_link.get_attribute("href")

        if href:
            m = GOOGLE_MAPS_PATTERN.search(href)
            if m:
                return float(m.group(1)), float(m.group(2))

        # Fallback: check for any link with destination= pattern
        all_links = await page.locator('a[href*="destination="]').all()
        for link in all_links:
            href = await link.get_attribute("href")
            if href:
                m = GOOGLE_MAPS_PATTERN.search(href)
                if m:
                    return float(m.group(1)), float(m.group(2))

    except Exception as e:
        print(f"    Error: {e}")

    return None, None


def build_gpx(waypoints):
    gpx = Element("gpx", {
        "version": "1.1",
        "creator": "w3w_to_gpx.py",
        "xmlns": "http://www.topografix.com/GPX/1/1",
    })
    for wp in waypoints:
        wpt = SubElement(gpx, "wpt", {
            "lat": f"{wp['lat']:.7f}",
            "lon": f"{wp['lon']:.7f}",
        })
        name = SubElement(wpt, "name")
        name.text = wp["label"] or wp["address"]
        desc = SubElement(wpt, "desc")
        addr = wp['address'].lstrip("/")
        desc.text = f"w3w: ///{addr} | List: {wp['list']}"
    return gpx


async def main():
    if len(sys.argv) != 3:
        print("Usage: python3 w3w-to-gpx.py input.csv output.gpx")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_gpx = sys.argv[2]

    print(f"Reading {input_csv} ...")
    with open(input_csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"Found {len(rows)} locations. Launching browser...\n")

    waypoints = []
    skipped = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="en-GB",
        )
        page = await context.new_page()

        for i, row in enumerate(rows, 1):
            address = (
                row.get("3 word address")
                or row.get("3word address")
                or row.get("words")
                or ""
            ).strip()
            label = (row.get("Label") or row.get("label") or "").strip()
            lst = (row.get("List") or row.get("list") or "").strip()

            if not address:
                print(f"[{i}/{len(rows)}] SKIP — empty address")
                skipped += 1
                continue

            print(f"[{i}/{len(rows)}] {address}  ({label or 'no label'})", end=" ... ", flush=True)
            lat, lon = await w3w_to_coords(page, address)

            if lat is None:
                print("FAILED")
                skipped += 1
            else:
                print(f"{lat:.7f}, {lon:.7f}")
                waypoints.append({
                    "address": address,
                    "label": label,
                    "list": lst,
                    "lat": lat,
                    "lon": lon,
                })

        await browser.close()

    print(f"\nConverted {len(waypoints)} locations ({skipped} skipped).")

    if not waypoints:
        print("Nothing to write.")
        sys.exit(1)

    raw_xml = tostring(build_gpx(waypoints), encoding="unicode")
    pretty = minidom.parseString(raw_xml).toprettyxml(indent="  ")

    with open(output_gpx, "w", encoding="utf-8") as f:
        f.write(pretty)

    print(f"\nGPX saved to: {output_gpx}")
    print("Import in CoMaps: Bookmarks → ⋮ → Import")


if __name__ == "__main__":
    asyncio.run(main())
