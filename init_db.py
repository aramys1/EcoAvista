import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "instance" / "ecoavista.db"
DATA_PATH = ROOT / "data"


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS fuentes (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    organizacion TEXT,
    tipo TEXT,
    url TEXT,
    fecha_consulta TEXT,
    nota_metodologica TEXT
);
CREATE TABLE IF NOT EXISTS especies (
    id TEXT PRIMARY KEY,
    nombre_cientifico TEXT NOT NULL,
    nombre_comun_es TEXT,
    categoria TEXT,
    grupo_taxonomico TEXT,
    familia TEXT,
    rango_taxonomico TEXT,
    estado_conservacion_panama TEXT,
    fuente_taxonomia_id TEXT REFERENCES fuentes(id),
    fuente_nombre_comun_id TEXT REFERENCES fuentes(id),
    fuente_estado_panama_id TEXT REFERENCES fuentes(id)
);
CREATE TABLE IF NOT EXISTS lugares (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    nombre_en_checklist TEXT,
    categoria_manejo TEXT,
    latitud REAL,
    longitud REAL,
    precision_ubicacion TEXT,
    fuente_area_id TEXT REFERENCES fuentes(id),
    fuente_coordenada_id TEXT REFERENCES fuentes(id),
    id_miambiente TEXT
);
CREATE TABLE IF NOT EXISTS especies_lugares (
    id_especie TEXT NOT NULL REFERENCES especies(id) ON DELETE CASCADE,
    id_lugar TEXT NOT NULL REFERENCES lugares(id) ON DELETE CASCADE,
    tipo_relacion TEXT,
    fuente_id TEXT REFERENCES fuentes(id),
    taxon_id_stri TEXT,
    nota TEXT,
    PRIMARY KEY (id_especie, id_lugar, fuente_id)
);
CREATE TABLE IF NOT EXISTS imagenes_especies (
    id_especie TEXT PRIMARY KEY REFERENCES especies(id) ON DELETE CASCADE,
    nombre_cientifico TEXT NOT NULL,
    nombre_confirmado TEXT,
    imagen_url TEXT,
    archivo TEXT,
    estado TEXT NOT NULL CHECK (estado IN ('verificada', 'pendiente')),
    fuente_url TEXT,
    autor TEXT,
    licencia TEXT,
    licencia_url TEXT,
    nota TEXT,
    fecha_verificacion TEXT
);
CREATE TABLE IF NOT EXISTS imagenes_lugares (
    id_lugar TEXT PRIMARY KEY REFERENCES lugares(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    nombre_confirmado TEXT,
    imagen_url TEXT,
    archivo TEXT,
    estado TEXT NOT NULL CHECK (estado IN ('verificada', 'pendiente')),
    fuente_url TEXT,
    autor TEXT,
    licencia TEXT,
    licencia_url TEXT,
    nota TEXT,
    fecha_verificacion TEXT
);
"""

TABLE_MIGRATIONS = {
    "imagenes_especies": {"tipo_visual": "TEXT"},
    "imagenes_lugares": {"tipo_visual": "TEXT"},
    "especies": {
        "categoria": "TEXT",
        "rango_taxonomico": "TEXT",
        "estado_conservacion_panama": "TEXT",
        "fuente_nombre_comun_id": "TEXT REFERENCES fuentes(id)",
        "fuente_estado_panama_id": "TEXT REFERENCES fuentes(id)",
    },
    "lugares": {"id_miambiente": "TEXT", "provincias": "TEXT", "provincia_fuente_url": "TEXT", "provincia_metodo": "TEXT"},
    "especies_lugares": {"taxon_id_stri": "TEXT"},
}


def read_csv(filename):
    with (DATA_PATH / filename).open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def value(row, key):
    raw = (row.get(key) or "").strip()
    return raw or None


def import_rows(connection, table, columns, rows, id_columns):
    key_columns = [id_columns] if isinstance(id_columns, str) else id_columns
    names = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(
        f"{column}=excluded.{column}" for column in columns if column not in key_columns
    )
    query = (
        f"INSERT INTO {table} ({names}) VALUES ({placeholders}) "
        f"ON CONFLICT({', '.join(key_columns)}) DO UPDATE SET {updates}"
    )
    connection.executemany(
        query,
        [tuple(value(row, column) for column in columns) for row in rows],
    )


def migrate_tables(connection):
    for table, key, name in [("imagenes_especies", "id_especie", "nombre_cientifico"), ("imagenes_lugares", "id_lugar", "nombre")]:
        existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        if "estado" not in existing:
            connection.execute(f"ALTER TABLE {table} RENAME TO {table}_anterior")
            statement = SCHEMA.split(f"CREATE TABLE IF NOT EXISTS {table} (")[1].split(";")[0]
            connection.execute(f"CREATE TABLE {table} (" + statement)
            source = "fuente_url" if "fuente_url" in existing else "fuente"
            connection.execute(
                f"INSERT INTO {table} ({key}, {name}, estado, fuente_url, autor, licencia, licencia_url, nota) "
                f"SELECT {key}, {name}, 'pendiente', {source}, autor, licencia, licencia_url, nota FROM {table}_anterior"
            )
            connection.execute(f"DROP TABLE {table}_anterior")
    for table, migrations in TABLE_MIGRATIONS.items():
        existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        for column, definition in migrations.items():
            if column not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    primary_key = [
        row[1] for row in sorted(connection.execute("PRAGMA table_info(especies_lugares)"), key=lambda row: row[5])
        if row[5]
    ]
    if primary_key != ["id_especie", "id_lugar", "fuente_id"]:
        connection.execute("ALTER TABLE especies_lugares RENAME TO especies_lugares_anterior")
        statement = SCHEMA.split("CREATE TABLE IF NOT EXISTS especies_lugares (")[1].split(";")[0]
        connection.execute("CREATE TABLE especies_lugares (" + statement)
        connection.execute(
            "INSERT INTO especies_lugares SELECT id_especie, id_lugar, tipo_relacion, "
            "fuente_id, taxon_id_stri, nota FROM especies_lugares_anterior"
        )
        connection.execute("DROP TABLE especies_lugares_anterior")


def remove_missing_rows(connection, table, key_columns, rows):
    keys = {tuple(row[column] for column in key_columns) for row in rows}
    existing = connection.execute(
        f"SELECT {', '.join(key_columns)} FROM {table}"
    ).fetchall()
    stale = [tuple(row) for row in existing if tuple(row) not in keys]
    if stale:
        condition = " AND ".join(f"{column}=?" for column in key_columns)
        connection.executemany(
            f"DELETE FROM {table} WHERE {condition}", stale
        )


def initialize_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(SCHEMA)
        migrate_tables(connection)
        connection.execute("CREATE INDEX IF NOT EXISTS especies_por_lugar ON especies_lugares(id_lugar, id_especie)")
        sources = [
            {**row, "id": row["fuente_id"]}
            for row in read_csv("fuentes.csv")
        ]
        species = [
            {**row, "id": row["id_especie"]}
            for row in read_csv("especies.csv")
        ]
        places = []
        for row in read_csv("lugares.csv"):
            place = {**row, "id": row["id_lugar"]}
            for coordinate in ("latitud", "longitud"):
                place[coordinate] = value(row, coordinate)
            places.append(place)
        relations = read_csv("especies_lugares.csv") + read_csv("observaciones_gbif.csv")
        images = read_csv("imagenes_especies.csv")
        place_images = read_csv("imagenes_lugares.csv")
        for rows, records, key in [(images, species, "id_especie"), (place_images, places, "id_lugar")]:
            if len(rows) != len(records) or {r[key] for r in rows} != {r[key] for r in records}:
                raise ValueError(f"El registro visual debe incluir una fila por {key}")
            for image in rows:
                if image.get("archivo"):
                    path = (ROOT / "static" / image["archivo"]).resolve()
                    if not path.is_relative_to((ROOT / "static/img").resolve()):
                        raise ValueError(f"Ruta de imagen inválida: {image['archivo']}")
                if image["estado"] == "verificada":
                    if image.get('tipo_visual') not in {'fotografia', 'referencia'}:
                        raise ValueError(f"Tipo de fotografía inválido: {image[key]}")
                    if image['tipo_visual'] == 'referencia' and (not image.get('archivo') or not (ROOT/'static'/image['archivo']).is_file()):
                        raise ValueError(f"Referencia local no disponible: {image[key]}")
                    name = "nombre_cientifico" if key == "id_especie" else "nombre"
                    expected = next(r[name] for r in records if r[key] == image[key])
                    if (image.get("tipo_visual") != "referencia" and image.get("nombre_confirmado") != expected) or not all(image.get(field) for field in ("imagen_url", "fuente_url", "autor", "fecha_verificacion", "nombre_confirmado")):
                        raise ValueError(f"Fotografía sin verificación completa: {image[key]}")
                    if not image["imagen_url"].startswith(("https://", "http://")):
                        raise ValueError(f"URL de fotografía inválida: {image[key]}")
        import_rows(
            connection,
            "fuentes",
            ["id", "titulo", "organizacion", "tipo", "url", "fecha_consulta", "nota_metodologica"],
            sources,
            "id",
        )
        import_rows(
            connection,
            "especies",
            ["id", "nombre_cientifico", "nombre_comun_es", "categoria", "grupo_taxonomico", "familia", "rango_taxonomico", "estado_conservacion_panama", "fuente_taxonomia_id", "fuente_nombre_comun_id", "fuente_estado_panama_id"],
            species,
            "id",
        )
        import_rows(
            connection,
            "lugares",
            ["id", "nombre", "nombre_en_checklist", "categoria_manejo", "latitud", "longitud", "precision_ubicacion", "fuente_area_id", "fuente_coordenada_id", "id_miambiente", "provincias", "provincia_fuente_url", "provincia_metodo"],
            places,
            "id",
        )
        import_rows(
            connection,
            "especies_lugares",
            ["id_especie", "id_lugar", "tipo_relacion", "fuente_id", "taxon_id_stri", "nota"],
            relations,
            ["id_especie", "id_lugar", "fuente_id"],
        )
        import_rows(
            connection, "imagenes_especies",
            ["id_especie", "nombre_cientifico", "nombre_confirmado", "imagen_url", "archivo", "estado", "fuente_url", "autor", "licencia", "licencia_url", "nota", "fecha_verificacion", "tipo_visual"],
            images, "id_especie",
        )
        import_rows(
            connection, "imagenes_lugares",
            ["id_lugar", "nombre", "nombre_confirmado", "imagen_url", "archivo", "estado", "fuente_url", "autor", "licencia", "licencia_url", "nota", "fecha_verificacion", "tipo_visual"],
            place_images, "id_lugar",
        )
        legacy_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(especies)")
        }
        for column in ("fuente_iucn_id", "fuente_lista_panama_id"):
            if column in legacy_columns:
                connection.execute(f"UPDATE especies SET {column}=NULL")
        remove_missing_rows(connection, "imagenes_especies", ["id_especie"], images)
        remove_missing_rows(connection, "imagenes_lugares", ["id_lugar"], place_images)
        remove_missing_rows(connection, "especies_lugares", ["id_especie", "id_lugar", "fuente_id"], relations)
        remove_missing_rows(connection, "especies", ["id"], species)
        remove_missing_rows(connection, "lugares", ["id"], places)
        remove_missing_rows(connection, "fuentes", ["id"], sources)


if __name__ == "__main__":
    initialize_database()
    print(f"Base inicializada en {DB_PATH}")
