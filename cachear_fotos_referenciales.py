import json
from catalogar_fotos import ROOT
from preparar_referencias_fotograficas import local_photo


if __name__ == '__main__':
    path = ROOT/'data/fotos_referenciales.jsonl'
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    output = []
    for row in rows:
        filename = 'img/referencias/' + row['id_lugar'].lower() + '.jpg'
        row = local_photo(row, filename)
        row['nombre_confirmado'] = 'Pteroglossus torquatus' if row['id_lugar']=='L_MA_004' else 'Lago de Gamboa'
        output.append(row)
        print(row['id_lugar'],filename,flush=True)
    path.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in output),encoding='utf-8')
