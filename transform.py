import datetime as dt

def milliseconds_to_iso(ms):
    if ms is None:
        return None
    seconds = ms / 1000
    date_iso = dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc).isoformat()
    return date_iso


def flatten_events(data):
    rows = []
    for feature in data["features"]:
        props = feature["properties"]
        lon, lat, depth = feature["geometry"]["coordinates"]

        row = {"id" : feature["id"],
               "event_time" : milliseconds_to_iso(props.get("time")),
               "place" : props.get("place"),
               "type" : props.get("type"),
               "magnitude" : props.get("mag"),
               "tsunami" : props.get("tsunami"),
               "status" : props.get("status"),
               "updated" : milliseconds_to_iso(props.get("updated")),
               "lon" : lon,
               "lat" : lat,
               "depth" : depth}

        rows.append(row)

    return rows

