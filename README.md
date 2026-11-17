# EcoAvista

Primera versión funcional de EcoAvista: catálogo educativo de especies de Panamá, fichas de especies y lugares, y mapa de localidades con coordenadas. La aplicación usa Flask, SQLite, plantillas Jinja y Leaflet.

## Requisitos

- Python 3.10 o posterior
- pip
- Conexión a internet para cargar Leaflet y los mosaicos de OpenStreetMap en el mapa

## Instalación y ejecución

Desde la carpeta del proyecto, crea y activa un entorno virtual e instala las dependencias:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Inicializa o actualiza la base local desde los CSV y arranca el servidor de desarrollo:

```powershell
python init_db.py
flask --app app run
```

Abre `http://127.0.0.1:5000`. La inicialización se puede repetir: actualiza filas por sus identificadores y conserva las relaciones. La base local se crea en `instance/ecoavista.db` y está excluida de Git.

## Páginas

- `/`: propósito, conteos calculados desde la base y especies del catálogo.
- `/especies`: búsqueda combinada por nombre, flora/fauna, grupo taxonómico, categoría nacional y lugar; `/especies/<id>` muestra la ficha, las fuentes y los checklists relacionados.
- `/mapa`: Leaflet con filtro por especie y acceso; la lista corresponde a los marcadores con coordenadas.
- `/lugares`: catálogo con filtro por estado de acceso; `/lugares/<id>` muestra la ficha, sus fuentes y especies relacionadas.
- `/nosotros`: propósito, integrantes del Grupo 3, método, límites y fuentes.

## Datos y límites

Los cuatro CSV de `data/` son la fuente estática para especies, lugares, relaciones y fuentes. La inicialización sincroniza sus registros por identificador y puede repetirse sin duplicarlos. Las relaciones de checklist no se presentan como avistamientos confirmados ni como coordenadas individuales de especies. Los campos vacíos de conservación nacional se muestran como “Sin dato confirmado”.

Los datos de procedencia y las notas metodológicas se guardan desde `data/` y se muestran en las fichas y en la página Nosotros. OpenStreetMap © colaboradores es el proveedor de mosaicos base del mapa.
