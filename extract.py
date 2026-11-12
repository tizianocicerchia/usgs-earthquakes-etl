import os 
import requests

RAW_DIR = "raw"
URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
DEFAULT_PARAMS = {"format": "geojson", "minmagnitude": 2.5, "limit": 500}


def extract_and_save(params, file_name):
    if params is None:
        params = DEFAULT_PARAMS

    response = requests.get(URL, params=params, timeout=30)
    response.raise_for_status()

    os.makedirs(RAW_DIR, exist_ok=True)
    path_to_file = os.path.join(RAW_DIR, file_name)
    with open(path_to_file, "w", encoding = "utf-8") as f:
        f.write(response.text)

    return response.text