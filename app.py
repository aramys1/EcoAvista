import sqlite3

from flask import Flask, abort, g, render_template, request, url_for

from init_db import DB_PATH


app = Flask(__name__)
app.config["DATABASE"] = DB_PATH
SPECIES_GROUPS = {
    "aves": "Aves",
    "mamiferos": "Mamíferos",
    "reptiles": "Reptiles",
    "anfibios": "Anfibios",
    "peces": "Peces",
    "invertebrados": "Invertebrados",
}
IUCN_LABELS = {
    "EX": "Extinta",
    "EW": "Extinta en Estado Silvestre",
    "CR": "En Peligro Crítico",
    "EN": "En Peligro",
    "VU": "Vulnerable",
    "NT": "Casi Amenazada",
    "LC": "Preocupación Menor",
    "DD": "Datos Insuficientes",
    "NE": "No Evaluada",
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


def category_name(taxon):
    return "Flora" if taxon == "Planta" else "Fauna"


def species_query(search, category, group, iucn_category, national_status):
    clauses = []
    parameters = []
    if search:
        clauses.append("(nombre_comun_es LIKE ? OR nombre_cientifico LIKE ?)")
        pattern = f"%{search}%"
        parameters.extend([pattern, pattern])
    if category in {"flora", "fauna"}:
        clauses.append("LOWER(grupo_taxonomico) = ?")
        parameters.append("planta" if category == "flora" else "fauna")
    if group in SPECIES_GROUPS:
        clauses.append("grupo_biologico = ?")
        parameters.append(group)
    if iucn_category in {*IUCN_LABELS, "sin_dato"}:
        if iucn_category == "sin_dato":
            clauses.append("iucn_categoria IS NULL")
        else:
            clauses.append("iucn_categoria = ?")
            parameters.append(iucn_category)
    if national_status in {"incluida", "no_incluida", "sin_dato"}:
        national_value = {
            "incluida": "Incluida",
            "no_incluida": "No incluida",
            "sin_dato": "Sin dato",
        }[national_status]
        clauses.append("estado_lista_panama = ?")
        parameters.append(national_value)
    sql = "SELECT * FROM especies"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY nombre_comun_es, nombre_cientifico"
    rows = get_db().execute(sql, parameters).fetchall()
    return [dict(row, categoria=category_name(row["grupo_taxonomico"])) for row in rows]


def species_filter_counts():
    counts = {key: 0 for key in SPECIES_GROUPS}
    counts.update(
        {
            row["grupo_biologico"]: row["cantidad"]
            for row in get_db().execute(
                "SELECT grupo_biologico, COUNT(*) AS cantidad FROM especies "
                "WHERE grupo_biologico IS NOT NULL GROUP BY grupo_biologico"
            )
        }
    )
    return counts


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
            "SELECT COUNT(*) FROM especies WHERE LOWER(grupo_taxonomico)='planta'"
        ).fetchone()[0],
        "fauna": database.execute(
            "SELECT COUNT(*) FROM especies WHERE LOWER(grupo_taxonomico)='fauna'"
        ).fetchone()[0],
    }
    return render_template("index.html", species=species, counts=counts)


@app.route("/especies")
def species_catalog():
    search = request.args.get("q", "").strip()
    category = request.args.get("categoria", "").strip().lower()
    group = request.args.get("grupo", "").strip().lower()
    iucn_category = request.args.get("iucn", "").strip().lower()
    if iucn_category != "sin_dato":
        iucn_category = iucn_category.upper()
    national_status = request.args.get("lista_panama", "").strip().lower()
    species = species_query(search, category, group, iucn_category, national_status)
    group_counts = species_filter_counts()
    return render_template(
        "especies.html",
        species=species,
        query=search,
        category=category,
        group=group,
        group_counts=group_counts,
        group_labels=SPECIES_GROUPS,
        iucn_category=iucn_category.lower(),
        national_status=national_status,
        fauna_empty=category == "fauna" and not species,
        group_empty=group in SPECIES_GROUPS and group_counts[group] == 0,
    )


@app.route("/especies/<species_id>")
def species_detail(species_id):
    database = get_db()
    species = database.execute(
        "SELECT s.*, f.titulo AS fuente_titulo, f.url AS fuente_url, "
        "f.nota_metodologica AS fuente_nota, fi.titulo AS fuente_iucn_titulo, "
        "fi.url AS fuente_iucn_url, fp.titulo AS fuente_panama_titulo, "
        "fp.url AS fuente_panama_url FROM especies s "
        "LEFT JOIN fuentes f ON f.id=s.fuente_taxonomia_id "
        "LEFT JOIN fuentes fi ON fi.id=s.fuente_iucn_id "
        "LEFT JOIN fuentes fp ON fp.id=s.fuente_lista_panama_id WHERE s.id=?",
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
        category=category_name(species["grupo_taxonomico"]),
        group_label=SPECIES_GROUPS.get(species["grupo_biologico"], "Sin dato"),
        iucn_label=IUCN_LABELS.get(species["iucn_categoria"], "Sin dato"),
        iucn_threatened=species["iucn_categoria"] in {"VU", "EN", "CR"},
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
        "SELECT s.id,s.nombre_comun_es,s.nombre_cientifico,s.grupo_taxonomico, "
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
