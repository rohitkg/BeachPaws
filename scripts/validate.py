#!/usr/bin/env python3
"""Offline, stdlib-only validator for BeachPaws' curated + generated data.

Run with no arguments to check the current data/*.json files:

    python3 scripts/validate.py

Optionally pass a captured build_data.py stderr log as the first argument to
additionally check that log's WARN lines against the committed warning-class
baseline (data/warning_baseline.json):

    python3 scripts/validate.py _research/build_stderr.log

Exits non-zero with one "FAIL: ..." line per problem on stderr. Prints a
short summary on success. This is the single source of truth for data
correctness — scripts/check.sh and CI both just run this script.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

VALID_STATUSES = {"friendly", "seasonal", "banned", "unknown"}
MMDD_RE = re.compile(r"^\d{2}-\d{2}$")
HHMM_RANGE_RE = re.compile(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Roughly England's bounding box (generous — this is a sanity check, not a
# precise polygon test). Longitude is negative west of Greenwich.
LAT_MIN, LAT_MAX = 49.0, 56.0
LNG_MIN, LNG_MAX = -7.0, 2.5

# Last known-good full run was 470; below this a pipeline run likely got
# truncated (pagination cut short, partial fetch).
MIN_BEACH_COUNT = 400


def is_number(x):
    """int/float but not bool — bool is a subclass of int in Python, and a
    JSON `true`/`false` slipping into a numeric field should fail the type
    check, not silently pass a `0 <= True <= 56`-style comparison."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def load_json(path):
    """Parse path as JSON. Returns (data, error_message_or_None)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"{path}: cannot read file: {e}"
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, f"{path}: invalid JSON: {e}"


def check_ban(entry_id, dogs, problems):
    status = dogs.get("status")
    has_ban = "ban" in dogs

    if status == "seasonal" and not has_ban:
        problems.append(f'{entry_id}: status is "seasonal" but has no "ban" object')
        return
    if status != "seasonal" and has_ban:
        problems.append(f'{entry_id}: has a "ban" object but status is "{status}", not "seasonal"')
        return
    if not has_ban:
        return

    ban = dogs["ban"]
    if not isinstance(ban, dict):
        problems.append(f'{entry_id}: "ban" must be an object, got {ban!r}')
        return

    for key in ("from", "to"):
        value = ban.get(key)
        if not isinstance(value, str) or not MMDD_RE.match(value):
            problems.append(
                f"{entry_id}: ban.{key} = {value!r} does not match MM-DD exactly "
                f'(e.g. an unpadded "5-01" would silently break app.js\'s lexical '
                f"date-string comparison with no error anywhere else)"
            )

    if "daily" in ban:
        daily = ban["daily"]
        m = HHMM_RANGE_RE.match(daily) if isinstance(daily, str) else None
        if not m:
            problems.append(f'{entry_id}: ban.daily = {daily!r} does not match "HH:MM-HH:MM"')
        else:
            h1, m1, h2, m2 = (int(g) for g in m.groups())
            if not (0 <= h1 <= 23 and 0 <= m1 <= 59 and 0 <= h2 <= 23 and 0 <= m2 <= 59):
                problems.append(
                    f"{entry_id}: ban.daily = {daily!r} has an out-of-range hour/minute"
                )


def check_accessed(entry_id, accessed, problems):
    if not isinstance(accessed, str) or not DATE_RE.match(accessed):
        problems.append(f"{entry_id}: accessed = {accessed!r} is not a YYYY-MM-DD date")
        return
    try:
        parsed = datetime.strptime(accessed, "%Y-%m-%d").date()
    except ValueError:
        problems.append(f"{entry_id}: accessed = {accessed!r} does not parse as a real date")
        return
    today = datetime.now(timezone.utc).date()
    if parsed > today:
        problems.append(f"{entry_id}: accessed = {accessed} is in the future (today is {today})")


def check_source(entry_id, source, problems):
    # SECURITY CHECK: dogs.source is rendered straight into an <a href> by
    # app.js with no scheme check. A "javascript:" (or other non-https)
    # source merged in from a future community PR would be stored XSS.
    # This validator is the gate — don't weaken this to accommodate a
    # non-https source; re-source the entry instead.
    if not isinstance(source, str) or not source.startswith("https://"):
        problems.append(f'{entry_id}: source = {source!r} must start with "https://"')


def validate_dog_rules(dog_rules_doc, problems):
    """Validate data/dog_rules.json's own shape, independent of beaches.json.
    Returns the entries dict (or {} if the document shape was unusable)."""
    if not isinstance(dog_rules_doc, dict) or "entries" not in dog_rules_doc:
        problems.append('data/dog_rules.json: missing top-level "entries" object')
        return {}
    entries = dog_rules_doc["entries"]
    if not isinstance(entries, dict):
        problems.append('data/dog_rules.json: "entries" must be an object keyed by beach id')
        return {}

    for entry_id, dogs in entries.items():
        if not isinstance(dogs, dict):
            problems.append(f"{entry_id}: entry must be an object")
            continue
        status = dogs.get("status")
        if status not in VALID_STATUSES:
            problems.append(f"{entry_id}: status = {status!r} not one of {sorted(VALID_STATUSES)}")
        # dog_rules.json only ever curates real statuses — "unknown" is
        # assigned automatically by build_data.py for beaches with no entry
        # here — so every curated entry must carry its provenance.
        if "source" not in dogs:
            problems.append(f'{entry_id}: missing required "source" field')
        else:
            check_source(entry_id, dogs["source"], problems)
        if "accessed" not in dogs:
            problems.append(f'{entry_id}: missing required "accessed" field')
        else:
            check_accessed(entry_id, dogs["accessed"], problems)
        check_ban(entry_id, dogs, problems)

    return entries


def validate_beaches(beaches_doc, problems):
    """Validate data/beaches.json (pipeline output). Returns the beach id set
    (or set() if the document shape was unusable)."""
    if not isinstance(beaches_doc, dict) or "beaches" not in beaches_doc:
        problems.append('data/beaches.json: missing top-level "beaches" array')
        return set()
    beaches = beaches_doc["beaches"]
    if not isinstance(beaches, list):
        problems.append('data/beaches.json: "beaches" must be an array')
        return set()

    if len(beaches) < MIN_BEACH_COUNT:
        problems.append(
            f"data/beaches.json: only {len(beaches)} beaches, expected at least "
            f"{MIN_BEACH_COUNT} — looks like a truncated/partial pipeline run"
        )

    seen_ids = set()
    for beach in beaches:
        if not isinstance(beach, dict):
            problems.append(f"data/beaches.json: beach entry must be an object, got {beach!r}")
            continue

        beach_id = beach.get("id")
        if beach_id in seen_ids:
            problems.append(f"data/beaches.json: duplicate beach id {beach_id!r}")
        seen_ids.add(beach_id)

        dogs = beach.get("dogs")
        if not isinstance(dogs, dict) or "status" not in dogs:
            problems.append(f'{beach_id}: missing "dogs" object with a status')
        elif dogs["status"] not in VALID_STATUSES:
            problems.append(
                f"{beach_id}: dogs.status = {dogs['status']!r} not one of {sorted(VALID_STATUSES)}"
            )

        lat, lng = beach.get("lat"), beach.get("lng")
        if lat is not None:
            if not is_number(lat):
                problems.append(f"{beach_id}: lat = {lat!r} is not a number")
            elif not (LAT_MIN <= lat <= LAT_MAX):
                problems.append(f"{beach_id}: lat {lat} outside England bounding box")
        if lng is not None:
            if not is_number(lng):
                problems.append(f"{beach_id}: lng = {lng!r} is not a number")
            elif not (LNG_MIN <= lng <= LNG_MAX):
                problems.append(f"{beach_id}: lng {lng} outside England bounding box")

    return seen_ids


def cross_check_ids(dog_rule_ids, beach_ids, problems):
    """Every dog_rules.json entry should refer to a real beach id. A mismatch
    here is ambiguous on its own: it's either a typo'd id in dog_rules.json,
    or a curated-file edit (e.g. a newly added entry) that just hasn't been
    through scripts/build_data.py yet, so beaches.json doesn't know about it
    yet. Say both possibilities so the message is never confusing."""
    if not beach_ids:
        return  # beaches.json itself was unusable; already reported above.
    for rule_id in dog_rule_ids:
        if rule_id not in beach_ids:
            problems.append(
                f"{rule_id}: in dog_rules.json but not in data/beaches.json — "
                f"either a typo'd beach id, or you added/edited this entry and "
                f"haven't rerun `python3 scripts/build_data.py` yet"
            )


# --- Warning-baseline mode -------------------------------------------------
#
# Each (substring, class name) pair below corresponds 1:1 to a warn() call
# site in build_data.py. A log line is classified by the first pair whose
# substring it contains. A WARN line matching none of these is a warning
# *shape* the validator has never seen — always a hard failure, regardless
# of the baseline file, since it means build_data.py grew a new warn() call
# that nobody's looked at yet.
WARNING_CLASSES = [
    (": no name in EA record", "no_name_in_ea_record"),
    (": no district in EA record", "no_district_in_ea_record"),
    (": no county mapping for district ", "no_county_mapping"),
    (": no regionalOrganization in EA record", "no_region_in_ea_record"),
    (": no sediment data", "no_sediment"),
    (": missing coordinates", "missing_coordinates"),
    (": no water quality classification", "no_water_quality"),
    ("no dog data for ", "dog_unknown"),
    ("dog_rules entry ", "dog_rule_unmatched"),
    ("duplicates an EA beach — skipped", "extra_beach_duplicate"),
    ("data/dog_rules.json not found", "no_dog_rules_file"),
    ("data/counties.json not found", "no_counties_file"),
    ("no beaches returned for configured country", "no_beaches_returned"),
]


def classify_warning(line):
    for substring, class_name in WARNING_CLASSES:
        if substring in line:
            return class_name
    return None


def check_warning_baseline(log_path, problems):
    path = Path(log_path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        problems.append(f"cannot read warning log {log_path}: {e}")
        return

    baseline_path = DATA / "warning_baseline.json"
    baseline_doc, err = load_json(baseline_path)
    if err:
        problems.append(err)
        return
    baseline = baseline_doc.get("classes", {})

    counts = {}
    unrecognized = []
    for line in lines:
        if not line.startswith("WARN: "):
            continue
        cls = classify_warning(line)
        if cls is None:
            unrecognized.append(line)
            continue
        counts[cls] = counts.get(cls, 0) + 1

    for line in unrecognized:
        problems.append(
            f"unrecognized warning shape in {log_path} (matches no known "
            f"WARNING_CLASSES entry in validate.py — build_data.py may have "
            f"grown a new warn() call site): {line!r}"
        )

    new_classes = sorted(set(counts) - set(baseline))
    for cls in new_classes:
        problems.append(
            f'warning class "{cls}" (n={counts[cls]}) appears in {log_path} but is '
            f"not in {baseline_path} — if this is expected, add it to the "
            f"baseline; if not, it's new pipeline behaviour worth a look"
        )

    print(f"Warning-baseline comparison against {log_path}:", file=sys.stderr)
    for cls in sorted(set(counts) | set(baseline)):
        expected = baseline.get(cls, 0)
        actual = counts.get(cls, 0)
        flag = "" if expected == actual else "  (drifted from baseline; not a failure)"
        print(f"  {cls}: {actual} (baseline {expected}){flag}", file=sys.stderr)


def main():
    args = sys.argv[1:]
    log_path = args[0] if args else None

    problems = []

    dog_rules_doc, err = load_json(DATA / "dog_rules.json")
    if err:
        problems.append(err)
        dog_rules_doc = None

    beaches_doc, err = load_json(DATA / "beaches.json")
    if err:
        problems.append(err)
        beaches_doc = None

    dog_rule_ids = validate_dog_rules(dog_rules_doc, problems) if dog_rules_doc is not None else {}
    beach_ids = validate_beaches(beaches_doc, problems) if beaches_doc is not None else set()
    cross_check_ids(dog_rule_ids, beach_ids, problems)

    if log_path:
        check_warning_baseline(log_path, problems)

    if problems:
        for p in problems:
            print(f"FAIL: {p}", file=sys.stderr)
        print(f"\n{len(problems)} problem(s) found.", file=sys.stderr)
        sys.exit(1)

    beach_count = len(beach_ids)
    unknown_count = 0
    if beaches_doc:
        unknown_count = sum(
            1 for b in beaches_doc["beaches"] if b.get("dogs", {}).get("status") == "unknown"
        )
    print(
        f"OK: {beach_count} beaches, {len(dog_rule_ids)} curated dog rules "
        f"({unknown_count} unknown), 0 problems."
    )


if __name__ == "__main__":
    main()
