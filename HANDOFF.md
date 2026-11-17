# Contexto de EcoAvista para continuar el trabajo

Este archivo es un traspaso para el siguiente agente. Léelo junto con las instrucciones que entregue el usuario. No es contenido para mostrar dentro de la aplicación.

## Proyecto y alcance

EcoAvista es una aplicación educativa web para consultar especies de flora y fauna de Panamá y explorar lugares relacionados. El recorrido principal es buscar una especie, abrir su ficha, consultar sus lugares relacionados y ver las localidades con coordenadas en el mapa.

El usuario pidió conservar la arquitectura, los datos y la estética existentes, con dependencias mínimas. La app está construida con Python, Flask, `sqlite3`, SQLite, Jinja, HTML, CSS y JavaScript. Leaflet carga desde CDN para el mapa. No rehagas la aplicación ni cambies la navegación por solicitudes limitadas al catálogo de especies.

## Estado del repositorio

- Repositorio local: `C:\Users\Asus Vivobook\OneDrive - Universidad Tecnológica de Panamá\Escritorio\EcoAvista`
- Rama: `main`
- Último commit: `6319b0b Add species filters and conservation details`
- La última revisión mostró el árbol de trabajo limpio y la rama local 4 commits por delante de `origin/main`.
- Los HTML estáticos anteriores fueron retirados porque se sustituyeron por plantillas. Su CSS se conservó en `static/css/style.css`; las páginas antiguas se pueden consultar con `git show <commit>:<archivo>`.
- El archivo `.db` local está excluido de Git.

## Arquitectura y archivos principales

- `app.py`: rutas Flask, consultas parametrizadas, filtros de `/especies` y fichas.
- `init_db.py`: esquema SQLite, importación idempotente de CSV y migración incremental de columnas nuevas en `especies`.
- `data/especies.csv`: registro de especies, grupo biológico, categoría y año UICN, y estado/año/fuente de lista nacional.
- `data/fuentes.csv`: procedencia de taxonomía, evaluaciones UICN y referencia nacional.
- `data/especies_lugares.csv`, `data/lugares.csv`: relaciones y localidades existentes; no deben alterarse para tareas solo de especies.
- `templates/base.html`: navegación compartida y estructura común.
- `templates/especies.html`: catálogo y filtros.
- `templates/especie_detalle.html`: ficha de especie, conservación y relaciones de localidades.
- `static/css/style.css`: estilos del sitio; conserva variables verdes/azules, tarjetas orgánicas, fondos claros y adaptación móvil.
- `requirements.txt`: Flask es la única dependencia Python directa.
- `instance/ecoavista.db`: base local generada por `python init_db.py`; no versionar.

## Trabajo ya realizado

La aplicación inicial tiene Inicio, Catálogo, Ficha de especie, Mapa, Catálogo de lugares, Ficha de lugar y Nosotros. El mapa solo presenta marcadores con coordenadas y atribuye OpenStreetMap. Los checklists se expresan como inclusiones en listas, no como avistamientos confirmados. Los accesos no respaldados aparecen como desconocidos.

El cambio más reciente añadió al catálogo de especies búsqueda más filtros combinables de:

- Categoría: Flora o Fauna.
- Grupo: Aves, Mamíferos, Reptiles, Anfibios, Peces e Invertebrados.
- Categoría global UICN, incluido el filtro separado “Sin dato”.
- Estado independiente en la lista nacional de Panamá: Incluida, No incluida o Sin dato.

Las fichas de especies muestran grupo biológico, categoría UICN con año y fuente, y estado nacional con su referencia y año de evaluación. Solo VU, EN y CR se etiquetan como amenazadas globalmente. El catálogo también muestra el estado y la categoría de forma compacta en las tarjetas. La interfaz conserva los componentes y colores existentes.

`init_db.py` agrega las columnas necesarias a una base creada con el esquema anterior sin eliminar ni cambiar los IDs existentes. La carga posterior actualiza registros por ID y conserva las relaciones.

## Datos de conservación actuales

La carga inicial conserva tres especies, todas de flora:

| ID | Especie | Grupo biológico | UICN global | Año de evaluación | Lista nacional Panamá |
|---|---|---|---|---:|---|
| E001 | *Anacardium excelsum* | Sin dato | LC · Preocupación Menor | 2023 | Sin dato |
| E002 | *Anacardium occidentale* | Sin dato | LC · Preocupación Menor | 2021 | Sin dato |
| E003 | *Spondias mombin* | Sin dato | LC · Preocupación Menor | 2018 | Sin dato |

Hay 8 relaciones especie-lugar y 11 fuentes en la base después de incorporar las nuevas referencias. No se añadió fauna ni se inventaron grupos biológicos o ambientes. Los grupos de fauna están disponibles en el filtro; cada uno muestra un mensaje cuando todavía no hay registros.

La resolución DM-0657-2016 se registró como referencia, pero no se confirmó la inclusión/exclusión individual de los tres taxones en la lista. Por eso el estado y el año de evaluación nacional permanecen `Sin dato`. Mantén la distinción entre esta lista nacional y la Lista Roja global.

Referencias registradas:

- UICN FAQ y categorías: <https://nrl.iucnredlist.org/about/faqs>
- *Anacardium excelsum*, IUCN Red List 2023: <https://doi.org/10.2305/IUCN.UK.2023-1.RLTS.T60761471A167188409.en>
- *Anacardium occidentale*, IUCN Red List 2021: <https://doi.org/10.2305/IUCN.UK.2021-3.RLTS.T60761600A60761604.en>
- *Spondias mombin*, evaluación IUCN 2018 / publicación 2019: <https://doi.org/10.2305/IUCN.UK.2019-2.RLTS.T61984209A149039998.en>
- Resolución N.° DM-0657-2016, Gaceta Oficial de Panamá: <https://www.gacetaoficial.gob.pa/storage/gacetas/2016/12/28187_A/GacetaNo_28187a_20161229.pdf>

## Ejecución local

Ejecuta PowerShell desde la raíz del repositorio. La base se inicializa o migra al correr `init_db.py`.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python init_db.py
python -m flask --app app run
```

Abre <http://127.0.0.1:5000>. El mapa requiere Internet para Leaflet y las teselas de OpenStreetMap. Asegúrate de estar en la carpeta del repositorio antes de ejecutar los comandos; el usuario ya encontró los errores de `requirements.txt` y `init_db.py` al ejecutarlos desde `C:\Users\Asus Vivobook`.

## Validación conocida

Se ejecutó la inicialización de la base con el esquema ampliado y se comprobó que siguen presentes E001–E003, las 8 relaciones y 11 fuentes. No se ejecutó una prueba integral del servidor Flask en este entorno; el usuario debe instalar los requisitos en el entorno virtual ubicado dentro del repositorio.

## Guía para el siguiente agente

1. Revisa `git status` antes de modificar archivos y conserva cambios locales del usuario.
2. Sigue el alcance explícito del último mensaje del usuario; si el cambio es solo de especies, limita el trabajo a catálogo, ficha, fuente/datos y esquema imprescindibles.
3. No inventes categorías, años, fuentes, grupo biológico, fauna ni ambientes. Usa “Sin dato” cuando no exista respaldo verificable.
4. Conserva los IDs de CSV, las relaciones, las consultas SQL parametrizadas y la estética existente.
5. No agregues dependencias si la función se puede realizar con Flask, SQLite, Jinja, CSS o JavaScript ya usados.
6. No hagas push ni borres la base local. Recuerda que la base se genera desde CSV con `python init_db.py`.
