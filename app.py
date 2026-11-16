import sqlite3

from flask import Flask, abort, g, render_template, request, url_for

from init_db import DB_PATH


app = Flask(__name__)
app.config["DATABASE"] = DB_PATH


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


def species_query():
    search = request.args.get("q", "").strip()
    category = request.args.get("categoria", "").strip().lower()
    clauses = []
    parameters = []
    if search:
        clauses.append("(nombre_comun_es LIKE ? OR nombre_cientifico LIKE ?)")
        pattern = f"%{search}%"
        parameters.extend([pattern, pattern])
    if category in {"flora", "fauna"}:
        clauses.append("LOWER(grupo_taxonomico) = ?")
        parameters.append("planta" if category == "flora" else "fauna")
    sql = "SELECT * FROM especies"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY nombre_comun_es, nombre_cientifico"
    rows = get_db().execute(sql, parameters).fetchall()
    return [dict(row, categoria=category_name(row["grupo_taxonomico"])) for row in rows]


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
    species = species_query()
    return render_template(
        "especies.html",
        species=species,
        query=request.args.get("q", "").strip(),
        category=request.args.get("categoria", ""),
        fauna_empty=request.args.get("categoria", "").lower() == "fauna" and not species,
    )


@app.route("/especies/<species_id>")
def species_detail(species_id):
    database = get_db()
    species = database.execute(
        "SELECT s.*, f.titulo AS fuente_titulo, f.url AS fuente_url, "
        "f.nota_metodologica AS fuente_nota FROM especies s "
        "LEFT JOIN fuentes f ON f.id=s.fuente_taxonomia_id WHERE s.id=?",
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
