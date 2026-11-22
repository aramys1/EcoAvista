import json
import sqlite3
from pathlib import Path
from app import app, image_registry
from catalogar_fotos import dimensions, ROOT
from init_db import read_csv, DB_PATH

with app.test_request_context('/'):
    registries = image_registry()
    local_files = set()
    for name, total in [('images', len(read_csv('especies.csv'))), ('place_images', 85)]:
        registry = registries[name]
        assert len(registry) == total
        for key, row in registry.items():
            assert row['src'] and row['estado'] == 'verificada', key
            backup = row['backup']
            if name == 'images':
                assert backup and backup['src'].startswith('/static/img/'), key
                local_files.add(backup['archivo'])
            else:
                assert row['archivo'] and row['tipo_visual'] == 'fotografia', key
            if row['archivo']:
                local_files.add(row['archivo'])
            if row['tipo_visual'] == 'referencia':
                assert row['archivo'] and row['reference_label'], key
            else:
                assert row['nombre_confirmado'] == (row.get('nombre_cientifico') or row.get('nombre')), key
        print(name, total, 'con imagen local' if name == 'place_images' else 'con foto y respaldo local')
    for filename in local_files:
        assert min(dimensions((ROOT/'static'/filename).read_bytes())) >= 200, filename

with app.test_client() as client:
    for filename in local_files:
        response = client.get('/static/' + filename)
        assert response.status_code == 200 and response.mimetype.startswith('image/'), filename
    for table, route, key in [('imagenes_especies','/especies/', 'id_especie'), ('imagenes_lugares','/lugares/', 'id_lugar')]:
        with sqlite3.connect(DB_PATH) as database:
            record = database.execute(f"SELECT {key} FROM {table} WHERE tipo_visual='referencia' LIMIT 1").fetchone()
        if record is None:
            assert table == 'imagenes_lugares'
            continue
        record = record[0]
        text = client.get(route + record).get_data(as_text=True)
        assert 'Imagen referencial' in text and 'data-backup=' in text
        if table == 'imagenes_especies':
            assert 'Especie fotografiada:' in text
    map_html = client.get('/mapa').get_data(as_text=True)
    points = json.loads(map_html.split('window.ecoAvistaMapPoints = ')[1].split(';</script>')[0])
    assert len(points) == 85 and all(point['image'].startswith('/static/') for point in points)
with sqlite3.connect(DB_PATH) as database:
    assert database.execute('SELECT COUNT(*) FROM especies_lugares').fetchone()[0] == len(read_csv("especies_lugares.csv")) + len(read_csv("observaciones_gbif.csv"))
    assert not database.execute('PRAGMA foreign_key_check').fetchall()
coverage = json.loads((ROOT/'data/cobertura_fotografias.json').read_text(encoding='utf-8'))
assert all(row['pendientes'] == 0 and row['cobertura_porcentaje'] == 100 for row in coverage.values())
print(len(local_files), 'archivos locales cargables; etiquetas, créditos, puntos y registros correctos.')
