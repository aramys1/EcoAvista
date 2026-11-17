import argparse
import csv
import html
import json
import re
import struct
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "data/fotos_verificacion.jsonl"
HEADERS = {"User-Agent": "EcoAvista academic photo catalog/1.0", "Accept": "text/html,application/json,image/*;q=0.9,*/*;q=0.8"}
HOST_LOCK = threading.Lock()
HOST_NEXT = {}


def read_csv(name):
    with (ROOT / "data" / name).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def fetch(url, image=False):
    host = urllib.parse.urlparse(url).netloc
    for attempt in range(2):
        with HOST_LOCK:
            now = time.monotonic()
            wait = max(0, HOST_NEXT.get(host, now) - now)
            HOST_NEXT[host] = now + wait + 1.1
        if wait:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=18) as response:
                content = response.read(196608 if image else 1500000)
                return content, response.geturl(), response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as error:
            if error.code in {429, 503} and attempt == 0:
                delay = max(30, min(120, int(error.headers.get("Retry-After", "30")) if error.headers.get("Retry-After", "30").isdigit() else 30))
                with HOST_LOCK:
                    HOST_NEXT[host] = time.monotonic() + delay
                time.sleep(delay)
            else:
                raise


def dimensions(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i + 9 < len(data):
            if data[i] != 255:
                i += 1
                continue
            marker = data[i + 1]
            i += 2
            if marker in {0xD8, 0xD9}:
                continue
            if i + 2 > len(data):
                break
            length = struct.unpack(">H", data[i:i + 2])[0]
            if marker in {0xC0, 0xC1, 0xC2, 0xC3}:
                height, width = struct.unpack(">HH", data[i + 3:i + 7])
                return width, height
            if length < 2:
                break
            i += length
    raise ValueError("Formato o dimensiones de fotografía no comprobados")


def check_image(url):
    data, final, content_type = fetch(url, image=True)
    width, height = dimensions(data)
    if min(width, height) < 250 or max(width, height) < 400:
        raise ValueError(f"Resolución insuficiente: {width}x{height}")
    return final, width, height


def plain(value):
    return html.unescape(re.sub(r"<[^>]+>", "", value)).strip()


def stri_photo(species, taxon_ids):
    name = species["nombre_cientifico"]
    errors = []
    for taxon_id in taxon_ids[:2]:
        source = f"https://panamabiota.org/stri/taxa/index.php?taxon={urllib.parse.quote(taxon_id)}"
        try:
            content, source, _ = fetch(source)
            page = content.decode("utf-8", "replace")
            heading = re.search(r'<h1[^>]*>(.*?)</h1>', page, re.S | re.I)
            if not heading or plain(heading.group(1)) != name:
                errors.append("El nombre del encabezado no coincide exactamente")
                continue
            block = re.search(r'<div id="centralimage">(.*?)</td>', page, re.S)
            if not block:
                errors.append("Sin fotografía principal identificada")
                continue
            image = re.search(r'<img\b([^>]+)>', block.group(1), re.I)
            if not image:
                errors.append("Sin fotografía principal identificada")
                continue
            attrs = dict((k.lower(), html.unescape(v)) for k, v in re.findall(r'([\w-]+)="([^"]*)"', image.group(1)))
            alt, title = attrs.get("alt", ""), attrs.get("title", "")
            if alt != name + " image" or re.search(r'illustrat|drawing|dibujo|mapa|linked from|painting', title, re.I):
                errors.append("Imagen sin identificación exacta o de tipo no fotográfico")
                continue
            url = urllib.parse.urljoin(source, attrs.get("src", ""))
            if not re.search(r'\.(jpg|jpeg|png)(?:\?|$)', url, re.I):
                errors.append("Formato fotográfico no confirmado")
                continue
            creator = re.search(r'<div class="creator">(.*?)</div>', block.group(1), re.S)
            author = (plain(creator.group(1)) if creator else "") or "Autor no indicado por STRI"
            final, width, height = check_image(url)
            return dict(estado="verificada", imagen_url=final, fuente_url=source, autor=author,
                        nombre_confirmado=name, licencia="Condiciones del proveedor STRI/Panamabiota; no se declara licencia abierta en la ficha taxonómica",
                        licencia_url="", archivo="", tipo_visual="fotografia",
                        nota=f"Foto principal publicada en ficha taxonómica con encabezado y texto alternativo coincidentes. {title}".strip(),
                        evidencia=dict(encabezado=plain(heading.group(1)), alt=alt, titulo=title, ancho=width, alto=height))
        except Exception as error:
            errors.append(source + ": " + str(error)[:180])
    return dict(estado="pendiente", nota="; ".join(dict.fromkeys(errors)) or "Sin identificador STRI para consulta")


def run(args):
    species = read_csv("especies.csv")
    ids = {}
    for row in read_csv("especies_lugares.csv"):
        values = ids.setdefault(row["id_especie"], [])
        if row["taxon_id_stri"] and row["taxon_id_stri"] not in values:
            values.append(row["taxon_id_stri"])
    previous = {}
    if AUDIT.exists():
        for line in AUDIT.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            previous[row["id_especie"]] = row
    todo = [row for row in species if row["id_especie"] not in previous]
    if args.limit:
        todo = todo[:args.limit]
    with ThreadPoolExecutor(max_workers=args.workers) as executor, AUDIT.open("a", encoding="utf-8") as output:
        futures = {executor.submit(stri_photo, row, ids.get(row["id_especie"], [])): row for row in todo}
        found = 0
        for index, future in enumerate(as_completed(futures), 1):
            row = futures[future]
            result = future.result()
            result.update(id_especie=row["id_especie"], nombre_cientifico=row["nombre_cientifico"], fecha_verificacion=datetime.now(timezone.utc).isoformat())
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            output.flush()
            found += result["estado"] == "verificada"
            if index % 25 == 0 or index == len(todo):
                print(f"STRI: {index}/{len(todo)} consultadas; {found} fotos exactas verificadas", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=4)
    run(parser.parse_args())
