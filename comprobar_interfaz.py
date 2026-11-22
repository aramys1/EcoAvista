import json
import sqlite3
from pathlib import Path
from app import app
from init_db import read_csv, DB_PATH

with sqlite3.connect(DB_PATH) as db:
    assert db.execute("SELECT COUNT(*) FROM especies_lugares").fetchone()[0] == len(read_csv("especies_lugares.csv")) + len(read_csv("observaciones_gbif.csv"))
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    assert db.execute("SELECT COUNT(*) FROM especies").fetchone()[0] == len(read_csv("especies.csv"))
    assert db.execute("SELECT COUNT(*) FROM lugares").fetchone()[0] == 85
with app.test_client() as client:
    for url in ['/', '/especies', '/especies/E002', '/lugares', '/lugares/L004', '/mapa', '/mapa?grupo=aves', '/mapa?checklist=si', '/mapa?checklist=no&coordenada=centroide', '/mapa?manejo=Parque+Nacional', '/mapa?especie=E002&grupo=plantas', '/nosotros']:
        response = client.get(url)
        assert response.status_code == 200, url
        text = response.get_data(as_text=True)
        assert 'Nombre común desconocido' not in text, url
        assert 'Fotografía pendiente' not in text, url
        assert 'La cobertura fotográfica está incompleta' not in text, url
        print(url, response.status_code)
    text = client.get('/mapa?checklist=si').get_data(as_text=True)
    points = json.loads(text.split('window.ecoAvistaMapPoints = ')[1].split(';</script>')[0])
    assert len(points) == len({r["id_lugar"] for r in read_csv("especies_lugares.csv") + read_csv("observaciones_gbif.csv")})
    assert all(point['count'] > 0 and point['maps'].startswith('https://www.google.com/maps/search/') for point in points)
    text = client.get('/mapa').get_data(as_text=True)
    points = json.loads(text.split('window.ecoAvistaMapPoints = ')[1].split(';</script>')[0])
    assert len(points) == 85
    assert sum(point['centroid'] for point in points) == 83
print('Integridad SQLite y rutas correctas; mapa y registros correctos.')

with app.test_client() as client, sqlite3.connect(DB_PATH) as db:
    first = client.get('/especies').get_data(as_text=True)
    second = client.get('/especies?pagina=2').get_data(as_text=True)
    assert first.count('class="card species-card"') == 24
    assert second.count('class="card species-card"') == 24
    assert 'Página 2 de' in second
    text = client.get('/especies?categoria=fauna&pagina=2').get_data(as_text=True)
    assert 'categoria=fauna' in text and 'pagina=3' in text
    for route in ['/lugares?provincia=Veraguas', '/mapa?provincia=Veraguas', '/lugares?q=Campana', '/mapa?area=L001']:
        response = client.get(route)
        assert response.status_code == 200
    text = client.get('/mapa?provincia=Veraguas').get_data(as_text=True)
    points = json.loads(text.split('window.ecoAvistaMapPoints = ')[1].split(';</script>')[0])
    expected = db.execute("SELECT COUNT(*) FROM lugares WHERE (';' || provincias || ';') LIKE '%;Veraguas;%' ").fetchone()[0]
    assert len(points) == expected and expected > 0
    text = client.get('/mapa?area=L001').get_data(as_text=True)
    points = json.loads(text.split('window.ecoAvistaMapPoints = ')[1].split(';</script>')[0])
    assert len(points) == 1 and points[0]['name'] == 'Altos de Campana'
print('Paginación, filtros por región y enfoque de área correctos.')
