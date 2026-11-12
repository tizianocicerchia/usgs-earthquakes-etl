import json
from transform import flatten_events

def test_flatten_events():
    with open("tests/data/try.geojson", encoding="utf-8") as f:
        data = json.load(f)
    rows = flatten_events(data)

    assert len(rows) == 5