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
    grupo_taxonomico TEXT,
    familia TEXT,
    fuente_taxonomia_id TEXT REFERENCES fuentes(id),
    grupo_biologico TEXT,
    iucn_categoria TEXT,
    iucn_anio_evaluacion INTEGER,
    fuente_iucn_id TEXT REFERENCES fuentes(id),
    estado_lista_panama TEXT,
    anio_lista_panama INTEGER,
    fuente_lista_panama_id TEXT REFERENCES fuentes(id)
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
    fuente_coordenada_id TEXT REFERENCES fuentes(id)
);
CREATE TABLE IF NOT EXISTS especies_lugares (
    id_especie TEXT NOT NULL REFERENCES especies(id) ON DELETE CASCADE,
    id_lugar TEXT NOT NULL REFERENCES lugares(id) ON DELETE CASCADE,
    tipo_relacion TEXT,
    fuente_id TEXT REFERENCES fuentes(id),
    nota TEXT,
    PRIMARY KEY (id_especie, id_lugar)
);
"""

SPECIES_MIGRATIONS = {
    "grupo_biologico": "TEXT",
    "iucn_categoria": "TEXT",
    "iucn_anio_evaluacion": "INTEGER",
    "fuente_iucn_id": "TEXT REFERENCES fuentes(id)",
    "estado_lista_panama": "TEXT",
    "anio_lista_panama": "INTEGER",
    "fuente_lista_panama_id": "TEXT REFERENCES fuentes(id)",
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


def migrate_species(connection):
    existing = {
        row[1] for row in connection.execute("PRAGMA table_info(especies)")
    }
    for column, definition in SPECIES_MIGRATIONS.items():
        if column not in existing:
            connection.execute(f"ALTER TABLE especies ADD COLUMN {column} {definition}")


def initialize_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(SCHEMA)
        migrate_species(connection)
        import_rows(
            connection,
            "fuentes",
            ["id", "titulo", "organizacion", "tipo", "url", "fecha_consulta", "nota_metodologica"],
            [
                {**row, "id": row["fuente_id"]}
                for row in read_csv("fuentes.csv")
            ],
            "id",
        )
        import_rows(
            connection,
            "especies",
            ["id", "nombre_cientifico", "nombre_comun_es", "grupo_taxonomico", "familia", "fuente_taxonomia_id", "grupo_biologico", "iucn_categoria", "iucn_anio_evaluacion", "fuente_iucn_id", "estado_lista_panama", "anio_lista_panama", "fuente_lista_panama_id"],
            [
                {**row, "id": row["id_especie"]}
                for row in read_csv("especies.csv")
            ],
            "id",
        )
        places = []
        for row in read_csv("lugares.csv"):
            place = {**row, "id": row["id_lugar"]}
            for coordinate in ("latitud", "longitud"):
                place[coordinate] = value(row, coordinate)
            places.append(place)
        import_rows(
            connection,
            "lugares",
            ["id", "nombre", "nombre_en_checklist", "categoria_manejo", "latitud", "longitud", "precision_ubicacion", "fuente_area_id", "fuente_coordenada_id"],
            places,
            "id",
        )
        import_rows(
            connection,
            "especies_lugares",
            ["id_especie", "id_lugar", "tipo_relacion", "fuente_id", "nota"],
            read_csv("especies_lugares.csv"),
            ["id_especie", "id_lugar"],
        )


if __name__ == "__main__":
    initialize_database()
    print(f"Base inicializada en {DB_PATH}")
