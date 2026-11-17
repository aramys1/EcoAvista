import base64
import json
from functools import lru_cache
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AREA_SOURCE = "https://geoportal.miambiente.gob.pa/server/rest/services/Hosted/Area_Protegida_F/FeatureServer/0"
GROUPS = {"Plantas": "plantas", "Aves": "aves", "Anfibios": "anfibios", "Peces": "peces", "Mamíferos": "mamiferos", "Reptiles": "reptiles"}
SHAPES = {
    "plantas": '<path d="M320 310V155M320 250Q215 260 215 160Q310 150 320 250M320 205Q420 220 425 115Q330 110 320 205"/><path d="M270 320H370"/>',
    "aves": '<path d="M190 260Q260 170 330 205Q350 130 400 180L445 195L410 211Q400 285 305 280L220 300L245 260Q215 275 190 260Z"/><path d="M300 240Q340 200 370 230M330 280L325 315M350 280L360 315"/><circle cx="389" cy="192" r="5" fill="#eff7e9"/>',
    "anfibios": '<ellipse cx="320" cy="245" rx="72" ry="55"/><circle cx="280" cy="195" r="25"/><circle cx="360" cy="195" r="25"/><path d="M255 240L210 275L255 310L200 325M385 240L430 275L385 310L440 325M290 280L275 325M350 280L365 325"/><circle cx="280" cy="192" r="8" fill="#eff7e9"/><circle cx="360" cy="192" r="8" fill="#eff7e9"/>',
    "peces": '<path d="M205 235Q305 125 410 235Q305 345 205 235L155 180V290Z"/><path d="M285 180L320 145L350 185M285 290L320 320L350 280M365 200Q340 235 365 270"/><circle cx="385" cy="225" r="6" fill="#eff7e9"/>',
    "mamiferos": '<ellipse cx="310" cy="235" rx="90" ry="48"/><circle cx="405" cy="215" r="40"/><circle cx="385" cy="180" r="16"/><circle cx="430" cy="185" r="14"/><path d="M245 265L235 315M280 275L280 315M350 270L360 315M380 250L395 310M220 225Q165 220 180 175"/><circle cx="420" cy="211" r="5" fill="#eff7e9"/>',
    "reptiles": '<path d="M180 280Q225 185 315 220L400 210L445 235L395 250L315 255Q235 235 180 280Z"/><path d="M285 225L265 180L235 175M340 220L360 180L390 170M285 250L270 290L240 300M340 250L365 295L395 300"/><circle cx="410" cy="227" r="5" fill="#eff7e9"/>',
}


def frame(content, label):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 480"><rect width="640" height="480" rx="28" fill="#edf5ed"/><circle cx="530" cy="80" r="130" fill="#dceee3"/><path d="M0 360Q180 300 320 370T640 340V480H0Z" fill="#d4e8ed"/>{content}<text x="320" y="432" text-anchor="middle" font-family="sans-serif" font-size="19" fill="#285741">{escape(label)}</text></svg>'


@lru_cache(maxsize=8)
def group_svg(group):
    slug = GROUPS.get(group, "plantas")
    return frame(f'<g fill="#85b59a" stroke="#285741" stroke-width="7" stroke-linejoin="round" stroke-linecap="round">{SHAPES[slug]}</g>', f"{group} · Ilustración referencial")


@lru_cache(maxsize=1)
def geometries():
    data = json.loads((ROOT / "data/geometrias_lugares.json").read_text(encoding="utf-8"))
    return {str(f["attributes"]["objectid_1"]): f for f in data["features"]}


@lru_cache(maxsize=100)
def area_svg(area_id):
    feature = geometries()[str(area_id)]
    rings = feature["geometry"]["rings"]
    points = [point for ring in rings for point in ring]
    xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
    ymin, ymax = min(p[1] for p in points), max(p[1] for p in points)
    scale = min(520 / max(xmax - xmin, 1), 290 / max(ymax - ymin, 1))
    paths = []
    for ring in rings:
        xy = [(320 + (p[0] - (xmin + xmax) / 2) * scale, 220 - (p[1] - (ymin + ymax) / 2) * scale) for p in ring]
        paths.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in xy) + "Z")
    content = f'<path d="{"".join(paths)}" fill="#83b79a" fill-rule="evenodd" stroke="#245c42" stroke-width="1.5"/><path d="M590 90V45L582 60M590 45L598 60" fill="none" stroke="#285741" stroke-width="3"/><text x="590" y="32" text-anchor="middle" font-family="sans-serif" fill="#285741">N</text><text x="32" y="32" font-family="sans-serif" fill="#285741" font-size="16">MiAMBIENTE · ID {escape(str(area_id))}</text>'
    return frame(content, "Mapa del área · Geometría oficial")


def data_uri(svg):
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
