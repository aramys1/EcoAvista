import json
import re
import urllib.parse
from datetime import datetime, timezone
from catalogar_fotos import ROOT, fetch, check_image, plain, read_csv


if __name__ == '__main__':
    path = ROOT / 'data/fotos_wikidata.jsonl'
    records = [r for r in read_csv('imagenes_especies.csv') if r['estado'] != 'verificada']
    completed = {r['id_especie'] for r in map(json.loads, path.read_text(encoding='utf-8').splitlines())} if path.exists() else set()
    records = [r for r in records if r['id_especie'] not in completed]
    with path.open('a', encoding='utf-8') as output:
        for start in range(0, len(records), 50):
            batch = records[start:start + 50]
            names = ' '.join(json.dumps(r['nombre_cientifico']) for r in batch)
            query = 'SELECT ?name ?item ?image WHERE { VALUES ?name { ' + names + ' } ?item wdt:P225 ?name; wdt:P18 ?image. }'
            try:
                bindings = json.loads(fetch('https://query.wikidata.org/sparql?' + urllib.parse.urlencode(dict(query=query, format='json')))[0])['results']['bindings']
            except Exception as error:
                print('Consulta:', str(error), flush=True)
                continue
            for row in batch:
                result = dict(id_especie=row['id_especie'], nombre_cientifico=row['nombre_cientifico'], estado='pendiente', nota='Sin foto exacta comprobada mediante Wikidata y Commons')
                for binding in bindings:
                    if binding['name']['value'] != row['nombre_cientifico']:
                        continue
                    try:
                        filename = urllib.parse.unquote(binding['image']['value'].rsplit('/', 1)[-1])
                        params = dict(action='query', format='json', titles='File:' + filename, prop='imageinfo', iiprop='url|extmetadata', iiurlwidth=960)
                        pages = json.loads(fetch('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params))[0])['query']['pages']
                        info = next(iter(pages.values()))['imageinfo'][0]
                        meta = info['extmetadata']
                        description = ' '.join(plain(meta.get(k, {}).get('value', '')) for k in ['ImageDescription', 'Categories', 'ObjectName'])
                        if re.search(r'illustrat|drawing|engraving|lithograph|painting|dessin|dibujo|map\b|fossil reconstruction', description + filename, re.I):
                            continue
                        if not re.search(r'\.(jpe?g)$', filename, re.I):
                            continue
                        image, width, height = check_image(info.get('thumburl', info['url']))
                        result.update(estado='verificada', nombre_confirmado=row['nombre_cientifico'], imagen_url=image, fuente_url=info['descriptionurl'], autor=plain(meta.get('Artist', {}).get('value', '')) or 'Autor no indicado en Commons', licencia=plain(meta.get('LicenseShortName', {}).get('value', 'Condiciones de Commons')), licencia_url=meta.get('LicenseUrl', {}).get('value', ''), archivo='', fecha_verificacion=datetime.now(timezone.utc).isoformat(), nota='Fotografía asociada al nombre científico exacto en Wikidata y documentada en Commons.', evidencia=dict(taxon=binding['item']['value'], descripcion=description, ancho=width, alto=height))
                        break
                    except Exception as error:
                        result['nota'] = str(error)
                output.write(json.dumps(result, ensure_ascii=False) + '\n')
                output.flush()
            print(start + len(batch), len(records), flush=True)
