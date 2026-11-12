import datetime as dt

def milliseconds_to_iso(ms):
    seconds = ms / 1000
    date_iso = dt.datetime.fromtimestamp(seconds).date().isoformat()
    return date_iso


def flatten_events(data):
    rows = []
    for feature in data["features"]:
        props = feature["properties"]
        lon, lat, depth = feature["geometry"]["coordinates"]

        row = {"id" : feature["id"],
               "magnitude" : props.get("mag"),
               "event_time" : milliseconds_to_iso(props.get("time")),
               "updated" : milliseconds_to_iso(props.get("updated")),
               "lon" : lon,
               "lat" : lat,
               "depth" : depth}

        rows.append(row)

    return rows

