"""Actualiza la muestra local de GBIF. Solo para mantenimiento: pip install requests shapely pyproj."""
import csv
import json
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import requests
from pyproj import Transformer
from shapely.geometry import Point, Polygon

from init_db import DATA_PATH, read_csv

TO_GPS = Transformer.from_crs(32617, 4326, always_xy=True)
TO_METERS = Transformer.from_crs(4326, 32617, always_xy=True)
NAMES = {s["nombre_cientifico"]: s["id_especie"] for s in read_csv("especies.csv")}
PLACES = {s["id_miambiente"]: s["id_lugar"] for s in read_csv("lugares.csv")}


PLACE_NAMES = {s["id_lugar"]: s["nombre"] for s in read_csv("lugares.csv")}


def plain_name(name):
    return "".join(c for c in unicodedata.normalize("NFKD", name.casefold()) if not unicodedata.combining(c))


def sample(feature, check_locality=False):
    place_id = PLACES[str(feature["attributes"]["objectid_1"])]
    rings = feature["geometry"]["rings"]
    shape = Polygon()
    for ring in rings:
        shape = shape.symmetric_difference(Polygon(ring).buffer(0))
    west, south, east, north = TO_GPS.transform_bounds(*shape.bounds)
    params = dict(country="PA", basisOfRecord="HUMAN_OBSERVATION", hasGeospatialIssue="false",
                  occurrenceStatus="PRESENT", decimalLongitude=f"{west:.6f},{east:.6f}",
                  decimalLatitude=f"{south:.6f},{north:.6f}", limit=300,
                  coordinateUncertaintyInMeters="1,1000", year="2000,2026")
    if check_locality:
        del params["coordinateUncertaintyInMeters"]
        del params["year"]
    found = {}
    for offset in (0, 300, 600):
        response = requests.get("https://api.gbif.org/v1/occurrence/search", params={**params, "offset": offset}, timeout=45)
        response.raise_for_status()
        page = response.json()
        for record in page["results"]:
            name = record.get("species")
            if name not in NAMES or name in found or record.get("establishmentMeans") in {"MANAGED", "CAPTIVE"}:
                continue
            point = Point(*TO_METERS.transform(record["decimalLongitude"], record["decimalLatitude"]))
            uncertainty = record.get("coordinateUncertaintyInMeters")
            if not uncertainty:
                locality = plain_name(record.get("locality") or "")
                if not check_locality or plain_name(PLACE_NAMES[place_id]) not in locality:
                    continue
            if not shape.contains(point) or shape.boundary.distance(point) <= (uncertainty or 100):
                continue
            found[name] = [NAMES[name], place_id, "observacion_publica", "F26", "",
                           f"https://www.gbif.org/occurrence/{record['key']}"]
            if len(found) == 16:
                break
        if len(found) >= 16 or page["endOfRecords"]:
            break
    print(place_id, len(found), flush=True)
    return found.values()


if __name__ == "__main__":
    features = json.loads((DATA_PATH / "geometrias_lugares.json").read_text(encoding="utf-8"))["features"]
    target = DATA_PATH / "observaciones_gbif.csv"
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = [row for result in pool.map(sample, features) for row in result]
    covered = {r[1] for r in rows} | {r["id_lugar"] for r in read_csv("especies_lugares.csv")}
    pending = [f for f in features if PLACES[str(f["attributes"]["objectid_1"])] not in covered]
    with ThreadPoolExecutor(max_workers=5) as pool:
        for result in pool.map(lambda f: sample(f, check_locality=True), pending):
            rows.extend(result)
    temporary = target.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["id_especie","id_lugar","tipo_relacion","fuente_id","taxon_id_stri","nota"])
        writer.writerows(sorted(rows))
    temporary.replace(target)
