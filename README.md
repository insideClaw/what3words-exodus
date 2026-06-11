# what3words Exodus

Export your saved what3words locations to GPX — no API key, no subscription, no Pro plan needed.

Free tool to migrate away from what3words. Convert w3w addresses to GPS coordinates and escape the what3words walled garden.

**Looking for:** what3words alternative, what3words export, what3words to GPS, w3w to GPX converter, what3words free coordinate lookup, what3words saved places backup, leave what3words, what3words migration tool, what3words to OsmAnd, what3words to CoMaps, what3words to Google Maps, cancel what3words pro

## Why

what3words has changed to an aggressive monetization model with severely limited saved location number and a lock-in model, locking coordinate conversion behind a paid API to further trap customers. This tool uses Playwright to visit each w3w page, clicks Navigate > Google Maps, and extracts the full-precision coordinates from the resulting URL.

Before you do this, you'll need a CSV export from what3words. Again, they have locked that in the Pro tier, but just the 7 day trial should allow you to get that and immediately cancel.

Disclaimer: 100% vibe coded

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install playwright
playwright install chromium
```

## Usage

```bash
python3 w3w-to-gpx.py input.csv output.gpx
```

### Input format

Standard what3words CSV export (Settings > Saved places > Export):

```csv
List,3 word address,Label
"Exploration",///trickle.archduke.boomed,"Some label here"
```

### Output

GPX 1.1 file with full 7-decimal-place coordinates, ready to import into:

- **CoMaps** (formerly MAPS.ME): Bookmarks > ... > Import
- **OsmAnd**: My Places > Favourites > Import
- **Google Maps**: My Maps > Import

## How it works

1. Opens each w3w address in headless Chromium
2. Dismisses cookie/consent overlays
3. Clicks the "Navigate" button
4. Reads the Google Maps link which contains `destination=lat,lon`
5. Writes all waypoints to a GPX file

~5 seconds per location. 30 locations takes ~2-3 minutes.

## Limitations

- Relies on w3w's current page structure — may break if they redesign
- Headless browser is heavier than a simple HTTP request, but it's the only way to get full precision without paying
