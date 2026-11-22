# EcoAvista

Catálogo educativo de biodiversidad de Panamá. Flask, SQLite, Jinja y Leaflet, con las dependencias existentes y datos estáticos.

## Iniciar

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python init_db.py
python -m flask --app app run
```

Abre http://127.0.0.1:5000. Si no existe el entorno, créalo con `py -m venv .venv`. SQLite se genera en instance/ecoavista.db. `init_db.py` sincroniza los seis CSV de forma repetible; la clave de relaciones es (id_especie, id_lugar, fuente_id).

## Datos y navegación

Los datos estáticos contienen 3.512 especies, 85 áreas protegidas, registros de inventarios, publicaciones y observaciones públicas con sus fuentes. Los inventarios de cuatro sitios se complementan con publicaciones y observaciones públicas enlazadas a GBIF. Una relación no representa un avistamiento ni permite estimar su probabilidad. Las áreas sin checklist siguen formando parte del catálogo geográfico.

83 coordenadas son centroides aproximados de MiAMBIENTE y dos son referencias de localidad STRI. No señalan entradas ni ubicaciones individuales de especies. Google Maps abre una búsqueda por nombre y categoría del área; el visitante debe comprobar el destino y el acceso.

La conservación nacional corresponde a la Resolución DM-0657-2016; las categorías desconocidas se explican únicamente en las fichas. Los nombres comunes documentados encabezan las fichas y tarjetas.

Los CSV imagenes_especies.csv e imagenes_lugares.csv mantienen una fila por registro, con fuente, URL, autor, condiciones, fecha y tipo de imagen. La cobertura visual es del 100 % para las 3.512 especies y los 85 lugares. Las fotografías específicas tienen prioridad. Las especies sin foto propia usan referencias de su grupo. Cada área tiene una imagen local distinta, de campo o satelital, con créditos. Las fichas con dos vistas permiten alternarlas. Se etiquetan como referencias y las fichas identifican la especie realmente fotografiada. data/cobertura_fotografias.json distingue ambos tipos; data/fotografias_referenciales.csv enumera las referencias. No son ilustraciones ni imágenes generadas.

El mapa combina filtros de especie, grupo taxonómico, categoría de manejo, checklist y tipo de coordenada. Los grupos filtran relaciones documentadas, no todas las áreas donde podría vivir una especie. Las provincias y comarcas se obtienen mediante intersección de la geometría del área con la capa oficial Provincias_2024 de MiAMBIENTE. Las columnas provincias, provincia_fuente_url y provincia_metodo documentan el resultado. Puede haber varias regiones por área; los espacios marinos sin intersección terrestre conservan el campo vacío. El cruce usa geometrías simplificadas y no establece límites legales. La propiedad pública o privada no se infiere a partir de la categoría de manejo.

## Preparación de fotografías

Los scripts catalogar_fotos.py y buscar_fotos_gbif.py consultan fuentes por lotes fuera de la navegación. exportar_fotografias.py consolida los resultados y pendientes; después ejecuta init_db.py. No se consultan servicios de imágenes desde Flask. No ejecutar preparar_visuales.py: corresponde a la etapa anterior de ilustraciones y sobrescribiría los registros fotográficos.

El catálogo de especies muestra 24 tarjetas por página y conserva los filtros al navegar. Lugares permite combinar nombre, provincia o comarca, categoría y checklist. Inicio destaca símbolos nacionales, especies endémicas y especies con una historia documentada.

Las fotos no necesitan haberse tomado en Panamá ni dentro de un parque asociado. tipo_visual=fotografia identifica una foto específica; tipo_visual=referencia identifica una referencia. nombre_confirmado conserva el nombre del sujeto fotografiado, que puede diferir del registro cuando la foto es referencial. Una foto no documenta avistamientos ni el lugar de captura.

Cada especie tiene además un respaldo fotográfico local en static/img/referencias/. Si falla la URL principal, se actualizan la imagen, su etiqueta y sus créditos. Las referencias siguen disponibles sin conexión; las fotografías remotas específicas, Leaflet y las teselas necesitan Internet. Los JSON referencias_grupos y referencias_paisajes registran las copias locales y su procedencia. No hay búsquedas de imágenes ni actualizaciones automáticas durante la navegación.

Para consolidar la carga ejecuta `python exportar_fotografias.py` y después `python init_db.py`. Comprueba el resultado con `python comprobar_interfaz.py`, `python comprobar_cobertura_visual.py` y `node comprobar_respaldo.js` (si Node está disponible). No se agregaron dependencias de la aplicación.

## Registros para visitantes

Los datos de observaciones se sirven desde `data/observaciones_gbif.csv`. Para renovar la muestra, instala `requests shapely pyproj` en el entorno de mantenimiento, ejecuta `python importar_observaciones.py` y luego `python init_db.py`. La aplicación solo requiere Flask. Los límites geográficos proceden de la capa oficial y cada observación enlaza a su registro en GBIF. Las selecciones editoriales y lecturas específicas están en los JSON de guía y lecturas de `data/`.
