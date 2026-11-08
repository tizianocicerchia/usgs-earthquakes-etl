import os 
import requests

raw_dir = "raw"
URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

params = {"format": "geojson", "starttime": "2026-10-31", "minmagnitude": 2.5, "limit": 500}

def extract_and_save(params, file_name):

    response = requests.get(URL, params=params, timeout=30)
    response.raise_for_status()

    os.makedirs(raw_dir, exist_ok=True)
    path_to_file = os.path.join(raw_dir, file_name)
    with open(path_to_file, "w", encoding = "utf-8") as f:
        f.write(response.text)

    return response.text