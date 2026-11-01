"""Regression: every /api/data/* payload must be strict-JSON serializable.

Covers the production 500 "Out of range float values are not JSON compliant"
seen on ko_1515_anaerobic and anchor_scorecard (NaN survived DataFrame.where
because None recasts to NaN in float columns).

Run: uv run python tests/test_api_data.py   (no extra dependencies)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server  # noqa: E402


def main():
    assert server.DATA_FILES, "no datasets registered"
    for name in sorted(server.DATA_FILES):
        payload = server.data(name)
        assert payload["rows"], f"{name}: empty rows"
        json.dumps(payload, allow_nan=False)  # strict: raises on NaN/inf
        print(f"OK {name} ({len(payload['rows'])} rows)")
    print(f"PASS: {len(server.DATA_FILES)} datasets JSON-clean")


if __name__ == "__main__":
    main()
