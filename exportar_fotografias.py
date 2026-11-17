import csv
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from catalogar_fotos import ROOT, read_csv


FIELDS = ["nombre_confirmado", "imagen_url", "fuente_url", "autor", "licencia", "licencia_url", "archivo", "estado", "fecha_verificacion", "nota"]


def audits(filename):
    path = ROOT / "data" / filename
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def write_csv(filename, fields, rows):
    with (ROOT / "data" / filename).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export():
    pending = []
    totals = {}
    for kind, key, name, files in [
        ("especies", "id_especie", "nombre_cientifico", ["fotos_gbif.jsonl", "fotos_verificacion.jsonl", "fotos_manuales.jsonl"]),
        ("lugares", "id_lugar", "nombre", ["fotos_lugares_verificacion.jsonl", "fotos_miambiente_verificacion.jsonl", "fotos_manuales.jsonl"]),
    ]:
        evidence = {}
        for filename in files:
            for row in audits(filename):
                if key not in row:
                    continue
                if row["estado"] == "verificada" or evidence.get(row[key], {}).get("estado") != "verificada":
                    evidence[row[key]] = row
        rows = []
        by_url = defaultdict(list)
        for record in read_csv(kind + ".csv"):
            row = {field: "" for field in [key, name] + FIELDS}
            row.update({key: record[key], name: record[name], "estado": "pendiente", "nota": "No se ha confirmado una fotografía exacta para este registro."})
            photo = evidence.get(record[key], {})
            row["nota"] = photo.get("nota", row["nota"])
            if photo.get("estado") == "verificada" and photo.get("nombre_confirmado") == record[name]:
                row.update({field: photo.get(field, "") for field in FIELDS})
                row["autor"] = row["autor"] or "Autor no indicado por el proveedor"
                by_url[urlsplit(row["imagen_url"])._replace(query="", fragment="").geturl()].append(row)
            rows.append(row)
        for url, duplicates in by_url.items():
            if len(duplicates) > 1:
                for row in duplicates:
                    row.update(estado="pendiente", imagen_url="", archivo="", nota="Fotografía compartida por registros distintos; identificación exacta pendiente de revisión.")
        for row in rows:
            if row["estado"] != "verificada":
                pending.append(dict(tipo=kind, id=row[key], nombre=row[name], motivo=row["nota"]))
        write_csv("imagenes_" + kind + ".csv", [key, name] + FIELDS, rows)
        totals[kind] = dict(total=len(rows), verificadas=sum(row["estado"] == "verificada" for row in rows), pendientes=sum(row["estado"] != "verificada" for row in rows))
    write_csv("fotografias_pendientes.csv", ["tipo", "id", "nombre", "motivo"], pending)
    (ROOT / "data/cobertura_fotografias.json").write_text(json.dumps(totals, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(totals, ensure_ascii=False))


if __name__ == "__main__":
    export()
