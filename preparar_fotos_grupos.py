import json
from catalogar_fotos import ROOT, read_csv
from preparar_referencias_fotograficas import local_photo, slug

PREFERRED = ['Abarema barbouriana', 'Ara macao', 'Agalychnis callidryas', 'Arothron hispidus', 'Panthera onca', 'Iguana iguana']

if __name__ == '__main__':
    images = {r['id_especie']:r for r in read_csv('imagenes_especies.csv')}
    species = read_csv('especies.csv')
    groups = sorted({g.strip() for row in species for g in row['grupo_taxonomico'].split(';') if g.strip()})
    output = {}
    saved_path = ROOT/'data/referencias_grupos.json'
    saved = json.loads(saved_path.read_text(encoding='utf-8')) if saved_path.exists() else {}
    for group in groups:
        candidates = [row for row in species if group in row['grupo_taxonomico'].split(';') and images[row['id_especie']]['estado']=='verificada' and images[row['id_especie']]['tipo_visual'] != 'referencia']
        candidates.sort(key=lambda row:(row['nombre_cientifico'] not in PREFERRED,row['nombre_cientifico']))
        for candidate in candidates[:3]:
            try:
                previous = saved.get(group, {})
                source = images[candidate['id_especie']]
                if previous.get('imagen_url') == source['imagen_url'] and (ROOT/'static'/previous['archivo']).is_file():
                    photo = previous
                else:
                    photo = local_photo(source, 'img/referencias/' + slug(group) + '-' + candidate['id_especie'].lower() + '.jpg')
                photo['grupo_taxonomico'] = group
                output[group] = photo
                print(group, candidate['nombre_cientifico'], flush=True)
                break
            except Exception as error:
                print(group,str(error),flush=True)
    (ROOT/'data/referencias_grupos.json').write_text(json.dumps(output, ensure_ascii=False, indent=2),encoding='utf-8')
