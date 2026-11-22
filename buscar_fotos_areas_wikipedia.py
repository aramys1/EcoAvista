import json
import re
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from catalogar_fotos import ROOT, fetch, check_image, plain, read_csv


def norm(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', value.lower()) if unicodedata.category(c) != 'Mn').split())


def wiki(params, host='es.wikipedia.org'):
    return json.loads(fetch('https://' + host + '/w/api.php?' + urllib.parse.urlencode(dict(format='json', action='query', **params)))[0])


if __name__ == '__main__':
    path = ROOT / 'data/fotos_areas_wikipedia.jsonl'
    done = {r['id_lugar'] for r in map(json.loads, path.read_text(encoding='utf-8').splitlines())} if path.exists() else set()
    rows = [r for r in read_csv('imagenes_lugares.csv') if r['estado'] != 'verificada' and r['id_lugar'] not in done]
    places = {r['id_lugar']: r for r in read_csv('lugares.csv')}
    with path.open('a', encoding='utf-8') as output:
        for row in rows:
            place = places[row['id_lugar']]
            result = dict(id_lugar=row['id_lugar'], nombre=row['nombre'], estado='pendiente', nota='Sin fotografía de área exacta comprobada en Wikipedia y Commons')
            try:
                data = wiki(dict(generator='search', gsrsearch=place['nombre'] + ' ' + place['categoria_manejo'] + ' Panamá', gsrlimit=3, prop='extracts|pageimages|info', exintro=1, explaintext=1, piprop='name', inprop='url'))
                for page in data.get('query', {}).get('pages', {}).values():
                    intro = norm(page.get('extract', ''))
                    title = norm(page['title'])
                    name = norm(place['nombre'])
                    category = norm(place['categoria_manejo'])
                    category_match = category in intro or category in title
                    if not category_match or name not in title or 'panama' not in intro or not page.get('pageimage'):
                        continue
                    photo = wiki(dict(titles='File:' + page['pageimage'], prop='imageinfo', iiprop='url|extmetadata', iiurlwidth=960), 'commons.wikimedia.org')
                    info = next(iter(photo['query']['pages'].values()))['imageinfo'][0]
                    meta = info['extmetadata']
                    description = plain(meta.get('ImageDescription', {}).get('value', ''))
                    if name not in norm(description + ' ' + page['pageimage']):
                        continue
                    if re.search(r'illustrat|drawing|map\b|mapa|lithograph|painting', description + page['pageimage'], re.I):
                        continue
                    if not re.search(r'\.jpe?g$', page['pageimage'], re.I):
                        continue
                    image, width, height = check_image(info.get('thumburl', info['url']))
                    result.update(estado='verificada', nombre_confirmado=place['nombre'], imagen_url=image, fuente_url=info['descriptionurl'], autor=plain(meta.get('Artist', {}).get('value', '')) or 'Autor no indicado en Commons', licencia=plain(meta.get('LicenseShortName', {}).get('value', 'Condiciones del proveedor')), licencia_url=meta.get('LicenseUrl', {}).get('value', ''), archivo='', fecha_verificacion=datetime.now(timezone.utc).isoformat(), nota='Foto del artículo que identifica el área por nombre y categoría de manejo.', evidencia=dict(pagina=page['fullurl'], titulo=page['title'], extracto=page['extract'], descripcion=description, ancho=width, alto=height))
                    break
            except Exception as error:
                result['nota'] = str(error)
            output.write(json.dumps(result, ensure_ascii=False) + '\n')
            output.flush()
            print(row['id_lugar'], result['estado'], flush=True)
