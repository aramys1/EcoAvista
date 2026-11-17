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
- `/mapa`: Leaflet con filtro por especie, 85 puntos diferenciados por tipo de coordenada y lista disponible sin mapa externo.
- `/lugares`: catálogo con filtro por estado de acceso; `/lugares/<id>` muestra la ficha, sus fuentes y especies relacionadas.
- `/nosotros`: propósito, integrantes del Grupo 3, método, límites y fuentes.

## Datos y límites

Los cuatro CSV de `data/` son la fuente estática para especies, lugares, relaciones y fuentes. La inicialización sincroniza sus registros por identificador y puede repetirse sin duplicarlos. Las relaciones de checklist no se presentan como avistamientos confirmados ni como coordenadas individuales de especies. Los campos vacíos de conservación nacional se muestran como “Sin dato confirmado”.

Los datos de procedencia y las notas metodológicas se guardan desde `data/` y se muestran en las fichas y en la página Nosotros. OpenStreetMap © colaboradores es el proveedor de mosaicos base del mapa.

La carga actual tiene 3.507 especies (2.976 flora y 531 fauna), 85 áreas protegidas, 4.984 relaciones por fuente y 19 fuentes. La clave de relaciones incluye especie, lugar y fuente; la migración conserva las filas anteriores y la importación recupera las que colapsaba la clave antigua. Los checklists seleccionados son de Altos de Campana, Soberanía, Barro Colorado y Coiba. No es un inventario completo de todas las especies de Panamá.

83 puntos son centroides aproximados MiAMBIENTE y dos son coordenadas referenciales STRI. No indican entradas ni posiciones individuales de especies. No se ofrecen filtros de acceso porque los CSV no incluyen ese dato.

`data/imagenes_especies.csv` contiene una fila por cada una de las 3.507 especies. Anacardium occidentale y Dendrobates auratus conservan fotografías identificadas; las otras 3.505 muestran una de seis ilustraciones originales de grupo, etiquetada “Ilustración referencial”. Todos los archivos activos de especies están en `static/img/especies/`. Una ilustración de grupo no permite identificar la especie exacta.

`data/imagenes_lugares.csv` contiene 85 filas. Coiba tiene una fotografía identificada de dronepicr (CC BY 2.0); las otras 84 áreas muestran “Mapa del área”. Cada área tiene además su propio mapa como respaldo, generado desde su geometría oficial MiAMBIENTE, asociada por `objectid_1` al `id_miambiente` del CSV y comprobada por nombre. `data/geometrias_lugares.json` conserva una copia estática EPSG:32617 simplificada para miniaturas; no sirve para navegación ni delimitación legal. La capa no declara una licencia específica y se conserva su procedencia sin atribuirle una licencia inventada.

`python preparar_visuales.py` regenera los SVG y los registros visuales desde los datos locales; no realiza descargas. `python init_db.py` migra y sincroniza los seis CSV. Si una imagen falta, Flask usa el respaldo SVG incrustado; si falla al cargar en el navegador, el manejador local cambia la imagen y su etiqueta al respaldo. Las fichas muestran atribución, fuente y condiciones de uso; el respaldo nunca conserva una etiqueta de fotografía.

Las imágenes y los respaldos funcionan sin Internet durante la navegación. Leaflet y las teselas OpenStreetMap sí requieren conexión; ante un fallo se muestra un aviso y permanece visible la lista de lugares. No se agregaron dependencias ni actualizaciones automáticas.
