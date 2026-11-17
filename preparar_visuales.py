import csv
import json
import math
import shutil

from visuales import ROOT, AREA_SOURCE, GROUPS, group_svg, area_svg


def read(name):
    with (ROOT / "data" / name).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write(name, rows):
    with (ROOT / "data" / name).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def simplify(points, tolerance):
    keep = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        a, b = points[first], points[last]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = dx * dx + dy * dy
        best, index = 0, first
        for i in range(first + 1, last):
            p = points[i]
            t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length)) if length else 0
            distance = math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)
            if distance > best:
                best, index = distance, i
        if best > tolerance:
            keep.add(index)
            stack.extend([(first, index), (index, last)])
    result = [points[i] for i in sorted(keep)]
    return result if len(result) >= 4 else points


def prepare():
    geometry_path = ROOT / "data/geometrias_lugares.json"
    geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
    if "source_url" not in geometry:
        for feature in geometry["features"]:
            rings = feature["geometry"]["rings"]
            points = [p for ring in rings for p in ring]
            extent = max(max(p[k] for p in points) - min(p[k] for p in points) for k in [0, 1])
            feature["geometry"]["rings"] = [simplify(ring, extent / 1500) for ring in rings]
        geometry["source_url"] = AREA_SOURCE
        geometry["nota"] = "Copia estática de geometrías EPSG:32617; simplificada para miniaturas, tolerancia máxima 1/1500 de la extensión de cada área. No usar para navegación ni delimitación legal."
        geometry_path.write_text(json.dumps(geometry, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for directory in ["especies", "lugares"]:
        (ROOT / "static/img" / directory).mkdir(parents=True, exist_ok=True)
    for group, slug in GROUPS.items():
        (ROOT / f"static/img/especies/{slug}.svg").write_text(group_svg(group), encoding="utf-8")
    photos = {r["id_especie"]: r for r in read("imagenes_especies.csv") if r.get("tipo_visual", "fotografia") == "fotografia"}
    rows = []
    for species in read("especies.csv"):
        group = species["grupo_taxonomico"].split(";")[0].strip()
        backup = f"img/especies/{GROUPS[group]}.svg"
        photo = photos.get(species["id_especie"])
        row = dict(id_especie=species["id_especie"], nombre_cientifico=species["nombre_cientifico"], archivo=backup, tipo_visual="ilustracion", fuente_url="", autor="EcoAvista", licencia="Ilustración original del proyecto", licencia_url="", nota=f"Ilustración referencial de {group}; no representa una identificación visual de esta especie.", respaldo=backup)
        if photo:
            original = ROOT / "static" / photo["archivo"]
            target = ROOT / "static/img/especies" / original.name
            if original != target:
                shutil.copyfile(original, target)
            row.update(archivo=target.relative_to(ROOT / "static").as_posix(), tipo_visual="fotografia", fuente_url=photo.get("fuente_url", photo.get("fuente", "")), autor=photo["autor"], licencia=photo["licencia"], licencia_url=photo["licencia_url"], nota=photo["nota"])
        rows.append(row)
    write("imagenes_especies.csv", rows)
    rows = []
    features = {str(f["attributes"]["objectid_1"]): f for f in geometry["features"]}
    for place in read("lugares.csv"):
        assert features[place["id_miambiente"]]["attributes"]["nombre"] == place["nombre"]
        backup = f"img/lugares/{place['id_lugar']}.svg"
        (ROOT / "static" / backup).write_text(area_svg(place["id_miambiente"]), encoding="utf-8")
        row = dict(id_lugar=place["id_lugar"], nombre=place["nombre"], archivo=backup, tipo_visual="mapa", fuente_url=AREA_SOURCE, autor="MiAMBIENTE; representación EcoAvista", licencia="La capa consultada no declara licencia específica; se conserva atribución y procedencia", licencia_url="", nota="Mapa del área a partir de geometría oficial EPSG:32617 simplificada para miniatura. Norte arriba; escala ajustada por área. No representa una entrada ni posiciones de especies.", respaldo=backup)
        if place["id_lugar"] == "L004" and (ROOT / "static/img/lugares/coiba.jpg").is_file():
            row.update(archivo="img/lugares/coiba.jpg", tipo_visual="fotografia", fuente_url="https://commons.wikimedia.org/wiki/File:Beach_on_Coiba,_Panama_(26822116145).jpg", autor="dronepicr", licencia="CC BY 2.0", licencia_url="https://creativecommons.org/licenses/by/2.0/", nota="Playa de Coiba, 25 de marzo de 2016. Miniatura de Wikimedia de 960 px; encuadre adaptado con CSS.")
        rows.append(row)
    write("imagenes_lugares.csv", rows)


if __name__ == "__main__":
    prepare()
