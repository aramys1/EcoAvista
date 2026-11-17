import json
import time
import urllib.parse

from catalogar_fotos import ROOT, fetch, plain, read_csv


if __name__ == "__main__":
    path = ROOT / "data/candidatas_lugares.jsonl"
    done = {json.loads(line)["id_lugar"] for line in path.read_text(encoding="utf-8").splitlines()} if path.exists() else set()
    with path.open("a", encoding="utf-8") as output:
        for place in read_csv("lugares.csv"):
            if place["id_lugar"] in done:
                continue
            result = {"id_lugar": place["id_lugar"], "nombre": place["nombre"], "candidatas": []}
            query = place["nombre"] + " Panama"
            params = dict(action="query", generator="search", gsrsearch=query, gsrnamespace=6, gsrlimit=5, prop="imageinfo", iiprop="url|extmetadata", iiurlwidth=960, format="json")
            try:
                data = json.loads(fetch("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))[0])
                for page in data.get("query", {}).get("pages", {}).values():
                    info = page.get("imageinfo", [{}])[0]
                    meta = info.get("extmetadata", {})
                    values = {key: plain(meta.get(key, {}).get("value", "")) for key in ["ImageDescription", "Artist", "LicenseShortName", "LicenseUrl", "Categories"]}
                    result["candidatas"].append(dict(titulo=page["title"], fuente_url=info.get("descriptionurl"), imagen_url=info.get("thumburl", info.get("url")), original_url=info.get("url"), **values))
            except Exception as error:
                result["error"] = str(error)
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            output.flush()
            print(place["id_lugar"], len(result["candidatas"]), flush=True)
            time.sleep(0.7)
