import json
from datetime import datetime, timezone

from catalogar_fotos import ROOT, check_image


SELECTED = {"L_MA_013": 0, "L003": 2, "L_MA_027": 0, "L_MA_083": 2, "L_MA_040": 1, "L_MA_030": 2, "L_MA_062": 1, "L_MA_047": 1, "L_MA_021": 4, "L_MA_024": 0, "L_MA_032": 4}


if __name__ == "__main__":
    rows = [json.loads(line) for line in (ROOT / "data/candidatas_lugares.jsonl").read_text(encoding="utf-8").splitlines()]
    path = ROOT / "data/fotos_lugares_verificacion.jsonl"
    with path.open("w", encoding="utf-8") as output:
        for row in rows:
            if row["id_lugar"] not in SELECTED:
                continue
            photo = row["candidatas"][SELECTED[row["id_lugar"]]]
            result = dict(id_lugar=row["id_lugar"], nombre=row["nombre"], estado="pendiente")
            try:
                final, width, height = check_image(photo["imagen_url"])
                result.update(estado="verificada", imagen_url=final, fuente_url=photo["fuente_url"], autor=photo["Artist"] or "Autor no indicado en la fuente", nombre_confirmado=row["nombre"], licencia=photo["LicenseShortName"], licencia_url=photo["LicenseUrl"], archivo="", nota=photo["ImageDescription"], evidencia=dict(titulo=photo["titulo"], descripcion=photo["ImageDescription"], categorias=photo["Categories"], ancho=width, alto=height), fecha_verificacion=datetime.now(timezone.utc).isoformat())
            except Exception as error:
                result["nota"] = str(error)
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            output.flush()
            print(row["id_lugar"],result["estado"],flush=True)
