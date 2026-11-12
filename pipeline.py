import json
from extract import extract_and_save
from transform import flatten_events


def main():
    params = {"format": "geojson", "starttime": "2026-11-10", "minmagnitude": 2.5, "limit": 500}
    text = extract_and_save(params, "events.geojson")
    data = json.loads(text)
    print(f"Number of events: {len(data["features"])}")

    data = flatten_events(data)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()