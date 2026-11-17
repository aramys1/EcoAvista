import sqlite3

from flask import Flask, abort, g, render_template, request, url_for

from init_db import DB_PATH


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
    if search:
        clauses.append("(nombre_comun_es LIKE ? OR nombre_cientifico LIKE ?)")
        pattern = f"%{search}%"
        parameters.extend([pattern, pattern])
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
    sql += " ORDER BY nombre_comun_es, nombre_cientifico"
    rows = get_db().execute(sql, parameters).fetchall()
    return [dict(row) for row in rows]


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


@app.route("/")
def index():
    database = get_db()
    species = database.execute(
        "SELECT * FROM especies ORDER BY nombre_comun_es LIMIT 3"
    ).fetchall()
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
    group_counts = species_filter_counts()
    places = get_db().execute("SELECT id, nombre FROM lugares ORDER BY nombre").fetchall()
    return render_template(
        "especies.html",
        species=species,
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
        unlocated=[place for place in locations if place["latitud"] is None or place["longitud"] is None],
    )


@app.route("/mapa")
def map_page():
    database = get_db()
    species = database.execute("SELECT id, nombre_comun_es, nombre_cientifico FROM especies ORDER BY nombre_comun_es").fetchall()
    species_id = request.args.get("especie", "").strip()
    access = request.args.get("acceso", "").strip().lower()
    clauses = ["l.latitud IS NOT NULL", "l.longitud IS NOT NULL"]
    parameters = []
    if species_id:
        clauses.append("EXISTS (SELECT 1 FROM especies_lugares el WHERE el.id_lugar=l.id AND el.id_especie=?)")
        parameters.append(species_id)
    places = database.execute(
        "SELECT l.* FROM lugares l WHERE " + " AND ".join(clauses) + " ORDER BY l.nombre",
        parameters,
    ).fetchall()
    if access in {"confirmado", "desconocido"}:
        # No access field is present in this initial source data, so every place is unknown.
        places = places if access == "desconocido" else []
    unlocated = []
    if species_id:
        unlocated = database.execute(
            "SELECT l.id,l.nombre FROM especies_lugares el JOIN lugares l ON l.id=el.id_lugar "
            "WHERE el.id_especie=? AND (l.latitud IS NULL OR l.longitud IS NULL) ORDER BY l.nombre",
            (species_id,),
        ).fetchall()
    selected_species = next((row for row in species if row["id"] == species_id), None)
    return render_template(
        "mapa.html",
        species=species,
        selected_species=species_id,
        selected_access=access,
        places=places,
        unlocated=unlocated,
        map_points=[{"lat": row["latitud"], "lng": row["longitud"], "name": row["nombre"], "url": url_for("place_detail", place_id=row["id"])} for row in places],
        selected_species_name=selected_species["nombre_comun_es"] if selected_species else None,
    )


@app.route("/lugares")
def places_catalog():
    access = request.args.get("acceso", "").strip().lower()
    database = get_db()
    places = database.execute("SELECT * FROM lugares ORDER BY nombre").fetchall()
    if access == "confirmado":
        places = []
    return render_template("lugares.html", places=places, access=access)


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
        "LEFT JOIN fuentes f ON f.id=el.fuente_id WHERE el.id_lugar=? ORDER BY s.nombre_comun_es",
        (place_id,),
    ).fetchall()
    return render_template("lugar_detalle.html", place=place, species=species)


@app.route("/nosotros")
def about():
    return render_template("nosotros.html", sources=get_sources())


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
