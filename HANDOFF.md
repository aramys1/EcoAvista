# Continuidad de EcoAvista

## Arquitectura y límites

Flask + sqlite3 + Jinja + Leaflet. Conservar static/css/style.css, componentes y dependencias. Revisar Git y preservar cambios locales. No hacer commit ni push sin instrucción.

Los datos estáticos contienen 3.512 especies, 85 áreas protegidas, registros de inventarios, publicaciones y observaciones públicas con sus fuentes. Los inventarios de cuatro sitios se complementan con publicaciones y observaciones públicas enlazadas a GBIF. Una relación no representa un avistamiento ni permite estimar su probabilidad. Las áreas sin checklist siguen formando parte del catálogo geográfico.

83 coordenadas son centroides aproximados de MiAMBIENTE y dos son referencias de localidad STRI. No señalan entradas ni ubicaciones individuales de especies. Google Maps abre una búsqueda por nombre y categoría del área; el visitante debe comprobar el destino y el acceso.

La conservación nacional corresponde a la Resolución DM-0657-2016; las categorías desconocidas se explican únicamente en las fichas. Los nombres comunes documentados encabezan las fichas y tarjetas.

La cobertura visual es del 100 % para las 3.512 especies y los 85 lugares. Los CSV de imágenes mantienen una fila por registro. Las fotos específicas tienen prioridad; las referencias locales completan los registros restantes. tipo_visual distingue fotografia y referencia. nombre_confirmado identifica el sujeto realmente fotografiado, que puede diferir del registro para referencias. No interpretar estado=verificada como prueba de que una imagen referencial identifica la especie de la ficha o se tomó en el lugar. Fuente, autor y licencia se conservan en ambas clases. El desglose está en data/cobertura_fotografias.json y las referencias se enumeran en data/fotografias_referenciales.csv.

El mapa combina filtros de especie, grupo taxonómico, categoría de manejo, checklist, provincia o comarca y tipo de coordenada. Los grupos filtran relaciones documentadas, no todas las áreas donde podría vivir una especie. Las regiones se derivan del cruce con cartografía oficial; la propiedad pública o privada no se infiere.

## Carga y mantenimiento

`python init_db.py` importa UTF-8, migra la clave triple de especies_lugares y sincroniza los cuatro CSV base y ambos registros de imágenes. `python exportar_fotografias.py` consolida las auditorías de fotos y genera cobertura y pendientes. La investigación es independiente de la navegación. Los procesos por lotes escriben JSONL incrementalmente: exportar e inicializar otra vez para incorporar nuevas verificaciones.

No ejecutar preparar_visuales.py: es un generador anterior de ilustraciones que sobrescribiría los registros fotográficos. La integración activa usa fotos reales, incluidas referencias de grupos y paisajes conforme al nuevo alcance. Las referencias siempre llevan etiqueta y no se presentan como identificaciones exactas. Los archivos originales de la etapa anterior permanecen fuera de la integración activa.

## Ejecutar

```powershell
python init_db.py
python -m flask --app app run
```

http://127.0.0.1:5000. Validar Inicio, Catálogo, fichas de especie y lugar, Lugares, Mapa y Nosotros con el cliente Flask; comprobar 4.984 relaciones y PRAGMA foreign_key_check tras repetir la carga.

## Ampliación geográfica y navegación

completar_provincias.py cruza las 85 geometrías locales con la capa oficial Provincias_2024 mediante consulta espacial, conserva la evidencia en data/provincias_lugares.jsonl y añade provincias, provincia_fuente_url y provincia_metodo a lugares.csv. init_db.py migra e importa estas columnas. Hay áreas marinas sin intersección y áreas con varias regiones. No interpretar el cruce simplificado como delimitación administrativa certificada. No asignar propiedad privada a todo un humedal porque una reserva privada esté dentro.

Lugares filtra por nombre, región, categoría y checklist; Mapa incorpora región. Especies tiene paginación de 24 resultados y enlaces que conservan filtros. Inicio selecciona un representante por grupo con foto. Las búsquedas adicionales de fotos se registran en fotos_inaturalist.jsonl, fotos_wikidata.jsonl y fotos_areas_wikipedia.jsonl; exportar_fotografias.py las consolida.

## Validación de esta ampliación

Se conservaron los campos originales y las coordenadas de los 85 lugares; solo se añadieron columnas geográficas. La carga repetida conserva 4.984 relaciones sin errores de claves foráneas. Se comprobaron las rutas, filtros, paginación y enfoque del mapa. comprobar_cobertura_visual.py comprueba cada registro, sus respaldos locales, archivos cargables, referencias y puntos del mapa. comprobar_respaldo.js simula una URL fallida y verifica que cambien la foto, la etiqueta y la atribución. No se realizó una comprobación visual completa en navegador.

Las fotos no necesitan haberse tomado en Panamá ni en los lugares asociados. static/img/referencias/ contiene las copias locales y data/referencias_grupos.json y data/referencias_paisajes.json mantienen sus créditos. exportar_fotografias.py completa la cobertura con ellas e init_db.py importa los CSV. En el navegador, una URL fallida cambia al respaldo con su etiqueta y créditos. Las fotos remotas específicas y el mapa base requieren Internet; el respaldo fotográfico es local.
