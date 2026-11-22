import json
from datetime import datetime, timezone
from catalogar_fotos import ROOT

if __name__ == '__main__':
    rows = json.loads((ROOT/'data/areas_revision.json').read_text(encoding='utf-8'))
    with (ROOT/'data/fotos_miambiente_verificacion.jsonl').open('a', encoding='utf-8') as output:
        for row in rows:
            if row['id_lugar'] not in {'L_MA_020', 'L001'}:
                continue
            row.update(estado='verificada', nombre_confirmado=row['nombre'], autor='MiAMBIENTE; fotógrafo no indicado', licencia='Condiciones de MiAMBIENTE', licencia_url='', fecha_verificacion=datetime.now(timezone.utc).isoformat(), nota='Fotografía del área publicada por MiAMBIENTE y revisada visualmente.')
            output.write(json.dumps(row, ensure_ascii=False) + '\n')
