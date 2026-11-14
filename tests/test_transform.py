# Create a "fake" feature and test that imported values are correct

from transform import flatten_events

def test_flatten_events():
    data = {"features" : [{
        "id" : "abc123",
        "properties": {
            "mag": 4.5,
            "time": 0,
            "updated": 86400000,
            "place": "10 km N of Roma",
            "type": "earthquake",
            "tsunami": 0,
            "status": "reviewed",
        },
        "geometry": {"coordinates": [12.5, 41.9, 10.0]},  # lon, lat, depth
    }]}
    
    rows = flatten_events(data)

    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "abc123"
    assert row["magnitude"] == 4.5
    assert row["event_time"] == "1970-01-01T00:00:00+00:00"
    assert row["updated"] == "1970-01-02T00:00:00+00:00"
    assert row["place"] == "10 km N of Roma"
    assert row["lon"] == 12.5
    assert row["lat"] == 41.9
    assert row["depth"] == 10.0