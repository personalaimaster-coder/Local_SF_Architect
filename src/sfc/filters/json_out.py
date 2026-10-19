"""--json output filter.

Query results with a records[] list are reprojected to CSV (~82% smaller in
Phase 0); other JSON payloads are whitespace-minified (~32% smaller).
Unparseable text falls back to whitespace squeeze.
"""

import csv
import io
import json
import re

VERSION = "1.0"


def _extract_json(text):
    """Output may be preceded by CLI warnings; parse from the first {/[ onward."""
    for i, ch in enumerate(text):
        if ch in "{[":
            try:
                return json.loads(text[i:])
            except ValueError:
                continue
    raise ValueError("no parseable JSON found")


def _find_records(obj):
    if isinstance(obj, dict):
        res = obj.get("result", obj)
        if isinstance(res, dict):
            records = res.get("records")
            if isinstance(records, list) and records and isinstance(records[0], dict):
                return records
    return None


def _records_to_csv(records):
    cols = [k for k in records[0].keys() if k != "attributes"]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(cols)
    for rec in records:
        writer.writerow([_cell(rec.get(c, "")) for c in cols])
    return buf.getvalue().rstrip("\n"), len(records)


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return value


def compress(text):
    try:
        obj = _extract_json(text)
    except ValueError:
        return re.sub(r"\s+", " ", text).strip()
    records = _find_records(obj)
    if records is not None:
        csv_text, n = _records_to_csv(records)
        return "[sfc] query result reprojected to CSV ({} records)\n{}".format(n, csv_text)
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
