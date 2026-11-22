import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from catalogar_fotos import ROOT, read_csv, fetch, stri_photo


def recover(row, ids):
    original = row['nombre_cientifico']
    name = original
    taxonomy = {}
    if 'encabezado' in row['nota']:
        api = 'https://api.gbif.org/v1/species/match?' + urllib.parse.urlencode(dict(name=original, strict='true'))
        try:
            taxonomy = json.loads(fetch(api)[0])
            if taxonomy.get('matchType') != 'EXACT' or taxonomy.get('rank') != 'SPECIES':
                return dict(estado='pendiente', nota='Sin equivalencia taxonómica exacta documentada')
            key = taxonomy.get('acceptedUsageKey', taxonomy.get('usageKey'))
            accepted = json.loads(fetch('https://api.gbif.org/v1/species/' + str(key))[0])
            name = accepted.get('canonicalName', original)
        except Exception as error:
            return dict(estado='pendiente', nota=str(error))
    result = stri_photo({'nombre_cientifico':name}, ids)
    if result['estado'] == 'verificada':
        result.update(nombre_confirmado=original, nota='Foto de la especie; equivalencia de sinónimos comprobada en GBIF.' if name != original else result['nota'])
        result['evidencia'].update(nombre_catalogo=original, nombre_fuente=name, equivalencia_gbif=taxonomy)
    return result


if __name__ == '__main__':
    path = ROOT/'data/fotos_taxonomia_actualizada.jsonl'
    done = {r['id_especie'] for r in map(json.loads,path.read_text(encoding='utf-8').splitlines())} if path.exists() else set()
    rows = [r for r in read_csv('imagenes_especies.csv') if r['estado'] != 'verificada' and r['id_especie'] not in done]
    ids = {}
    for row in read_csv('especies_lugares.csv'):
        if row['taxon_id_stri']:
            ids.setdefault(row['id_especie'],set()).add(row['taxon_id_stri'])
    with ThreadPoolExecutor(max_workers=3) as executor, path.open('a',encoding='utf-8') as output:
        futures = {executor.submit(recover,r,sorted(ids.get(r['id_especie'],[]))):r for r in rows}
        count = 0
        for index,future in enumerate(as_completed(futures),1):
            row = futures[future]
            try:
                result = future.result()
            except Exception as error:
                result = dict(estado='pendiente', nota=str(error))
            result.update(id_especie=row['id_especie'],nombre_cientifico=row['nombre_cientifico'],fecha_verificacion=datetime.now(timezone.utc).isoformat())
            output.write(json.dumps(result,ensure_ascii=False)+'\n')
            output.flush()
            count += result['estado'] == 'verificada'
            if index % 25 == 0:
                print(index,len(rows),count,flush=True)
