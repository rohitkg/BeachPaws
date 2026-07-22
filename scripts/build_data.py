#!/usr/bin/env python3
"""Build data/beaches.json from the EA Bathing Water API + curated dog rules.

- Reads data/config.json for the country to fetch (URI selector, e.g. England).
- Reads data/dog_rules.json (curated, never written by this script).
- Writes data/beaches.json only after every fetch succeeds.

Stdlib only; Python 3.9+.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://environment.data.gov.uk/doc"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TIMEOUT = 15
DELAY = 0.2
PAGE_SIZE = 50

ATTRIBUTION = (
    "Beach locations, sediment types and water quality from the Environment Agency "
    "Bathing Water Quality API (environment.data.gov.uk/bwq), "
    "Open Government Licence v3.0. Dog restrictions hand-curated from council PSPO "
    "pages; see per-beach source and accessed date."
)


def warn(msg):
    print(f"WARN: {msg}", file=sys.stderr)


def as_list(x):
    """The linked-data API returns a bare object where a list has one item."""
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def get_json(url):
    """GET url with one retry."""
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt == 2:
                raise SystemExit(f"ERROR: failed to fetch {url}: {e}")
            warn(f"retrying {url}: {e}")
            time.sleep(1)


def lang_value(x):
    """Extract _value from a langString object (possibly a single-item list)."""
    items = as_list(x)
    if not items:
        return None
    v = items[0]
    return v.get("_value") if isinstance(v, dict) else v


def fetch_all_beach_ids(country_uri):
    """Return every bathing-water id for the given country, following pagination."""
    ids = []
    page = 0
    while True:
        query = urllib.parse.urlencode(
            {"country": country_uri, "_pageSize": PAGE_SIZE, "_page": page}
        )
        doc = get_json(f"{BASE}/bathing-water.json?{query}")
        items = doc["result"].get("items", [])
        for item in items:
            ids.append(item["_about"].rsplit("/", 1)[-1])
        if len(items) < PAGE_SIZE:
            return ids
        page += 1


def geo_label(node):
    """Extract a place name from a district/regionalOrganization-shaped node —
    a bare {name: langString} object, or (district's case) a list containing
    that object plus bare URI strings."""
    for item in as_list(node):
        if isinstance(item, dict) and "name" in item:
            return lang_value(item["name"])
    return None


def fetch_beach(beach_id, county_map):
    """Fetch one beach record and flatten it."""
    doc = get_json(f"{BASE}/bathing-water/{beach_id}.json")
    topic = doc["result"]["primaryTopic"]

    name = lang_value(topic.get("name"))
    if not name:
        warn(f"{beach_id}: no name in EA record")
        name = beach_id

    district = geo_label(topic.get("district"))
    if not district:
        warn(f'{beach_id} "{name}": no district in EA record')

    county = county_map.get(district)
    if district and not county:
        warn(f'{beach_id} "{name}": no county mapping for district "{district}"')

    region = geo_label(topic.get("regionalOrganization"))
    if not region:
        warn(f'{beach_id} "{name}": no regionalOrganization in EA record')

    sediments = sorted(
        uri.rsplit("/", 1)[-1].replace("-sediment", "")
        for uri in as_list(topic.get("sedimentTypesPresent"))
    )
    if not sediments:
        warn(f'{beach_id} "{name}": no sediment data')

    sampling = topic.get("samplingPoint") or {}
    lat = sampling.get("lat")
    lng = sampling.get("long")
    if isinstance(lat, list):  # defensive: multiple sampling points
        lat, lng = lat[0], lng[0]
    if lat is None or lng is None:
        warn(f'{beach_id} "{name}": missing coordinates')
        lat = lng = None

    quality = None
    assessment = as_list(topic.get("latestComplianceAssessment"))
    if assessment:
        assessment = assessment[0]
        cls = lang_value(assessment.get("complianceClassification", {}).get("name"))
        year_match = re.search(r"/year/(\d{4})", assessment.get("_about", ""))
        if cls:
            quality = {
                "class": cls,
                "year": int(year_match.group(1)) if year_match else None,
            }
    if quality is None:
        warn(f'{beach_id} "{name}": no water quality classification')

    return {
        "id": beach_id,
        "name": name,
        "district": district,
        "county": county,
        "region": region,
        "lat": lat,
        "lng": lng,
        "sandy": "sand" in sediments,
        "sediments": sediments,
        "waterQuality": quality,
        "eaMonitored": True,
    }


def load_extra_beaches(county_map):
    """Curated beaches that are not EA-designated bathing waters."""
    path = DATA / "extra_beaches.json"
    if not path.exists():
        return []
    extras = json.loads(path.read_text(encoding="utf-8"))["beaches"]
    out = []
    for e in extras:
        sediments = sorted(e.get("sediments", []))
        district = e["district"]
        county = county_map.get(district)
        if district and not county:
            warn(f'{e["id"]} "{e["name"]}": no county mapping for district "{district}"')
        out.append({
            "id": e["id"],
            "name": e["name"],
            "district": district,
            "county": county,
            "region": e.get("region"),
            "lat": e.get("lat"),
            "lng": e.get("lng"),
            "sandy": "sand" in sediments,
            "sediments": sediments,
            "waterQuality": None,
            "eaMonitored": False,
        })
    return out


def main():
    config = json.loads((DATA / "config.json").read_text(encoding="utf-8"))

    dog_rules = {}
    rules_path = DATA / "dog_rules.json"
    if rules_path.exists():
        dog_rules = json.loads(rules_path.read_text(encoding="utf-8"))["entries"]
    else:
        warn("data/dog_rules.json not found — all beaches marked unknown")

    county_map = {}
    counties_path = DATA / "counties.json"
    if counties_path.exists():
        raw_counties = json.loads(counties_path.read_text(encoding="utf-8"))
        county_map = {k: v for k, v in raw_counties.items() if not k.startswith("_")}
    else:
        warn("data/counties.json not found — all beaches missing county")

    beaches = []
    seen_ids = set()
    ids = fetch_all_beach_ids(config["countryUri"])
    if not ids:
        warn("no beaches returned for configured country")
    for beach_id in ids:
        time.sleep(DELAY)
        beach = fetch_beach(beach_id, county_map)
        beaches.append(beach)
        seen_ids.add(beach_id)

    for beach in load_extra_beaches(county_map):
        if beach["id"] in seen_ids:
            warn(f'extra beach {beach["id"]} duplicates an EA beach — skipped')
            continue
        beaches.append(beach)
        seen_ids.add(beach["id"])

    # Merge curated dog rules; validate both directions.
    for rule_id in dog_rules:
        if rule_id not in seen_ids:
            warn(f"dog_rules entry {rule_id} matches no EA beach")
    for beach in beaches:
        rule = dog_rules.get(beach["id"])
        if rule:
            beach["dogs"] = rule
        else:
            warn(f'no dog data for {beach["id"]} "{beach["name"]}" — marked unknown')
            beach["dogs"] = {"status": "unknown"}

    beaches.sort(key=lambda b: (b["district"], b["name"]))

    out = {
        "meta": {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "coverage": config["coverage"],
            "attribution": ATTRIBUTION,
            "beachCount": len(beaches),
        },
        "beaches": beaches,
    }
    out_path = DATA / "beaches.json"
    out_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Wrote {out_path} ({len(beaches)} beaches)")


if __name__ == "__main__":
    main()
