import json
from catalogar_fotos import ROOT, fetch, dimensions

SELECTED = {'L_MA_004': 0, 'L_MA_020': 0, 'L_MA_014': 0, 'L_MA_077': 2, 'L001': 2}

if __name__ == '__main__':
    rows = {r['id_lugar']:r for r in map(json.loads, (ROOT/'data/candidatas_miambiente.jsonl').read_text(encoding='utf-8').splitlines())}
    output = []
    for key, index in SELECTED.items():
        candidate = rows[key]['candidatas'][index]
        try:
            data, url, _ = fetch(candidate['imagen_url'])
            width, height = dimensions(data)
            path = 'img/lugares/' + key.lower() + '_miambiente.jpg'
            (ROOT / 'static' / path).write_bytes(data)
            output.append(dict(id_lugar=key, nombre=rows[key]['nombre'], archivo=path, imagen_url=url, fuente_url=candidate['fuente_url'], evidencia=candidate, ancho=width, alto=height))
            print(key, path, flush=True)
        except Exception as error:
            print(str(error), flush=True)
    (ROOT/'data/areas_revision.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
