"""
Free geocoding via OpenStreetMap's Nominatim service - no API key needed.
Used to turn a lead's typed address into coordinates so clinics can be
sorted by distance. Respects Nominatim's usage policy: a real User-Agent
identifying the app, and at most ~1 request/second (fine for this prototype's
low volume - each search is a single on-demand lookup, not batch geocoding).
"""

import json
import math
import urllib.parse
import urllib.request

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "trexo-clinic-trial-prototype/1.0 (internal sales tool)"


def geocode_address(address):
    """Returns (lat, lon) for a free-text address, or None if it can't be found."""
    if not address or not address.strip():
        return None

    params = {"q": address, "format": "json", "limit": 1}
    url = f"{NOMINATIM_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            results = json.loads(resp.read())
    except Exception:  # noqa: BLE001 - any network/parsing failure just means "not found"
        return None

    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in kilometers."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
