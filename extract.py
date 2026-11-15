import logging
import os 
import requests

logger = logging.getLogger(__name__)

RAW_DIR = "raw"
URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
DEFAULT_PARAMS = {"format": "geojson", "minmagnitude": 2.5, "limit": 500}


def extract_and_save(params, file_name):
    if params is None:
        params = DEFAULT_PARAMS

    logger.info("Requesting USGS API with params: %s", params)
    response = requests.get(URL, params=params, timeout=30)
    response.raise_for_status()

    os.makedirs(RAW_DIR, exist_ok=True)
    path_to_file = os.path.join(RAW_DIR, file_name)
    with open(path_to_file, "w", encoding = "utf-8") as f:
        f.write(response.text)
    logger.info("Saved raw response to %s (%d bytes)", path_to_file, len(response.content))


    return response.text