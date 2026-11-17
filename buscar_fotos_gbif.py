import json
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from catalogar_fotos import ROOT, fetch, plain, check_image


def find_photo(row):
    name = row["nombre_cientifico"]
    params = urllib.parse.urlencode(dict(scientificName=name, mediaType="StillImage", limit=12))
    errors = []
    try:
        records = json.loads(fetch("https://api.gbif.org/v1/occurrence/search?" + params)[0]).get("results", [])
        for record in records:
            if record.get("species") != name or record.get("taxonRank") != "SPECIES":
                continue
            source = record.get("references") or record.get("occurrenceID", "")
            if not source.startswith(("https://", "http://")):
                continue
            media = [m for m in record.get("media", []) if m.get("type") == "StillImage" and m.get("identifier", "").startswith(("http://", "https://"))]
            if not media:
                continue
            try:
                observation = re.search(r'inaturalist\.org/observations/(\d+)', source)
                if observation:
                    api = "https://api.inaturalist.org/v1/observations/" + observation.group(1)
                    result = json.loads(fetch(api)[0]).get("results", [])[0]
                    if result.get("taxon", {}).get("name") != name or result.get("quality_grade") != "research":
                        continue
                    photo_ids = {str(photo["id"]) for photo in result.get("photos", [])}
                    media = [m for m in media if any("/photos/" + photo_id + "/" in m["identifier"] for photo_id in photo_ids)]
                    proof = dict(nombre_original=result["taxon"]["name"], fuente_estructurada=api, gbif=record["key"])
                elif record.get("basisOfRecord") == "PRESERVED_SPECIMEN":
                    page = fetch(source)[0].decode("utf-8", "replace")
                    if name not in plain(page):
                        continue
                    media = [m for m in media if urllib.parse.unquote(m["identifier"].split("/")[-1].split("?")[0]) in urllib.parse.unquote(page)]
                    proof = dict(nombre_original=name, fuente_estructurada=f"https://api.gbif.org/v1/occurrence/{record['key']}", gbif=record["key"], tipo="espécimen identificado")
                else:
                    continue
                for image in media[:2]:
                    url = image["identifier"]
                    if observation:
                        url = re.sub(r'/original\.(jpe?g|png)$', r'/large.\1', url, flags=re.I)
                    final, width, height = check_image(url)
                    proof.update(ancho=width, alto=height)
                    return dict(estado="verificada", imagen_url=final, fuente_url=source, autor=image.get("creator") or image.get("rightsHolder") or "Autor no indicado por el proveedor", nombre_confirmado=name, licencia=image.get("license") or "Condiciones del proveedor", licencia_url=image.get("license", ""), archivo="", nota="Fotografía vinculada a una identificación exacta en la fuente original; descubierta mediante GBIF.", evidencia=proof)
            except Exception as error:
                errors.append(str(error)[:120])
    except Exception as error:
        errors.append(str(error)[:120])
    return dict(estado="pendiente", nota="Sin fotografía exacta verificable en GBIF y su proveedor original. " + "; ".join(errors[:2]))


if __name__ == "__main__":
    source = ROOT / "data/fotos_verificacion.jsonl"
    target = ROOT / "data/fotos_gbif.jsonl"
    done = {json.loads(line)["id_especie"] for line in target.read_text(encoding="utf-8").splitlines()} if target.exists() else set()
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    todo = [row for row in rows if row["estado"] == "pendiente" and row["id_especie"] not in done]
    with ThreadPoolExecutor(max_workers=3) as executor, target.open("a", encoding="utf-8") as output:
        futures = {executor.submit(find_photo, row): row for row in todo}
        count = 0
        for index, future in enumerate(as_completed(futures), 1):
            row = futures[future]
            result = future.result()
            result.update(id_especie=row["id_especie"], nombre_cientifico=row["nombre_cientifico"], fecha_verificacion=datetime.now(timezone.utc).isoformat())
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            output.flush()
            count += result["estado"] == "verificada"
            if index % 20 == 0 or index == len(todo):
                print(f"GBIF: {index}/{len(todo)}; {count} fotos adicionales verificadas", flush=True)
