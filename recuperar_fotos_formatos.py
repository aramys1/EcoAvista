import json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from catalogar_fotos import ROOT, read_csv, stri_photo


if __name__ == '__main__':
    path = ROOT/'data/fotos_formatos.jsonl'
    done = {r['id_especie'] for r in map(json.loads,path.read_text(encoding='utf-8').splitlines())} if path.exists() else set()
    rows = [r for r in read_csv('imagenes_especies.csv') if r['estado'] != 'verificada' and r['nota'].startswith('Formato') and r['id_especie'] not in done]
    ids = {}
    for row in read_csv('especies_lugares.csv'):
        if row['taxon_id_stri']:
            ids.setdefault(row['id_especie'],set()).add(row['taxon_id_stri'])
    with ThreadPoolExecutor(max_workers=2) as executor, path.open('a',encoding='utf-8') as output:
        futures = {executor.submit(stri_photo,row,sorted(ids.get(row['id_especie'],[]))):row for row in rows}
        count = 0
        for index,future in enumerate(as_completed(futures),1):
            row = futures[future]
            result = future.result()
            result.update(id_especie=row['id_especie'],nombre_cientifico=row['nombre_cientifico'],fecha_verificacion=datetime.now(timezone.utc).isoformat())
            output.write(json.dumps(result,ensure_ascii=False)+'\n')
            output.flush()
            count += result['estado']=='verificada'
            if index % 10 == 0:
                print(index,len(rows),count,flush=True)
