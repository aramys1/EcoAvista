import csv
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

from catalogar_fotos import ROOT, read_csv


FIELDS = ["nombre_confirmado", "imagen_url", "fuente_url", "autor", "licencia", "licencia_url", "archivo", "estado", "fecha_verificacion", "nota", "tipo_visual"]


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
    reference_rows = []
    totals = {}
    for kind, key, name, files in [
        ("especies", "id_especie", "nombre_cientifico", ["fotos_wikidata.jsonl", "fotos_inaturalist.jsonl", "fotos_gbif.jsonl", "fotos_verificacion.jsonl", "fotos_taxonomia_actualizada.jsonl", "fotos_formatos.jsonl", "fotos_manuales.jsonl"]),
        ("lugares", "id_lugar", "nombre", ["fotos_areas_wikipedia.jsonl", "fotos_lugares_verificacion.jsonl", "fotos_miambiente_verificacion.jsonl", "fotos_manuales.jsonl", "fotos_referenciales.jsonl", "fotos_propias_lugares.jsonl"]),
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
                row["tipo_visual"] = row["tipo_visual"] or "fotografia"
                url = urlsplit(row["imagen_url"])
                # En WMS los límites del encuadre identifican una imagen distinta.
                query = sorted(parse_qsl(url.query)) if row["nota"].startswith("Vista satelital") else []
                by_url[url._replace(query=urlencode(query), fragment="").geturl()].append(row)
            rows.append(row)
        for url, duplicates in by_url.items():
            if len(duplicates) > 1:
                for row in [r for r in duplicates if r["tipo_visual"] != "referencia"]:
                    row.update(estado="pendiente", imagen_url="", archivo="", nota="Fotografía compartida por registros distintos; identificación exacta pendiente de revisión.")
        if kind == "especies":
            references = json.loads((ROOT / 'data/referencias_grupos.json').read_text(encoding='utf-8'))
            originals = {r[key]:r for r in read_csv('especies.csv')}
            for row in rows:
                if row['estado'] == 'verificada':
                    continue
                original = originals[row[key]]
                group = next(g.strip() for g in original['grupo_taxonomico'].split(';') if g.strip() in references)
                reference = references[group]
                row.update({field:reference.get(field,'') for field in FIELDS})
                row.update(estado='verificada', tipo_visual='referencia', nota='Fotografía referencial del grupo ' + group + '. Especie fotografiada: ' + reference['nombre_confirmado'] + '. No identifica la especie de esta ficha.')
        for row in rows:
            if row["estado"] != "verificada":
                pending.append(dict(tipo=kind, id=row[key], nombre=row[name], motivo=row["nota"]))
            elif row['tipo_visual'] == 'referencia':
                reference_rows.append(dict(tipo=kind,id=row[key],nombre=row[name],nombre_visual=row['nombre_confirmado'],archivo=row['archivo'],fuente_url=row['fuente_url'],autor=row['autor'],licencia=row['licencia']))
        write_csv("imagenes_" + kind + ".csv", [key, name] + FIELDS, rows)
        totals[kind] = dict(total=len(rows), verificadas=sum(row["estado"] == "verificada" for row in rows), pendientes=sum(row["estado"] != "verificada" for row in rows))
        totals[kind]["referenciales"] = sum(row["estado"] == "verificada" and row["tipo_visual"] == "referencia" for row in rows)
        totals[kind]['fotografias_especificas'] = totals[kind]['verificadas'] - totals[kind]['referenciales']
        totals[kind]['cobertura_porcentaje'] = round(totals[kind]['verificadas'] / totals[kind]['total'] * 100, 2)
    write_csv("fotografias_pendientes.csv", ["tipo", "id", "nombre", "motivo"], pending)
    write_csv('fotografias_referenciales.csv', ['tipo','id','nombre','nombre_visual','archivo','fuente_url','autor','licencia'], reference_rows)
    (ROOT / "data/cobertura_fotografias.json").write_text(json.dumps(totals, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(totals, ensure_ascii=False))


if __name__ == "__main__":
    export()
