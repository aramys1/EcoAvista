import csv
import json
import time
import urllib.parse
import urllib.request
from catalogar_fotos import ROOT, HEADERS, read_csv

SOURCE = 'https://geoportal.miambiente.gob.pa/server/rest/services/Hosted/Panama_Province_Boundaries_2024__4122679916533830055/FeatureServer/0'


def query(params):
    request = urllib.request.Request(SOURCE + '/query', data=urllib.parse.urlencode(params).encode(), headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.load(response)
    if 'error' in data:
        raise ValueError(data['error'])
    return data


if __name__ == '__main__':
    geometries = json.loads((ROOT / 'data/geometrias_lugares.json').read_text(encoding='utf-8'))
    by_id = {str(f['attributes']['objectid_1']): f['geometry'] for f in geometries['features']}
    path = ROOT / 'data/provincias_lugares.jsonl'
    done = {r['id_lugar'] for r in map(json.loads, path.read_text(encoding='utf-8').splitlines())} if path.exists() else set()
    with path.open('a', encoding='utf-8') as output:
        for place in read_csv('lugares.csv'):
            if place['id_lugar'] in done:
                continue
            try:
                geometry = by_id[place['id_miambiente']]
                data = query(dict(f='json', geometry=json.dumps(geometry), geometryType='esriGeometryPolygon', inSR=32617, spatialRel='esriSpatialRelIntersects', outFields='provincia', returnGeometry='false'))
                names = sorted({f['attributes']['provincia'] for f in data['features']})
                row = dict(id_lugar=place['id_lugar'], provincias=';'.join(names), provincia_fuente_url=SOURCE, provincia_metodo='Intersección con geometría oficial del área, simplificada para el catálogo; puede abarcar varias provincias o comarcas.')
                output.write(json.dumps(row, ensure_ascii=False) + '\n')
                output.flush()
                print(place['nombre'], names, flush=True)
            except Exception as error:
                print(place['id_lugar'], str(error), flush=True)
            time.sleep(1)
    records = read_csv('lugares.csv')
    evidence = {r['id_lugar']: r for r in map(json.loads, path.read_text(encoding='utf-8').splitlines())}
    fields = list(records[0]) + [k for k in ['provincias', 'provincia_fuente_url', 'provincia_metodo'] if k not in records[0]]
    for record in records:
        record.update({k: v for k, v in evidence.get(record['id_lugar'], {}).items() if k != 'id_lugar'})
    with (ROOT / 'data/lugares.csv').open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
