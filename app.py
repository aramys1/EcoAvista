import sqlite3
import unicodedata
from difflib import SequenceMatcher, get_close_matches
import json
from urllib.parse import urlencode

from flask import Flask, abort, g, render_template, request, url_for

from init_db import DB_PATH, ROOT


app = Flask(__name__)
app.config["DATABASE"] = DB_PATH
SPECIES_GROUPS = {
    "plantas": "Plantas",
    "aves": "Aves",
    "anfibios": "Anfibios",
    "peces": "Peces",
    "mamiferos": "Mamíferos",
    "reptiles": "Reptiles",
}
NATIONAL_CATEGORIES = {
    "cr": "CR",
    "en": "EN",
    "vu": "VU",
}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.create_function("normalizar", 1, normalize, deterministic=True)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def token_match(column):
    return (
        "(',' || replace(replace(coalesce(" + column
        + ", ''), '; ', ';'), ';', ',') || ',') LIKE ? COLLATE NOCASE"
    )


def species_query(search, category, group, national_category, place_id):
    clauses = []
    parameters = []
    if category in {"flora", "fauna"}:
        clauses.append(token_match("categoria"))
        parameters.append(f"%,{category.title()},%")
    if group in SPECIES_GROUPS:
        clauses.append(token_match("grupo_taxonomico"))
        parameters.append(f"%,{SPECIES_GROUPS[group]},%")
    if national_category in NATIONAL_CATEGORIES:
        clauses.append(token_match("estado_conservacion_panama"))
        parameters.append(f"%,{NATIONAL_CATEGORIES[national_category]},%")
    if place_id:
        clauses.append(
            "EXISTS (SELECT 1 FROM especies_lugares el "
            "WHERE el.id_especie=especies.id AND el.id_lugar=?)"
        )
        parameters.append(place_id)
    sql = "SELECT * FROM especies"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY nombre_cientifico"
    rows = get_db().execute(sql, parameters).fetchall()
    rows = [dict(row) for row in rows]
    if request.args.get("origen") == "endemicas":
        rows = [row for row in rows if GUIDE.get(row["id"], {}).get("endemica")]
    query = normalize(search)
    if not query:
        return rows
    exact, nearby = [], []
    for row in rows:
        key = row["id"]
        names = [row["nombre_comun_es"], row["nombre_cientifico"],
                 *GUIDE.get(key, {}).get("aliases", []), *READINGS.get(key, {}).get("aliases", [])]
        names = [normalize(n) for n in names if n]
        if any(query in n for n in names):
            exact.append(row)
        elif 4 <= len(query) <= 80:
            score = max(SequenceMatcher(None, query, n).ratio() for n in names)
            if score >= .83:
                nearby.append((score, row))
    if exact:
        return exact
    g.approximate = bool(nearby)
    return [row for _, row in sorted(nearby, key=lambda pair: -pair[0])]


def normalize(text):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                            if not unicodedata.combining(c)).split())


GUIDE = json.loads((ROOT / "data/guia_especies.json").read_text(encoding="utf-8"))
READINGS = json.loads((ROOT / "data/lecturas_especies.json").read_text(encoding="utf-8"))
PLACE_FIELD_PHOTOS = json.loads((ROOT / "data/fotos_de_campo.json").read_text(encoding="utf-8"))
PLACE_LAWS = json.loads((ROOT / "data/normas_lugares.json").read_text(encoding="utf-8"))
PLACE_GUIDE = json.loads((ROOT / "data/guia_lugares.json").read_text(encoding="utf-8"))
STATUS = {"CR": "En peligro crítico", "EN": "En peligro", "VU": "Vulnerable"}
app.jinja_env.globals.update(guide=GUIDE, status_label=STATUS, readings=READINGS)


def species_filter_counts():
    return {
        key: get_db().execute(
            "SELECT COUNT(*) FROM especies WHERE " + token_match("grupo_taxonomico"),
            (f"%,{label},%",),
        ).fetchone()[0]
        for key, label in SPECIES_GROUPS.items()
    }


def get_sources():
    return get_db().execute("SELECT * FROM fuentes ORDER BY id").fetchall()


def province_options():
    return sorted({name for row in get_db().execute("SELECT provincias FROM lugares") for name in (row[0] or '').split(';') if name})


def page_link(page):
    params = request.args.to_dict()
    params['pagina'] = page
    return url_for(request.endpoint, **params)


app.jinja_env.globals['page_link'] = page_link


@app.context_processor
def image_registry():
    if "registries" in g:
        return g.registries
    registries = []
    group_references = json.loads((ROOT / 'data/referencias_grupos.json').read_text(encoding='utf-8'))
    species_groups = {row[0]:row[1].split(';')[0].strip() for row in get_db().execute('SELECT id, grupo_taxonomico FROM especies')}
    local_files = {}

    def local_file_exists(filename):
        if filename not in local_files:
            local_files[filename] = (ROOT/'static'/filename).is_file()
        return local_files[filename]
    for table, key in [("imagenes_especies", "id_especie"), ("imagenes_lugares", "id_lugar")]:
        registry = {}
        for row in get_db().execute(f"SELECT * FROM {table}"):
            image = dict(row)
            image["src"] = None
            if image["estado"] == "verificada":
                path = image["archivo"]
                image["src"] = url_for("static", filename=path) if path and local_file_exists(path) else image["imagen_url"]
            image['backup'] = None
            image['reference_label'] = 'Imagen referencial'
            reference = None
            image['view_label'] = (image['nota'] or '').split(' · ')[0] if (image['nota'] or '').startswith(('Vista satelital', 'Vista orbital')) else None
            if table == 'imagenes_especies':
                group = species_groups[row[key]]
                reference = group_references.get(group)
                image['reference_label'] = 'Imagen referencial del grupo · ' + group
            if reference:
                backup_path = reference['archivo']
                if local_file_exists(backup_path):
                    image['backup'] = {**reference, 'src':url_for('static',filename=backup_path), 'tipo_visual':'referencia', 'reference_label':image['reference_label']}
            registry[row[key]] = image
        registries.append(registry)
    g.registries = {"images": registries[0], "place_images": registries[1]}
    return g.registries


def coordinate_type(place):
    if place["latitud"] is None or place["longitud"] is None:
        return "Sin coordenadas"
    if place["fuente_coordenada_id"] == "F01":
        return "Centroide aproximado · MiAMBIENTE"
    return "Referencia de localidad · STRI"


app.jinja_env.globals["coordinate_type"] = coordinate_type
app.jinja_env.globals["google_maps"] = lambda place: "https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": place["nombre"] + " Panamá " + (place["categoria_manejo"] or "")})


@app.route("/")
def index():
    database = get_db()
    species = [database.execute("SELECT * FROM especies WHERE id=?", (key,)).fetchone() for key in GUIDE]
    counts = {
        "especies": database.execute("SELECT COUNT(*) FROM especies").fetchone()[0],
        "lugares": database.execute("SELECT COUNT(*) FROM lugares").fetchone()[0],
        "flora": database.execute(
            "SELECT COUNT(*) FROM especies WHERE categoria='Flora'"
        ).fetchone()[0],
        "fauna": database.execute(
            "SELECT COUNT(*) FROM especies WHERE categoria='Fauna'"
        ).fetchone()[0],
    }
    return render_template("index.html", species=species, counts=counts)


@app.route("/especies")
def species_catalog():
    search = request.args.get("q", "").strip()
    category = request.args.get("categoria", "").strip().lower()
    group = request.args.get("grupo", "").strip().lower()
    national_category = request.args.get("estado", "").strip().lower()
    place_id = request.args.get("lugar", "").strip()
    species = species_query(search, category, group, national_category, place_id)
    total = len(species)
    pages = max(1, (total + 23) // 24)
    page = max(1, min(request.args.get('pagina', 1, type=int), pages))
    species = species[(page - 1) * 24:page * 24]
    group_counts = species_filter_counts()
    places = get_db().execute("SELECT id, nombre FROM lugares WHERE EXISTS (SELECT 1 FROM especies_lugares el WHERE el.id_lugar=lugares.id) ORDER BY nombre").fetchall()
    return render_template(
        "especies.html",
        species=species,
        total=total, page=page, pages=pages,
        query=search,
        category=category,
        group=group,
        group_counts=group_counts,
        group_labels=SPECIES_GROUPS,
        national_category=national_category,
        places=places,
        place_id=place_id,
    )


@app.route("/especies/<species_id>")
def species_detail(species_id):
    database = get_db()
    species = database.execute(
        "SELECT s.*, ft.titulo AS fuente_taxonomia_titulo, ft.url AS fuente_taxonomia_url, "
        "ft.nota_metodologica AS fuente_taxonomia_nota, "
        "fn.titulo AS fuente_nombre_comun_titulo, fn.url AS fuente_nombre_comun_url, "
        "fe.titulo AS fuente_estado_titulo, fe.url AS fuente_estado_url, "
        "fe.nota_metodologica AS fuente_estado_nota, "
        "fr.titulo AS fuente_resolucion_titulo, fr.url AS fuente_resolucion_url "
        "FROM especies s "
        "LEFT JOIN fuentes ft ON ft.id=s.fuente_taxonomia_id "
        "LEFT JOIN fuentes fn ON fn.id=s.fuente_nombre_comun_id "
        "LEFT JOIN fuentes fe ON fe.id=s.fuente_estado_panama_id "
        "LEFT JOIN fuentes fr ON fr.id='F19' WHERE s.id=?",
        (species_id,),
    ).fetchone()
    if species is None:
        abort(404)
    locations = database.execute(
        "SELECT l.*, el.tipo_relacion, el.nota AS nota_relacion, "
        "f.titulo AS fuente_titulo, f.url AS fuente_url "
        "FROM especies_lugares el JOIN lugares l ON l.id=el.id_lugar "
        "LEFT JOIN fuentes f ON f.id=el.fuente_id "
        "WHERE el.id_especie=? ORDER BY l.nombre",
        (species_id,),
    ).fetchall()
    return render_template(
        "especie_detalle.html",
        species=species,
        category=species["categoria"] or "Sin dato",
        locations=locations,
        guide_source=database.execute("SELECT * FROM fuentes WHERE id=?", (GUIDE.get(species_id, {}).get("fuente"),)).fetchone(),
        unlocated=[place for place in locations if place["latitud"] is None or place["longitud"] is None],
    )


def map_matches(query):
    """Find map destinations, keeping exact, partial and suggested names distinct."""
    needle = normalize(query)
    if not needle:
        return [], False
    entries = []
    names = {}

    def add(kind, key, label, detail, aliases):
        index = len(entries)
        entries.append(dict(kind=kind, key=key, label=label, detail=detail))
        for alias in {normalize(value) for value in [label, *aliases] if value}:
            names.setdefault(alias, []).append(index)

    for place in get_db().execute("SELECT id, nombre, categoria_manejo FROM lugares ORDER BY nombre"):
        add("area", place["id"], place["nombre"], place["categoria_manejo"],
            [f"{place['categoria_manejo']} {place['nombre']}"])
    for province in province_options():
        add("provincia", province, province, "Provincia o comarca", [])
    for row in get_db().execute("SELECT id, nombre_comun_es, nombre_cientifico FROM especies ORDER BY nombre_cientifico"):
        key, common, scientific = row
        aliases = [scientific, *GUIDE.get(key, {}).get("aliases", []), *READINGS.get(key, {}).get("aliases", [])]
        add("especie", key, common or scientific, "Especie" + (" · " + scientific if common else ""), aliases)

    hits = [name for name in names if needle in name]
    hits.sort(key=lambda name: (name != needle, not name.startswith(needle), len(name), name))
    approximate = not hits and len(needle) >= 3
    if approximate:
        hits = get_close_matches(needle, names, n=5, cutoff=.78)
    indexes = dict.fromkeys(index for name in hits for index in names[name])
    return [entries[index] for index in indexes], bool(approximate and hits)


@app.get("/mapa/sugerencias")
def map_suggestions():
    query = request.args.get("q", "").strip()[:100]
    matches, approximate = map_matches(query) if len(query) >= 2 else ([], False)
    return {"approximate": approximate, "items": [
        {"label": item["label"], "detail": item["detail"],
         "url": url_for("map_page", **{item["kind"]: item["key"]}, _anchor="explorar")}
        for item in matches[:7]
    ]}


@app.route("/mapa")
def map_page():
    database = get_db()
    species = database.execute("SELECT id, nombre_comun_es, nombre_cientifico FROM especies WHERE id IN (SELECT id_especie FROM especies_lugares) ORDER BY nombre_comun_es IS NULL, nombre_comun_es, nombre_cientifico").fetchall()
    species_id = request.args.get("especie", "").strip()
    clauses = ["1=1"]
    parameters = []
    group = request.args.get("grupo", "")
    management = request.args.get("manejo", "")
    checklist = request.args.get("checklist", "")
    coordinate = request.args.get("coordenada", "")
    area = request.args.get('area', '')
    query = request.args.get("q", "").strip()[:100]
    matches, approximate = map_matches(query)
    if query:
        area_ids = {item["key"] for item in matches if item["kind"] == "area"}
        regions = {item["key"] for item in matches if item["kind"] == "provincia"}
        if regions:
            for row in database.execute("SELECT id, provincias FROM lugares"):
                if regions.intersection((row["provincias"] or "").split(";")):
                    area_ids.add(row["id"])
        species_ids = {item["key"] for item in matches if item["kind"] == "especie"}
        if species_ids:
            area_ids.update(row[0] for row in database.execute(
                "SELECT DISTINCT id_lugar FROM especies_lugares WHERE id_especie IN (SELECT value FROM json_each(?))",
                (json.dumps(sorted(species_ids)),)))
        clauses.append("l.id IN (SELECT value FROM json_each(?))")
        parameters.append(json.dumps(sorted(area_ids)))
    if area:
        clauses.append('l.id=?')
        parameters.append(area)
    province = request.args.get('provincia', '')
    if province:
        clauses.append(token_match('l.provincias'))
        parameters.append(f'%,{province},%')
    if group in SPECIES_GROUPS:
        clauses.append("EXISTS (SELECT 1 FROM especies_lugares el JOIN especies s ON s.id=el.id_especie WHERE el.id_lugar=l.id AND " + token_match("s.grupo_taxonomico") + ")")
        parameters.append(f"%,{SPECIES_GROUPS[group]},%")
    if management:
        clauses.append("l.categoria_manejo=?")
        parameters.append(management)
    if checklist in {"si", "no"}:
        clauses.append(("" if checklist == "si" else "NOT ") + "EXISTS (SELECT 1 FROM especies_lugares el WHERE el.id_lugar=l.id)")
    if coordinate in {"centroide", "referencia"}:
        clauses.append("l.fuente_coordenada_id " + ("=" if coordinate == "centroide" else "!=") + " 'F01'")
    if species_id:
        clauses.append("EXISTS (SELECT 1 FROM especies_lugares el WHERE el.id_lugar=l.id AND el.id_especie=?)")
        parameters.append(species_id)
    related_places = database.execute(
        "SELECT l.*, (SELECT COUNT(DISTINCT el.id_especie) FROM especies_lugares el WHERE el.id_lugar=l.id) AS species_count FROM lugares l WHERE " + " AND ".join(clauses) + " ORDER BY l.nombre",
        parameters,
    ).fetchall()
    places = [row for row in related_places if row["latitud"] is not None and row["longitud"] is not None]
    unlocated = [row for row in related_places if row["latitud"] is None or row["longitud"] is None]
    selected_species = database.execute("SELECT nombre_comun_es, nombre_cientifico FROM especies WHERE id=?", (species_id,)).fetchone() if species_id else None
    photos = image_registry()["place_images"]
    return render_template(
        "mapa.html",
        query=query, approximate=approximate, search_matches=matches,
        group=group, group_labels=SPECIES_GROUPS, management=management, checklist=checklist, coordinate=coordinate,
        province=province, provinces=province_options(), area=area,
        managements=[row[0] for row in database.execute("SELECT DISTINCT categoria_manejo FROM lugares ORDER BY categoria_manejo")],
        species=species,
        selected_species=species_id,
        places=places,
        related_places=related_places,
        unlocated=unlocated,
        map_points=[{"lat": row["latitud"], "lng": row["longitud"], "name": row["nombre"], "category": row["categoria_manejo"], "count": row["species_count"], "image": photos.get(row["id"], {}).get("src"), "backup": photos.get(row["id"], {}).get("backup"), "reference": photos.get(row["id"], {}).get("tipo_visual") == "referencia", "maps": app.jinja_env.globals["google_maps"](row), "viewLabel": photos.get(row["id"], {}).get("view_label"), "coordinateType": coordinate_type(row), "centroid": row["fuente_coordenada_id"] == "F01", "url": url_for("place_detail", place_id=row["id"])} for row in places],
        selected_species_name=(selected_species["nombre_comun_es"] or selected_species["nombre_cientifico"]) if selected_species else None,
    )


@app.route("/lugares")
def places_catalog():
    database = get_db()
    query = request.args.get('q', '').strip()
    province = request.args.get('provincia', '')
    management = request.args.get('manejo', '')
    checklist = request.args.get('checklist', '')
    clauses = ['1=1']
    parameters = []
    if query:
        clauses.append('normalizar(l.nombre) LIKE ?')
        parameters.append('%' + normalize(query) + '%')
    if province:
        clauses.append(token_match('l.provincias'))
        parameters.append(f'%,{province},%')
    if management:
        clauses.append('l.categoria_manejo=?')
        parameters.append(management)
    if checklist == 'si':
        clauses.append('EXISTS (SELECT 1 FROM especies_lugares el WHERE el.id_lugar=l.id)')
    places = database.execute(
        "SELECT l.*, (SELECT COUNT(DISTINCT el.id_especie) FROM especies_lugares el "
        "WHERE el.id_lugar=l.id) AS species_count FROM lugares l WHERE " + ' AND '.join(clauses) + " ORDER BY nombre", parameters
    ).fetchall()
    return render_template("lugares.html", places=places, checklist_count=sum(row["species_count"] > 0 for row in places), query=query, province=province, provinces=province_options(), management=management, checklist=checklist, managements=[row[0] for row in database.execute('SELECT DISTINCT categoria_manejo FROM lugares ORDER BY categoria_manejo')])


@app.route("/lugares/<place_id>")
def place_detail(place_id):
    database = get_db()
    place = database.execute(
        "SELECT l.*, fa.titulo AS area_fuente_titulo, fa.url AS area_fuente_url, "
        "fa.nota_metodologica AS area_fuente_nota, fc.titulo AS coord_fuente_titulo, "
        "fc.url AS coord_fuente_url, fc.nota_metodologica AS coord_fuente_nota "
        "FROM lugares l LEFT JOIN fuentes fa ON fa.id=l.fuente_area_id "
        "LEFT JOIN fuentes fc ON fc.id=l.fuente_coordenada_id WHERE l.id=?",
        (place_id,),
    ).fetchone()
    if place is None:
        abort(404)
    species = database.execute(
        "SELECT s.id,s.nombre_comun_es,s.nombre_cientifico,s.categoria,s.grupo_taxonomico, "
        "el.tipo_relacion,el.nota AS nota_relacion,f.titulo AS fuente_titulo,f.url AS fuente_url "
        "FROM especies_lugares el JOIN especies s ON s.id=el.id_especie "
        "LEFT JOIN fuentes f ON f.id=el.fuente_id WHERE el.id_lugar=? ORDER BY (s.nombre_comun_es IS NULL), s.nombre_comun_es, s.nombre_cientifico",
        (place_id,),
    ).fetchall()
    return render_template("lugar_detalle.html", place=place, species=species,
                           field_photo=PLACE_FIELD_PHOTOS.get(place_id),
                           marco_legal=database.execute("SELECT titulo,url FROM fuentes WHERE id='F40'").fetchone(),
                           leyes=PLACE_LAWS.get(place_id, []),
                           intro=PLACE_GUIDE.get(place_id, (None, None))[0],
                           local_source=database.execute("SELECT * FROM fuentes WHERE id=?", (PLACE_GUIDE.get(place_id, (None, None))[1],)).fetchone())


@app.route("/nosotros")
def about():
    return render_template("nosotros.html", sources=get_sources())


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
