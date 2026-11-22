import json
from datetime import datetime, timezone
from catalogar_fotos import ROOT, fetch, check_image

SELECTED = {"L_MA_079": 3}

if __name__ == "__main__":
    rows = [json.loads(line) for line in (ROOT / "data/candidatas_miambiente.jsonl").read_text(encoding="utf-8").splitlines()]
    with (ROOT / "data/fotos_miambiente_verificacion.jsonl").open("w", encoding="utf-8") as output:
        for row in rows:
            if row["id_lugar"] not in SELECTED:
                continue
            photo = row["candidatas"][SELECTED[row["id_lugar"]]]
            print(json.dumps(photo, ensure_ascii=True), flush=True)
            try:
                url, width, height = check_image(photo["imagen_url"])
                data = fetch(url, image=True)[0]
                (ROOT / "data" / (row["id_lugar"] + "_revision.jpg")).write_bytes(data)
                result = dict(id_lugar=row["id_lugar"], nombre=row["nombre"], nombre_confirmado=row["nombre"], imagen_url=url, fuente_url=photo["fuente_url"], autor="MiAMBIENTE; fotógrafo no indicado", licencia="Condiciones de MiAMBIENTE", licencia_url="", archivo="", estado="verificada", fecha_verificacion=datetime.now(timezone.utc).isoformat(), nota=photo["titulo"], evidencia=photo)
                output.write(json.dumps(result, ensure_ascii=False) + "\n")
                output.flush()
            except Exception as error:
                print(str(error), flush=True)
