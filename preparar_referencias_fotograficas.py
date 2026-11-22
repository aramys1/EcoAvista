import csv
import json
import shutil
import unicodedata
from datetime import datetime, timezone
from catalogar_fotos import ROOT, read_csv, fetch, dimensions


def slug(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.lower()) if c.isascii() and c.isalnum())


def local_photo(photo, filename):
    target = ROOT / 'static' / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = ROOT / 'static' / (photo.get('archivo') or '__missing__')
    if existing.is_file():
        if existing != target:
            shutil.copyfile(existing, target)
    elif not target.is_file():
        data, final, _ = fetch(photo['imagen_url'])
        width, height = dimensions(data)
        if min(width, height) < 200:
            raise ValueError('Fotografía demasiado pequeña')
        target.write_bytes(data)
    dimensions(target.read_bytes())
    return {**photo, 'archivo': filename, 'fecha_verificacion': datetime.now(timezone.utc).isoformat()}


if __name__ == '__main__':
    places = {r['id_lugar']:r for r in read_csv('imagenes_lugares.csv')}
    output = {}
    saved_path = ROOT/'data/referencias_paisajes.json'
    saved = json.loads(saved_path.read_text(encoding='utf-8')) if saved_path.exists() else {}
    for key, record in [('bosque','L_MA_027'), ('costa','L004'), ('islas','L_MA_020')]:
        try:
            if key in saved and (ROOT/'static'/saved[key]['archivo']).is_file():
                output[key] = saved[key]
                print(key, output[key]['archivo'], flush=True)
                continue
            output[key] = local_photo(places[record], 'img/referencias/' + key + '.jpg')
            print(key, output[key]['archivo'], flush=True)
        except Exception as error:
            print(key, str(error), flush=True)
    (ROOT/'data/referencias_paisajes.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
