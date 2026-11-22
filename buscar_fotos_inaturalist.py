import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from catalogar_fotos import ROOT, fetch, check_image, read_csv


def photo(row):
    name = row['nombre_cientifico']
    api = 'https://api.inaturalist.org/v1/taxa?' + urllib.parse.urlencode(dict(q=name, per_page=5))
    try:
        taxa = json.loads(fetch(api)[0]).get('results', [])
        for taxon in taxa:
            if taxon['name'] != name:
                continue
            image = taxon.get('default_photo') or {}
            url = image.get('medium_url', '').replace('/medium.', '/large.')
            if not url or not image.get('attribution'):
                continue
            final, width, height = check_image(url)
            return dict(estado='verificada', nombre_confirmado=name, imagen_url=final, fuente_url='https://www.inaturalist.org/taxa/' + str(taxon['id']), autor=image['attribution'], licencia=image.get('license_code') or 'Condiciones del proveedor', licencia_url='', archivo='', fecha_verificacion=datetime.now(timezone.utc).isoformat(), nota='Foto principal del taxón identificado por nombre científico exacto en iNaturalist.', evidencia=dict(api=api, nombre=taxon['name'], ancho=width, alto=height, foto_id=image.get('id')))
    except Exception as error:
        return dict(estado='pendiente', nota=str(error))
    return dict(estado='pendiente', nota='Sin foto de taxón con coincidencia exacta en iNaturalist')


if __name__ == '__main__':
    path = ROOT / 'data/fotos_inaturalist.jsonl'
    done = {r['id_especie'] for r in map(json.loads, path.read_text(encoding='utf-8').splitlines())} if path.exists() else set()
    todo = [r for r in read_csv('imagenes_especies.csv') if r['estado'] != 'verificada' and r['id_especie'] not in done]
    with ThreadPoolExecutor(max_workers=3) as executor, path.open('a', encoding='utf-8') as output:
        futures = {executor.submit(photo, row): row for row in todo}
        found = 0
        for index, future in enumerate(as_completed(futures), 1):
            row = futures[future]
            result = future.result()
            result.update(id_especie=row['id_especie'], nombre_cientifico=row['nombre_cientifico'])
            output.write(json.dumps(result, ensure_ascii=False) + '\n')
            output.flush()
            found += result['estado'] == 'verificada'
            if index % 25 == 0:
                print(index, len(todo), found, flush=True)
