import json
import re
import unicodedata
import urllib.parse

from catalogar_fotos import ROOT, fetch, plain, read_csv


def normalized(value):
    return " ".join("".join(c for c in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(c) != "Mn").split())


if __name__ == "__main__":
    target = ROOT / "data/candidatas_miambiente.jsonl"
    done = {json.loads(line)["id_lugar"] for line in target.read_text(encoding="utf-8").splitlines()} if target.exists() else set()
    with target.open("a", encoding="utf-8") as output:
        for place in read_csv("lugares.csv"):
            if place["id_lugar"] in done:
                continue
            result = dict(id_lugar=place["id_lugar"], nombre=place["nombre"], candidatas=[])
            query = urllib.parse.urlencode(dict(search=place["nombre"], per_page=20, _embed=1))
            try:
                posts = json.loads(fetch("https://miambiente.gob.pa/wp-json/wp/v2/posts?" + query)[0])
                for post in posts:
                    title = plain(post["title"]["rendered"])
                    if normalized(place["nombre"]) not in normalized(title):
                        continue
                    media = post.get("_embedded", {}).get("wp:featuredmedia", [{}])[0]
                    if not media.get("source_url"):
                        continue
                    image = media.get("media_details", {}).get("sizes", {}).get("large", {}).get("source_url", media["source_url"])
                    result["candidatas"].append(dict(titulo=title, fuente_url=post["link"], imagen_url=image, alt=media.get("alt_text", ""), caption=plain(media.get("caption", {}).get("rendered", "")), descripcion=plain(post["content"]["rendered"])[:1500], api="https://miambiente.gob.pa/wp-json/wp/v2/posts/"+str(post['id'])))
            except Exception as error:
                result["error"] = str(error)
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            output.flush()
            print(place["id_lugar"], len(result["candidatas"]), flush=True)
