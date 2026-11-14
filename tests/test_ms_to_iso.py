from transform import milliseconds_to_iso

def test_ms_to_iso_utc():
    assert milliseconds_to_iso(0) == "1970-01-01T00:00:00+00:00"
    assert milliseconds_to_iso(None) is None