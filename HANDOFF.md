# Contexto de EcoAvista para continuar el trabajo

## Alcance y arquitectura

Aplicación educativa Flask, sqlite3, SQLite, Jinja, HTML, CSS y JavaScript. Leaflet 1.9.4 y teselas OpenStreetMap requieren Internet. Conserva la paleta y los componentes de static/css/style.css. No agregar APIs, actualizaciones automáticas ni dependencias para los datos.

## Datos actuales

Los CSV estáticos contienen 3.507 especies (2.976 flora y 531 fauna), 85 áreas protegidas, 4.984 relaciones de checklist por fuente y 19 fuentes. Hay seis grupos: plantas, aves, anfibios, peces, mamíferos y reptiles. No es un inventario completo de la biodiversidad de Panamá.
Los checklists seleccionados corresponden a Altos de Campana, Soberanía, Barro Colorado y Coiba.
83 coordenadas son centroides aproximados derivados de geometrías oficiales MiAMBIENTE y dos son referencias de localidad publicadas por STRI. Ningún punto representa entrada de parque ni posición individual de especie.
La conservación es nacional, basada en la Resolución DM-0657-2016: los valores vacíos muestran “Sin dato confirmado”. No usar categorías globales UICN ni inferir ausencia de amenaza.
data/imagenes_especies.csv tiene 3.507 filas: dos fotografías verificadas (Anacardium occidentale y Dendrobates auratus) y 3.505 ilustraciones referenciales de seis grupos. Archivos activos en static/img/especies/. Las fotos de especies no documentan avistamientos en Panamá.
data/imagenes_lugares.csv tiene 85 filas: fotografía identificada de Coiba (dronepicr, CC BY 2.0) y 84 mapas de área. Las 85 áreas tienen un mapa propio como respaldo. Geometrías estáticas simplificadas en data/geometrias_lugares.json, EPSG:32617, vinculadas por objectid_1 a id_miambiente y comprobadas por nombre. No usar las miniaturas para navegación o delimitación legal. La capa no declara licencia específica; conservar fuente y atribución.

## Implementación

- init_db.py importa UTF-8 con BOM opcional, migra el esquema y sincroniza los cuatro CSV y el registro de imágenes mediante UPSERT y eliminación de registros ausentes.
- especies_lugares usa clave (id_especie, id_lugar, fuente_id). La migración copia los registros existentes antes de retirar la tabla anterior; la importación restaura las relaciones que la clave antigua colapsaba.
- imagenes_especies e imagenes_lugares usan el ID de su registro como clave; init_db.py valida cobertura completa, rutas locales y sincroniza ambos CSV. Migra el registro antiguo de dos fotos.
- app.py conserva consultas parametrizadas, filtros combinables de nombre, flora/fauna, grupo, estado nacional y lugar. Inicio muestra especies con fotografía verificada.
- visuales.py produce SVG de grupo y de área; preparar_visuales.py regenera archivos y registros visuales sin descargas. templates/_species_visual.html comparte imágenes, etiquetas y créditos. Flask detecta archivos faltantes y ofrece el SVG incrustado. static/js/visuales.js sustituye imágenes fallidas y actualiza su etiqueta y atribución. El respaldo de especie dice “Ilustración referencial”; el de lugar “Mapa del área”.
- /mapa filtra lugares por EXISTS para no duplicar marcadores por fuente; ajusta todos los puntos y conserva lista HTML aun sin Leaflet o teselas. Verde: centroide; azul: STRI. No hay filtro de acceso.
- /lugares distingue áreas con checklist de las demás mediante conteo de especies distintas.

## Ejecución

Desde la raíz del repositorio, activa .venv y ejecuta:
```powershell
python init_db.py
python -m flask --app app run
```
Abre http://127.0.0.1:5000. La base instance/ecoavista.db se genera localmente y no se versiona.
Revisa git status antes de editar, conserva cambios locales, no hagas push ni borres la base. Los cambios del usuario en lugares.csv y fuentes.csv se conservaron.

## Comprobación

Se repitió init_db.py: 3.507 especies, 85 lugares, 4.984 relaciones, 19 fuentes, 3.507 registros visuales de especies y 85 de lugares; sin errores de claves foráneas. Se comprobó cobertura completa de ambos registros y los 94 archivos activos distintos (tres JPEG, seis SVG de grupo y 85 SVG de área), incluyendo los respaldos. El cliente Flask confirmó respuestas 200 de Inicio, Catálogo, fichas con fotos y referencias, Lugares, Mapa y Nosotros, con 3.507 imágenes en el catálogo y 85 en Lugares. Se simuló la ausencia de archivos locales para comprobar el respaldo SVG incrustado. No se realizó revisión visual de las páginas en navegador. El mapa interactivo conserva 85 puntos (83 centroides) y depende de Internet para Leaflet y teselas; los recursos visuales y sus respaldos son locales.
